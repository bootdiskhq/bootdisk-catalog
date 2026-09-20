from pathlib import Path
import unittest

from bootdisk_catalog.version import __version__


class VersionTests(unittest.TestCase):
    def test_development_version_markers_agree(self):
        version = (Path(__file__).parents[1] / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, "0.2.0-dev1")
        self.assertEqual(version, __version__)


if __name__ == "__main__":
    unittest.main()
