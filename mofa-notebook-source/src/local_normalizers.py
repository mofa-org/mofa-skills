import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


MAX_XLSX_ROWS = 200
MAX_XLSX_COLS = 50


def _ensure_trailing_newline(value: str) -> str:
    return value.rstrip() + "\n"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr_by_local_name(element: ET.Element, name: str) -> Optional[str]:
    for key, value in element.attrib.items():
        if _local_name(key) == name:
            return value
    return None


def _parse_xml_from_zip(archive: zipfile.ZipFile, name: str) -> ET.Element:
    with archive.open(name) as fh:
        return ET.fromstring(fh.read())


def _text_nodes(element: ET.Element) -> List[str]:
    values: List[str] = []
    for child in element.iter():
        if _local_name(child.tag) == "t" and child.text:
            values.append(child.text)
    return values


def _normalize_result(kind: str, raw_markdown: str, warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "kind": kind,
        "raw_markdown": _ensure_trailing_newline(raw_markdown),
        "warnings": list(warnings or []),
        "provenance": {"normalizer": "local_office", "format": kind},
    }


def normalize_docx(path: Path, title: str) -> Dict[str, Any]:
    warnings: List[str] = []
    paragraphs: List[str] = []
    with zipfile.ZipFile(path) as archive:
        try:
            root = _parse_xml_from_zip(archive, "word/document.xml")
        except KeyError as exc:
            raise ValueError("DOCX file is missing word/document.xml.") from exc
        for paragraph in root.iter():
            if _local_name(paragraph.tag) != "p":
                continue
            text = "".join(_text_nodes(paragraph)).strip()
            if text:
                paragraphs.append(text)
    if not paragraphs:
        warnings.append("No DOCX paragraph text was extracted.")
    body = "\n\n".join(paragraphs) or "_No DOCX text extracted._"
    return _normalize_result("docx", f"# {title}\n\n{body}", warnings)


def _slide_number(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def normalize_pptx(path: Path, title: str) -> Dict[str, Any]:
    warnings: List[str] = []
    sections: List[str] = [f"# {title}"]
    with zipfile.ZipFile(path) as archive:
        slide_names = sorted(
            [
                name
                for name in archive.namelist()
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ],
            key=_slide_number,
        )
        if not slide_names:
            warnings.append("No PPTX slides were found.")
        for index, name in enumerate(slide_names, start=1):
            root = _parse_xml_from_zip(archive, name)
            lines = [text.strip() for text in _text_nodes(root) if text.strip()]
            sections.append(f"## Slide {index}")
            sections.append("\n".join(lines) if lines else "_No slide text extracted._")
        note_names = sorted(
            [
                name
                for name in archive.namelist()
                if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)
            ],
            key=_slide_number,
        )
        for index, name in enumerate(note_names, start=1):
            root = _parse_xml_from_zip(archive, name)
            lines = [text.strip() for text in _text_nodes(root) if text.strip()]
            if not lines:
                continue
            sections.append(f"### Speaker Notes {index}")
            sections.append("\n".join(lines))
    return _normalize_result("pptx", "\n\n".join(sections), warnings)


def _shared_strings(archive: zipfile.ZipFile) -> List[str]:
    try:
        root = _parse_xml_from_zip(archive, "xl/sharedStrings.xml")
    except KeyError:
        return []
    strings: List[str] = []
    for item in root.iter():
        if _local_name(item.tag) != "si":
            continue
        strings.append("".join(_text_nodes(item)))
    return strings


def _workbook_relationships(archive: zipfile.ZipFile) -> Dict[str, str]:
    try:
        root = _parse_xml_from_zip(archive, "xl/_rels/workbook.xml.rels")
    except KeyError:
        return {}
    relationships: Dict[str, str] = {}
    for relationship in root.iter():
        if _local_name(relationship.tag) != "Relationship":
            continue
        rel_id = relationship.attrib.get("Id")
        target = relationship.attrib.get("Target")
        if not rel_id or not target:
            continue
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        relationships[rel_id] = target
    return relationships


