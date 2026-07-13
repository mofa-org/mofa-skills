from typing import Dict, List, Optional


def _heading_text(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    marker, _, title = stripped.partition(" ")
    if marker and all(ch == "#" for ch in marker) and title.strip():
        return title.strip()
    return None


def _make_chunk(
    source_id: str,
    title: str,
    source_path: str,
    heading: Optional[str],
    start_line: int,
    end_line: int,
    lines: List[str],
    index: int,
) -> Dict[str, object]:
    return {
        "chunk_id": f"{source_id}#chunk-{index:04d}",
        "source_id": source_id,
        "title": title,
        "source_path": source_path,
        "heading": heading,
        "start_line": start_line,
        "end_line": end_line,
        "text": "\n".join(lines).strip(),
    }


def chunk_markdown(
    source_id: str,
    title: str,
    source_path: str,
    text: str,
    max_lines: int = 40,
) -> List[Dict[str, object]]:
    chunks: List[Dict[str, object]] = []
    current_lines: List[str] = []
    current_heading: Optional[str] = None
    start_line = 1

    def flush(end_line: int) -> None:
        nonlocal current_lines, start_line
        body = "\n".join(current_lines).strip()
        if not body:
            current_lines = []
            start_line = end_line + 1
            return
        chunks.append(
            _make_chunk(
                source_id,
                title,
                source_path,
                current_heading,
                start_line,
                end_line,
                current_lines,
                len(chunks) + 1,
            )
        )
        current_lines = []
        start_line = end_line + 1

    lines = text.splitlines()
    for offset, line in enumerate(lines, start=1):
        heading = _heading_text(line)
        if heading and current_lines:
            flush(offset - 1)
            current_heading = heading
            start_line = offset
        elif heading:
            current_heading = heading
            start_line = offset
        current_lines.append(line)
        if len(current_lines) >= max_lines:
            flush(offset)
    if current_lines:
        flush(len(lines))
    return chunks

