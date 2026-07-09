import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))

from gemini_source import build_gemini_prompt, normalize_with_gemini

SERVICE_ACCOUNT = {
    "type": "service_account",
    "client_email": "vertex@example.iam.gserviceaccount.com",
    "private_key": "unused",
    "project_id": "source-project",
}


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

    def test_vertex_normalizes_image_with_service_account_credentials(self):
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    "## Raw Extracted Content\n"
                                    "Visible text: Vertex source\n\n"
                                    "## AI Summary / Description\n"
                                    "A source normalized through Vertex.\n"
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
                env={
                    "VERTEX_SA_JSON": json.dumps(SERVICE_ACCOUNT),
                    "GEMINI_MODEL": "gemini-vertex",
                    "GOOGLE_CLOUD_LOCATION": "global",
                },
                transport=transport,
                access_token_provider=lambda _: "vertex-token",
            )

        self.assertEqual(normalized["kind"], "image")
        self.assertIn("Vertex source", normalized["raw_markdown"])
        self.assertEqual(normalized["provenance"]["normalizer"], "vertex")
        call = transport.calls[0]
        self.assertIn(
            "https://aiplatform.googleapis.com/v1/projects/source-project/locations/global/publishers/google/models/gemini-vertex:generateContent",
            call["url"],
        )
        self.assertEqual(call["headers"]["Authorization"], "Bearer vertex-token")
        self.assertNotIn("?key=", call["url"])
        inline = call["payload"]["contents"][0]["parts"][1]["inline_data"]
        self.assertEqual(inline["mime_type"], "image/jpeg")

    def test_vertex_normalizes_image_with_access_token(self):
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    "## Raw Extracted Content\n"
                                    "Token source\n\n"
                                    "## AI Summary / Description\n"
                                    "A source normalized with an access token.\n"
                                )
                            }
                        ]
                    }
                }
            ]
        }
        transport = FakeTransport(response)
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "scan.png"
            image.write_bytes(b"png")

            normalized = normalize_with_gemini(
                image,
                kind="image",
                title="Scan",
                env={
                    "VERTEX_ACCESS_TOKEN": "direct-token",
                    "GOOGLE_CLOUD_PROJECT": "direct-project",
                    "GEMINI_MODEL": "vertex-token-model",
                },
                transport=transport,
            )

        self.assertEqual(normalized["provenance"]["normalizer"], "vertex")
        call = transport.calls[0]
        self.assertIn("direct-project", call["url"])
        self.assertIn("vertex-token-model:generateContent", call["url"])
        self.assertEqual(call["headers"]["Authorization"], "Bearer direct-token")

    def test_gemini_missing_api_key_returns_actionable_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "chart.png"
            image.write_bytes(b"png")

            with self.assertRaises(ValueError) as raised:
                normalize_with_gemini(image, kind="image", title="Chart", env={})

        self.assertIn("GEMINI_API_KEY", str(raised.exception))
        self.assertIn("VERTEX_SA_JSON", str(raised.exception))
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
