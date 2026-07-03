import importlib
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mofa-notebook-data-table" / "src"))


SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string"}},
    "required": ["title"],
}


class RecordingTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, headers, payload):
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        return self.response


class LlmClientTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(
            importlib.util.find_spec("llm_client"),
            "llm_client must implement internal provider calls",
        )
        return importlib.import_module("llm_client")

    def test_gemini_uses_structured_output_and_parses_fenced_json(self):
        module = self.module()
        transport = RecordingTransport(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "```json\n{\"title\":\"Grounded\"}\n```"}
                            ]
                        }
                    }
                ]
            }
        )
        client = module.GeminiClient(
            api_key="gemini-secret",
            model="gemini-test",
            base_url="https://gemini.example/v1beta/",
            transport=transport,
        )

        result = client.generate("Use sources", SCHEMA)

        self.assertEqual(result, {"title": "Grounded"})
        call = transport.calls[0]
        self.assertEqual(
            call["url"],
            "https://gemini.example/v1beta/models/gemini-test:generateContent?key=gemini-secret",
        )
        self.assertEqual(
            call["payload"]["generationConfig"]["responseMimeType"],
            "application/json",
        )
        self.assertEqual(
            call["payload"]["generationConfig"]["responseSchema"],
            SCHEMA,
        )

    def test_openai_uses_json_schema_and_bearer_auth(self):
        module = self.module()
        transport = RecordingTransport(
            {
                "choices": [
                    {"message": {"content": "{\"title\":\"Grounded\"}"}}
                ]
            }
        )
        client = module.OpenAIClient(
            api_key="openai-secret",
            model="openai-test",
            base_url="https://openai.example/v1/",
            transport=transport,
        )

        result = client.generate("Use sources", SCHEMA)

        self.assertEqual(result, {"title": "Grounded"})
        call = transport.calls[0]
        self.assertEqual(
            call["url"],
            "https://openai.example/v1/chat/completions",
        )
        self.assertEqual(call["headers"]["Authorization"], "Bearer openai-secret")
        self.assertEqual(call["payload"]["response_format"]["type"], "json_schema")
        self.assertFalse(
            call["payload"]["response_format"]["json_schema"]["strict"]
        )
        self.assertEqual(
            call["payload"]["response_format"]["json_schema"]["schema"],
            SCHEMA,
        )

    def test_factory_prefers_explicit_provider_then_gemini(self):
        module = self.module()
        env = {
            "GEMINI_API_KEY": "gemini-secret",
            "OPENAI_API_KEY": "openai-secret",
        }

        explicit = module.create_llm_client(
            {"provider": "openai", "model": "chosen"},
            env=env,
            transport=RecordingTransport({}),
        )
        automatic = module.create_llm_client(
            {},
            env=env,
            transport=RecordingTransport({}),
        )

        self.assertIsInstance(explicit, module.OpenAIClient)
        self.assertEqual(explicit.model, "chosen")
        self.assertIsInstance(automatic, module.GeminiClient)

    def test_factory_uses_environment_override_and_reports_missing_key(self):
        module = self.module()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "No supported model credential"):
                module.create_llm_client({})

        client = module.create_llm_client(
            {},
            env={
                "MOFA_DATA_TABLE_PROVIDER": "openai",
                "MOFA_DATA_TABLE_MODEL": "env-model",
                "OPENAI_API_KEY": "openai-secret",
            },
            transport=RecordingTransport({}),
        )
        self.assertIsInstance(client, module.OpenAIClient)
        self.assertEqual(client.model, "env-model")


if __name__ == "__main__":
    unittest.main()
