import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Mapping, Optional


Transport = Callable[
    [str, Dict[str, str], Dict[str, Any]],
    Dict[str, Any],
]

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


def _post_json(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    request_headers = {"Content-Type": "application/json", **headers}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Model provider request failed with HTTP {exc.code}: {detail[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Model provider request failed: {exc.reason}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Model provider returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Model provider returned a non-object response.")
    return parsed


def _parse_json_text(text: str) -> Dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model response did not contain a JSON object.")
        parsed = json.loads(value[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model response JSON must be an object.")
    return parsed


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        transport: Transport = _post_json,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        model = urllib.parse.quote(self.model, safe="")
        api_key = urllib.parse.quote(self.api_key, safe="")
        url = (
            f"{self.base_url}/models/{model}:generateContent"
            f"?key={api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0.1,
            },
        }
        response = self.transport(url, {}, payload)
        try:
            parts = response["candidates"][0]["content"]["parts"]
            text = "".join(
                str(part.get("text") or "")
                for part in parts
                if isinstance(part, dict)
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Gemini response did not contain generated content.") from exc
        if not text.strip():
            raise ValueError("Gemini response contained empty generated content.")
        return _parse_json_text(text)


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENAI_MODEL,
        base_url: str = "https://api.openai.com/v1",
        transport: Transport = _post_json,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "grounded_data_table",
                    "strict": False,
                    "schema": schema,
                },
            },
        }
        response = self.transport(
            f"{self.base_url}/chat/completions",
            {"Authorization": f"Bearer {self.api_key}"},
            payload,
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("OpenAI response did not contain generated content.") from exc
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenAI response contained empty generated content.")
        return _parse_json_text(content)


def create_llm_client(
    args: Dict[str, Any],
    env: Optional[Mapping[str, str]] = None,
    transport: Transport = _post_json,
):
    values = os.environ if env is None else env
    provider = str(
        args.get("provider") or values.get("MOFA_DATA_TABLE_PROVIDER") or ""
    ).strip().lower()
    gemini_key = str(values.get("GEMINI_API_KEY") or "").strip()
    openai_key = str(values.get("OPENAI_API_KEY") or "").strip()
    if not provider:
        if gemini_key:
            provider = "gemini"
        elif openai_key:
            provider = "openai"
        else:
            raise ValueError(
                "No supported model credential is configured. "
                "Set GEMINI_API_KEY or OPENAI_API_KEY."
            )
    if provider not in {"gemini", "openai"}:
        raise ValueError(f"Unsupported data table model provider: {provider}")

    model_override = str(
        args.get("model") or values.get("MOFA_DATA_TABLE_MODEL") or ""
    ).strip()
    if provider == "gemini":
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is required for provider 'gemini'.")
        return GeminiClient(
            api_key=gemini_key,
            model=model_override or DEFAULT_GEMINI_MODEL,
            base_url=str(
                values.get("GEMINI_BASE_URL")
                or "https://generativelanguage.googleapis.com/v1beta"
            ),
            transport=transport,
        )
    if not openai_key:
        raise ValueError("OPENAI_API_KEY is required for provider 'openai'.")
    return OpenAIClient(
        api_key=openai_key,
        model=model_override or DEFAULT_OPENAI_MODEL,
        base_url=str(values.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"),
        transport=transport,
    )