def _workbook_sheets(archive: zipfile.ZipFile) -> List[Tuple[str, str]]:
    relationships = _workbook_relationships(archive)
    try:
        root = _parse_xml_from_zip(archive, "xl/workbook.xml")
    except KeyError:
        sheet_names = sorted(
            [name for name in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)]
        )
        return [(f"Sheet{index}", name) for index, name in enumerate(sheet_names, start=1)]
    sheets: List[Tuple[str, str]] = []
    fallback_index = 1
    for sheet in root.iter():
        if _local_name(sheet.tag) != "sheet":
            continue
        name = sheet.attrib.get("name") or f"Sheet{fallback_index}"
        rel_id = _attr_by_local_name(sheet, "id")
        target = relationships.get(rel_id or "")
        if not target:
            target = f"xl/worksheets/sheet{fallback_index}.xml"
        sheets.append((name, target))
        fallback_index += 1
    return sheets


def _column_index(cell_ref: str) -> int:
    letters = re.sub(r"[^A-Za-z]", "", cell_ref).upper()
    if not letters:
        return 0
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return max(index - 1, 0)


def _first_child_text(element: ET.Element, local_name: str) -> str:
    for child in element.iter():
        if _local_name(child.tag) == local_name and child.text is not None:
            return child.text
    return ""


def _cell_value(cell: ET.Element, shared: List[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(_text_nodes(cell)).strip()
    raw_value = _first_child_text(cell, "v").strip()
    if cell_type == "s":
        try:
            return shared[int(raw_value)]
        except (ValueError, IndexError):
            return raw_value
    return raw_value


def _sheet_rows(root: ET.Element, shared: List[str]) -> List[List[str]]:
    rows: List[List[str]] = []
    for row in root.iter():
        if _local_name(row.tag) != "row":
            continue
        cells: Dict[int, str] = {}
        for cell in list(row):
            if _local_name(cell.tag) != "c":
                continue
            cell_ref = cell.attrib.get("r") or ""
            column = _column_index(cell_ref) if cell_ref else len(cells)
            cells[column] = _cell_value(cell, shared)
        if not cells:
            continue
        width = max(cells) + 1
        rows.append([cells.get(index, "") for index in range(width)])
    return rows


def _escape_table_cell(value: str) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|").strip()


def _markdown_table(rows: List[List[str]]) -> str:
    if not rows:
        return "_No tabular data extracted._"
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header = normalized[0]
    body = normalized[1:]
    lines = [
        "| " + " | ".join(_escape_table_cell(cell) for cell in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |")
    return "\n".join(lines)


def _cap_rows_and_columns(rows: List[List[str]], warnings: List[str], sheet_name: str) -> List[List[str]]:
    capped = rows
    if len(capped) > MAX_XLSX_ROWS:
        warnings.append(f"Sheet '{sheet_name}' was truncated to {MAX_XLSX_ROWS} rows.")
        capped = capped[:MAX_XLSX_ROWS]
    max_width = max((len(row) for row in capped), default=0)
    if max_width > MAX_XLSX_COLS:
        warnings.append(f"Sheet '{sheet_name}' was truncated to {MAX_XLSX_COLS} columns.")
        capped = [row[:MAX_XLSX_COLS] for row in capped]
    return capped


def normalize_xlsx(path: Path, title: str) -> Dict[str, Any]:
    warnings: List[str] = []
    sections: List[str] = [f"# {title}"]
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        sheets = _workbook_sheets(archive)
        if not sheets:
            warnings.append("No XLSX worksheets were found.")
        for sheet_name, sheet_path in sheets:
            try:
                root = _parse_xml_from_zip(archive, sheet_path)
            except KeyError:
                warnings.append(f"Worksheet '{sheet_name}' is missing ({sheet_path}).")
                continue
            rows = _cap_rows_and_columns(_sheet_rows(root, shared), warnings, sheet_name)
            sections.append(f"## Sheet: {sheet_name}")
            sections.append(_markdown_table(rows))
    return _normalize_result("xlsx", "\n\n".join(sections), warnings)


def normalize_office_file(path: Path, title: str) -> Dict[str, Any]:
    ext = path.suffix.lower()
    if ext == ".docx":
        return normalize_docx(path, title)
    if ext == ".pptx":
        return normalize_pptx(path, title)
    if ext in {".xlsx", ".xlsm"}:
        return normalize_xlsx(path, title)
    raise ValueError(f"Unsupported Office source format '{ext or '<none>'}'.")
