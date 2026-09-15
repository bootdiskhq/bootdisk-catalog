from pathlib import Path
import unittest


class VersionTests(unittest.TestCase):
    def test_release_candidate_version_marker(self):
        version = (Path(__file__).parents[1] / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, "0.1.0-rc1")


if __name__ == "__main__":
    unittest.main()
