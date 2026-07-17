import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))

from local_normalizers import normalize_docx, normalize_pptx, normalize_xlsx


def write_zip(path, files):
    with zipfile.ZipFile(path, "w") as archive:
        for name, body in files.items():
            archive.writestr(name, body)


class LocalNormalizerTests(unittest.TestCase):
    def test_docx_extractor_reads_document_paragraphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            docx = Path(tmp) / "report.docx"
            write_zip(
                docx,
                {
                    "word/document.xml": """
                    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                      <w:body>
                        <w:p><w:r><w:t>Executive summary</w:t></w:r></w:p>
                        <w:p><w:r><w:t>Revenue grew in Q3.</w:t></w:r></w:p>
                      </w:body>
                    </w:document>
                    """,
                },
            )

            normalized = normalize_docx(docx, "Report")

        self.assertEqual(normalized["kind"], "docx")
        self.assertIn("Executive summary", normalized["raw_markdown"])
        self.assertIn("Revenue grew in Q3.", normalized["raw_markdown"])
        self.assertEqual(normalized["warnings"], [])

    def test_pptx_extractor_reads_slide_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            pptx = Path(tmp) / "slides.pptx"
            write_zip(
                pptx,
                {
                    "ppt/slides/slide1.xml": """
                    <p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                           xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                      <p:cSld><p:spTree>
                        <p:sp><p:txBody>
                          <a:p><a:r><a:t>Quarterly Revenue</a:t></a:r></a:p>
                          <a:p><a:r><a:t>North region grew.</a:t></a:r></a:p>
                        </p:txBody></p:sp>
                      </p:spTree></p:cSld>
                    </p:sld>
                    """,
                    "ppt/slides/slide2.xml": """
                    <p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                           xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                      <p:cSld><p:spTree>
                        <p:sp><p:txBody><a:p><a:r><a:t>Risks</a:t></a:r></a:p></p:txBody></p:sp>
                      </p:spTree></p:cSld>
                    </p:sld>
                    """,
                },
            )

            normalized = normalize_pptx(pptx, "Slides")

        self.assertEqual(normalized["kind"], "pptx")
        self.assertIn("## Slide 1", normalized["raw_markdown"])
        self.assertIn("Quarterly Revenue", normalized["raw_markdown"])
        self.assertIn("## Slide 2", normalized["raw_markdown"])
        self.assertIn("Risks", normalized["raw_markdown"])

    def test_xlsx_extractor_reads_sheet_as_markdown_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = Path(tmp) / "table.xlsx"
            write_zip(
                xlsx,
                {
                    "xl/sharedStrings.xml": """
                    <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                      <si><t>Region</t></si>
                      <si><t>Revenue</t></si>
                      <si><t>North</t></si>
                      <si><t>42</t></si>
                    </sst>
                    """,
                    "xl/workbook.xml": """
                    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                      <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
                    </workbook>
                    """,
                    "xl/_rels/workbook.xml.rels": """
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
                    </Relationships>
                    """,
                    "xl/worksheets/sheet1.xml": """
                    <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                      <sheetData>
                        <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
                        <row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row>
                      </sheetData>
                    </worksheet>
                    """,
                },
            )

            normalized = normalize_xlsx(xlsx, "Workbook")

        self.assertEqual(normalized["kind"], "xlsx")
        self.assertIn("## Sheet: Sheet1", normalized["raw_markdown"])
        self.assertIn("| Region | Revenue |", normalized["raw_markdown"])
        self.assertIn("| North | 42 |", normalized["raw_markdown"])


if __name__ == "__main__":
    unittest.main()
