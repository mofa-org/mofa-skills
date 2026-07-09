import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))

from gemini_source import build_gemini_prompt, normalize_with_gemini


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, headers, payload):
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        return self.response


class GeminiSourceTests(unittest.TestCase):
    def test_gemini_normalizes_image_response_into_raw_and_summary_markdown(self):
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    "## Raw Extracted Content\n"
                                    "Visible label: Q3 Revenue\n\n"
                                    "## AI Summary / Description\n"
                                    "A chart describing Q3 revenue growth.\n\n"
                                    "## Warnings / Limitations\n"
                                    "- Low resolution image."
                                )
                            }
                        ]
                    }
                }
            ]
        }
        transport = FakeTransport(response)
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "chart.jpg"
            image.write_bytes(b"\xff\xd8\xff\xe0fakejpeg")

            normalized = normalize_with_gemini(
                image,
                kind="image",
                title="Revenue Chart",
                env={"GEMINI_API_KEY": "gemini-secret", "GEMINI_MODEL": "gemini-test"},
                transport=transport,
            )

        self.assertEqual(normalized["kind"], "image")
        self.assertIn("Visible label", normalized["raw_markdown"])
        self.assertIn("Q3 revenue growth", normalized["summary_markdown"])
        self.assertEqual(normalized["warnings"], ["Low resolution image."])
        self.assertIn("## Raw Extracted Content", normalized["source_markdown"])
        call = transport.calls[0]
        self.assertIn("models/gemini-test:generateContent", call["url"])
        inline = call["payload"]["contents"][0]["parts"][1]["inline_data"]
        self.assertEqual(inline["mime_type"], "image/jpeg")
        self.assertEqual(base64.b64decode(inline["data"]), b"\xff\xd8\xff\xe0fakejpeg")

    def test_gemini_missing_api_key_returns_actionable_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "chart.png"
            image.write_bytes(b"png")

            with self.assertRaises(ValueError) as raised:
                normalize_with_gemini(image, kind="image", title="Chart", env={})

        self.assertIn("GEMINI_API_KEY", str(raised.exception))
        self.assertIn("image", str(raised.exception))

    def test_gemini_prompt_requests_raw_and_summary_sections(self):
        prompt = build_gemini_prompt(Path("chart.png"), kind="image", title="Chart")

        lowered = prompt.lower()
        self.assertIn("raw extracted text", lowered)
        self.assertIn("semantic summary", lowered)
        self.assertIn("tables", lowered)
        self.assertIn("warnings", lowered)
        self.assertIn("markdown", lowered)


if __name__ == "__main__":
    unittest.main()
