import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))
sys.path.insert(0, str(ROOT / "mofa-notebook-video-overview" / "src"))

from notebook_source import handle_tool as source_tool
from notebook_video_overview import GeminiVeoClient, VertexVeoClient, create_video_client, handle_tool, video_overview_generate


class FakeLlmClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, prompt, schema):
        self.calls.append({"prompt": prompt, "schema": schema})
        return self.response


class FakeVideoClient:
    def __init__(self):
        self.calls = []

    def generate_video(self, prompt, output_path, **params):
        self.calls.append({"prompt": prompt, "output_path": output_path, "params": params})
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake mp4 bytes")
        return {
            "operation_name": "operations/fake-video",
            "model": "veo-3.1-generate-preview",
            **params,
            "video_uri": "https://example.test/fake.mp4",
        }


class NotebookVideoOverviewTests(unittest.TestCase):
    def make_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        (workspace / "uploads").mkdir()
        (workspace / "uploads" / "report.md").write_text(
            "# Market Report\n\nRevenue grew in enterprise accounts.\n\n## Risks\n\nSupply chain risk increased for hardware.\n\n## Opportunity\n\nExpansion improved in APAC.",
            encoding="utf-8",
        )
        source_tool(
            "source_import",
            {"workspace": str(workspace), "path": "uploads/report.md", "title": "Market Report"},
        )
        return tmp, workspace

    def overview_response(self):
        return {
            "title": "Market Brief",
            "style": "executive",
            "duration_minutes": 3,
            "script_sections": [
                {
                    "heading": "Growth signal",
                    "narration": "Revenue grew in enterprise accounts.",
                    "citation_chunk_ids": ["market-report#chunk-0001"],
                }
            ],
            "scenes": [
                {
                    "scene": 1,
                    "type": "evidence",
                    "visual": "Revenue growth card",
                    "narration": "Show enterprise revenue growth.",
                    "citation_chunk_ids": ["market-report#chunk-0001"],
                },
                {
                    "scene": 2,
                    "type": "risk",
                    "visual": "Hardware risk card",
                    "narration": "Show supply chain risk for hardware.",
                    "citation_chunk_ids": ["market-report#chunk-0002"],
                },
            ],
            "asset_brief": {
                "tone": "executive",
                "assets": [
                    {
                        "name": "Revenue card",
                        "description": "Card showing enterprise growth.",
                        "citation_chunk_ids": ["market-report#chunk-0001"],
                    }
                ],
            },
            "handoff_notes": ["Keep citations visible on evidence cards."],
        }

    def test_video_overview_generate_uses_llm_and_writes_script_scene_plan_and_asset_brief(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        llm = FakeLlmClient(self.overview_response())
        video = FakeVideoClient()

        result = video_overview_generate(
            {"workspace": str(workspace), "title": "Market Brief", "duration_minutes": 3, "style": "executive"},
            llm_client=llm,
            video_client=video,
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(len(video.calls), 1)
        self.assertIn("Generate a source-grounded video overview", llm.calls[0]["prompt"])
        self.assertIn("market-report#chunk-0001", llm.calls[0]["prompt"])
        script = workspace / result["data"]["script_path"]
        scenes = workspace / result["data"]["scene_plan_path"]
        brief = workspace / result["data"]["asset_brief_path"]
        handoff = workspace / result["data"]["handoff_path"]
        video_path = workspace / result["data"]["video_path"]
        veo_prompt = workspace / result["data"]["veo_prompt_path"]
        self.assertTrue(script.is_file())
        self.assertTrue(scenes.is_file())
        self.assertTrue(brief.is_file())
        self.assertTrue(handoff.is_file())
        self.assertTrue(video_path.is_file())
        self.assertTrue(veo_prompt.is_file())
        self.assertIn("Revenue grew in enterprise accounts", script.read_text(encoding="utf-8"))
        self.assertIn("Market Report (notebook-sources/market-report/source.md:", script.read_text(encoding="utf-8"))
        scene_data = json.loads(scenes.read_text(encoding="utf-8"))
        self.assertEqual(scene_data["title"], "Market Brief")
        self.assertEqual(scene_data["scenes"][1]["type"], "risk")
        self.assertIn("mofa-slides", handoff.read_text(encoding="utf-8"))
        self.assertIn("mofa-fm", handoff.read_text(encoding="utf-8"))
        self.assertIn("Revenue grew in enterprise accounts", veo_prompt.read_text(encoding="utf-8"))
        self.assertIn(str(script.resolve()), result["files_to_send"])
        self.assertIn(str(video_path.resolve()), result["files_to_send"])

    def test_video_overview_generate_honors_selected_sources_in_llm_prompt(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        (workspace / "uploads" / "notes.md").write_text("# Notes\n\nOnboarding improved.", encoding="utf-8")
        source_tool(
            "source_import",
            {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"},
        )
        llm = FakeLlmClient(
            {
                **self.overview_response(),
                "script_sections": [
                    {"heading": "Notes", "narration": "Onboarding improved.", "citation_chunk_ids": ["notes#chunk-0001"]}
                ],
                "scenes": [
                    {"scene": 1, "type": "evidence", "visual": "Notes card", "narration": "Show onboarding.", "citation_chunk_ids": ["notes#chunk-0001"]}
                ],
                "asset_brief": {"tone": "clear", "assets": [{"name": "Notes card", "description": "Show onboarding.", "citation_chunk_ids": ["notes#chunk-0001"]}]},
            }
        )

        result = video_overview_generate({"workspace": str(workspace), "source_ids": ["notes"], "render_video": False}, llm_client=llm)

        self.assertTrue(result["success"], result)
        self.assertIn("notes#chunk-0001", llm.calls[0]["prompt"])
        self.assertNotIn("market-report#chunk-0001", llm.calls[0]["prompt"])

    def test_rejects_model_citations_that_are_not_in_notebook_sources(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        bad = self.overview_response()
        bad["script_sections"][0]["citation_chunk_ids"] = ["missing#chunk-9999"]
        result = video_overview_generate({"workspace": str(workspace)}, llm_client=FakeLlmClient(bad))

        self.assertFalse(result["success"])
        self.assertIn("cites unknown chunk", result["output"])

    def test_render_video_false_writes_plan_without_calling_video_client(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        llm = FakeLlmClient(self.overview_response())
        video = FakeVideoClient()

        result = video_overview_generate(
            {"workspace": str(workspace), "render_video": False},
            llm_client=llm,
            video_client=video,
        )

        self.assertTrue(result["success"], result)
        self.assertFalse(result["data"]["render_video"])
        self.assertNotIn("video_path", result["data"])
        self.assertEqual(video.calls, [])

    def test_gemini_veo_client_starts_polls_and_downloads_video(self):
        calls = []

        def transport(url, headers, payload, method):
            calls.append({"url": url, "headers": headers, "payload": payload, "method": method})
            if method == "POST":
                return 200, json.dumps({"name": "models/veo-3.1-generate-preview/operations/abc"}).encode("utf-8")
            if method == "GET" and url.endswith("operations/abc"):
                return 200, json.dumps({
                    "done": True,
                    "response": {
                        "generateVideoResponse": {
                            "generatedSamples": [{"video": {"uri": "https://files.example/video.mp4"}}]
                        }
                    },
                }).encode("utf-8")
            if method == "GET" and url == "https://files.example/video.mp4":
                return 200, b"video-bytes"
            raise AssertionError(f"unexpected request {method} {url}")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "overview.mp4"
            client = GeminiVeoClient("key", base_url="https://generativelanguage.googleapis.com/v1beta", transport=transport)
            metadata = client.generate_video(
                "make a video",
                output,
                duration_seconds=8,
                aspect_ratio="9:16",
                resolution="720p",
                poll_interval_secs=1,
                timeout_secs=5,
            )

            self.assertEqual(output.read_bytes(), b"video-bytes")
            self.assertEqual(metadata["operation_name"], "models/veo-3.1-generate-preview/operations/abc")
            self.assertEqual(calls[0]["payload"]["parameters"]["aspectRatio"], "9:16")
            self.assertEqual(calls[0]["payload"]["parameters"]["durationSeconds"], "8")
            self.assertEqual(calls[-1]["headers"]["x-goog-api-key"], "key")

    def test_vertex_veo_client_starts_polls_and_downloads_gcs_video(self):
        calls = []

        def transport(url, headers, payload, method):
            calls.append({"url": url, "headers": headers, "payload": payload, "method": method})
            if method == "POST" and url.endswith(":predictLongRunning"):
                self.assertEqual(headers["Authorization"], "Bearer vertex-token")
                self.assertEqual(payload["parameters"]["storageUri"], "gs://video-bucket/out/")
                self.assertEqual(payload["parameters"]["sampleCount"], 1)
                return 200, json.dumps({"name": "projects/proj/locations/us-central1/operations/abc"}).encode("utf-8")
            if method == "POST" and url.endswith(":fetchPredictOperation"):
                self.assertEqual(payload["operationName"], "projects/proj/locations/us-central1/operations/abc")
                return 200, json.dumps({
                    "done": True,
                    "response": {
                        "videos": [{"gcsUri": "gs://video-bucket/out/sample_0.mp4", "mimeType": "video/mp4"}]
                    },
                }).encode("utf-8")
            if method == "GET" and url == "https://storage.googleapis.com/storage/v1/b/video-bucket/o/out%2Fsample_0.mp4?alt=media":
                self.assertEqual(headers["Authorization"], "Bearer vertex-token")
                return 200, b"vertex-video-bytes"
            raise AssertionError(f"unexpected request {method} {url}")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "overview.mp4"
            client = VertexVeoClient(
                {"client_email": "test@example.test", "private_key": "unused", "project_id": "proj"},
                access_token_provider=lambda _: "vertex-token",
                model="veo-3.1-generate-001",
                location="us-central1",
                transport=transport,
            )
            metadata = client.generate_video(
                "make a video",
                output,
                duration_seconds=8,
                aspect_ratio="16:9",
                resolution="720p",
                poll_interval_secs=1,
                timeout_secs=5,
                output_gcs_uri="gs://video-bucket/out/",
            )

            self.assertEqual(output.read_bytes(), b"vertex-video-bytes")
            self.assertEqual(metadata["provider"], "vertex")
            self.assertEqual(metadata["model"], "veo-3.1-generate-001")
            self.assertEqual(metadata["video_uri"], "gs://video-bucket/out/sample_0.mp4")
            self.assertTrue(calls[0]["url"].endswith("/publishers/google/models/veo-3.1-generate-001:predictLongRunning"))

    def test_create_video_client_uses_notebook_video_model_override(self):
        client = create_video_client(
            {},
            env={
                "GEMINI_API_KEY": "key",
                "MOFA_NOTEBOOK_VIDEO_MODEL": "custom-veo",
                "GEMINI_BASE_URL": "https://example.test/v1beta",
            },
            transport=lambda *args: (200, b"{}"),
        )

        self.assertEqual(client.model, "custom-veo")
        self.assertEqual(client.base_url, "https://example.test/v1beta")

    def test_create_video_client_uses_vertex_when_vertex_credentials_are_configured(self):
        client = create_video_client(
            {},
            env={
                "VERTEX_ACCESS_TOKEN": "vertex-token",
                "GOOGLE_CLOUD_PROJECT": "proj",
                "GOOGLE_CLOUD_LOCATION": "us-central1",
            },
            transport=lambda *args: (200, b"{}"),
        )

        self.assertIsInstance(client, VertexVeoClient)
        self.assertEqual(client.model, "veo-3.1-generate-001")
        self.assertEqual(client.project, "proj")
        self.assertEqual(client.location, "us-central1")

    def test_empty_manifest_returns_clear_error_before_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("video_overview_generate", {"workspace": tmp})

            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])

    def test_main_runs_when_installed_without_repo_common(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            installed_skill = root / "installed-skills" / "mofa-notebook-video-overview"
            installed_skill.parent.mkdir()
            shutil.copytree(ROOT / "mofa-notebook-video-overview", installed_skill)

            completed = subprocess.run(
                [str(installed_skill / "main"), "video_overview_generate"],
                input=json.dumps({"workspace": str(workspace)}),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 1)
            result = json.loads(completed.stdout)
            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])
            self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
