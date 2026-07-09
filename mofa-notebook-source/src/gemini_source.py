import base64
import json
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional


Transport = Callable[[str, Dict[str, str], Dict[str, Any]], Dict[str, Any]]

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
INLINE_FILE_MAX_BYTES = 20 * 1024 * 1024


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini request failed with HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini request failed: {exc.reason}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Gemini returned a non-object response.")
    return parsed


def _ensure_trailing_newline(value: str) -> str:
    return value.rstrip() + "\n"


def build_gemini_prompt(path: Path, kind: str, title: str) -> str:
    return "\n".join(
        [
            "You are normalizing a user-uploaded source for a NotebookLM-like workspace.",
            "",
            f"Title: {title}",
            f"File name: {path.name}",
            f"Source kind: {kind}",
            "",
            "Return Markdown with these exact second-level headings:",
            "",
            "## Raw Extracted Content",
            "Include raw extracted text, visible text, transcript, OCR text, table text, chart labels, slide text, or any directly recoverable content. Preserve useful line breaks.",
            "",
            "## AI Summary / Description",
            "Write a semantic summary of the source. Describe important entities, claims, scenes, charts, tables, and structure. For images or video, describe visual evidence separately from inference.",
            "",
            "## Warnings / Limitations",
            "List uncertainty, missing audio/text, low-resolution areas, unreadable tables, extraction limits, or unsupported content. Use bullet points.",
            "",
            "Requirements:",
            "- Markdown output only.",
            "- Do not invent facts that are not visible, audible, or strongly implied by the file.",
            "- Mention tables and charts explicitly when present.",
            "- Keep raw extraction separate from the semantic summary.",
        ]
    )


def _compose_source_markdown(title: str, raw_markdown: str, summary_markdown: str) -> str:
    raw_body = raw_markdown.strip() or "_No raw text extracted._"
    summary_body = summary_markdown.strip() or "_No summary generated._"
    return _ensure_trailing_newline(
        "\n".join(
            [
                f"# {title}",
                "",
                "## Raw Extracted Content",
                "",
                raw_body,
                "",
                "## AI Summary / Description",
                "",
                summary_body,
            ]
        )
    )


def _heading_key(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    heading = stripped.lstrip("#").strip().lower()
    heading = re.sub(r"\s+", " ", heading)
    aliases = {
        "raw": {
            "raw",
            "raw content",
            "raw extracted content",
            "raw extracted text",
        },
        "summary": {
            "ai summary",
            "ai summary / description",
            "semantic summary",
            "summary",
            "summary / description",
        },
        "warnings": {
            "limitations",
            "warnings",
            "warnings / limitations",
            "warnings and limitations",
        },
    }
    for key, values in aliases.items():
        if heading in values:
            return key
    return None


def _clean_section(lines: List[str]) -> str:
    return "\n".join(lines).strip()


def _parse_warning_lines(value: str) -> List[str]:
    warnings: List[str] = []
    for line in value.splitlines():
        item = re.sub(r"^\s*[-*]\s*", "", line).strip()
        if item:
            warnings.append(item)
    return warnings


def parse_gemini_markdown(markdown: str) -> Dict[str, Any]:
    sections: Dict[str, List[str]] = {"raw": [], "summary": [], "warnings": []}
    current: Optional[str] = None
    preamble: List[str] = []
    for line in markdown.splitlines():
        heading = _heading_key(line)
        if heading:
            current = heading
            continue
        if current:
            sections[current].append(line)
        else:
            preamble.append(line)

    raw_markdown = _clean_section(sections["raw"])
    summary_markdown = _clean_section(sections["summary"])
    warnings = _parse_warning_lines(_clean_section(sections["warnings"]))
    if not raw_markdown and preamble:
        raw_markdown = _clean_section(preamble)
    if not summary_markdown:
        summary_markdown = markdown.strip()
        warnings.append("Gemini response did not include an explicit summary section.")
    if not raw_markdown:
        warnings.append("Gemini response did not include explicit raw extracted content.")
    return {
        "raw_markdown": _ensure_trailing_newline(raw_markdown) if raw_markdown else "",
        "summary_markdown": _ensure_trailing_newline(summary_markdown) if summary_markdown else "",
        "warnings": warnings,
    }


def _extract_gemini_text(response: Mapping[str, Any]) -> str:
    try:
        parts = response["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Gemini response did not contain generated content.") from exc
    text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise ValueError("Gemini response contained empty generated content.")
    return text


def _mime_type_for(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def normalize_with_gemini(
    path: Path,
    kind: str,
    title: str,
    env: Optional[Mapping[str, str]] = None,
    transport: Transport = _post_json,
) -> Dict[str, Any]:
    values = os.environ if env is None else env
    api_key = str(values.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(f"This source format requires GEMINI_API_KEY for notebook import: {kind}")

    data = path.read_bytes()
    if len(data) > INLINE_FILE_MAX_BYTES:
        raise ValueError(
            f"Source file is too large for inline Gemini import ({len(data)} bytes). "
            "Gemini Files API support is not implemented yet."
        )

    model = str(values.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    base_url = str(values.get("GEMINI_BASE_URL") or DEFAULT_GEMINI_BASE_URL).rstrip("/")
    mime_type = _mime_type_for(path)
    prompt = build_gemini_prompt(path, kind, title)
    url = (
        f"{base_url}/models/{urllib.parse.quote(model, safe='')}:generateContent"
        f"?key={urllib.parse.quote(api_key, safe='')}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(data).decode("ascii"),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {"temperature": 0.1},
    }
    parsed = parse_gemini_markdown(_extract_gemini_text(transport(url, {}, payload)))
    return {
        "kind": kind,
        "raw_markdown": parsed["raw_markdown"],
        "summary_markdown": parsed["summary_markdown"],
        "source_markdown": _compose_source_markdown(
            title,
            parsed["raw_markdown"],
            parsed["summary_markdown"],
        ),
        "warnings": parsed["warnings"],
        "provenance": {
            "normalizer": "gemini",
            "model": model,
            "mime_type": mime_type,
            "file_name": path.name,
        },
    }
