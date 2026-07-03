import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RegistryGenerationTests(unittest.TestCase):
    def test_registry_includes_notebook_skill_directories(self):
        output = subprocess.check_output(
            [sys.executable, str(ROOT / "scripts" / "gen-registry.py")],
            cwd=ROOT,
            text=True,
        )
        registry = json.loads(output)
        skills = registry[0]["skills"]

        self.assertIn("mofa-slides", skills)
        self.assertIn("notebook-source", skills)
        self.assertIn("notebook-video-overview", skills)


if __name__ == "__main__":
    unittest.main()
