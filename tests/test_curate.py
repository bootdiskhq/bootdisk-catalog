import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog
from bootdisk_catalog.curate import curation_queue, format_curation_queue


SCHEMA = "bootdisk-catalog-0.1"
ARTIFACT_DIGEST = "a" * 64
ARTIFACT_ID = f"artifact:sha256:{ARTIFACT_DIGEST}"


class CurationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        self.root = self.workspace / "catalog"
        self.root.mkdir()

        # The ingest manifest is an external evidence source, not a Catalog record.
        # Keep it outside the catalog root so Catalog.load() never mistakes it for
        # authoritative catalog JSON while recursively discovering records.
        self.manifest_path = self.workspace / "ingest.json"

        manifest = {
            "entries": [
                {"source_id": "K1", "normalized": {"title": "Program One 1.0"}},
                {"source_id": "K2", "normalized": {"title": "Program Two 2.0"}},
            ]
        }
        raw = json.dumps(manifest, indent=2).encode("utf-8") + b"\n"
        self.manifest_path.write_bytes(raw)
        self.manifest_ref = f"sha256:{hashlib.sha256(raw).hexdigest()}"

        for directory in (
            "artifacts",
            "occurrences",
            "software",
            "releases",
            "identifications",
        ):
            (self.root / directory).mkdir()

        self._write(
            "artifacts/artifact.json",
            {
                "schema": SCHEMA,
                "type": "artifact",
                "id": ARTIFACT_ID,
                "sha256": ARTIFACT_DIGEST,
                "size": 123,
            },
        )

        # Deliberately reuse the exact same Artifact in two editorial entries. Curation
        # state must follow evidence source, not accidentally leak across the hash.
        for entry in ("K1", "K2"):
            self._write(
                f"occurrences/{entry}.json",
                {
                    "schema": SCHEMA,
                    "type": "occurrence",
                    "id": f"occurrence:{self.manifest_ref[7:]}:{entry}:installer",
                    "artifact_id": ARTIFACT_ID,
                    "source_ref": {
                        "manifest": self.manifest_ref,
                        "entry": entry,
                        "path": f"{entry}/Setup.exe",
                    },
                },
            )

        self._write(
            "software/one.json",
            {
                "schema": SCHEMA,
                "type": "software",
                "id": "software:one",
                "name": "Program One",
            },
        )
        self._write(
            "releases/one.json",
            {
                "schema": SCHEMA,
                "type": "software_release",
                "id": "release:one:1.0",
                "software_id": "software:one",
                "version": "1.0",
            },
        )
        self._write(
            "identifications/one.json",
            {
                "schema": SCHEMA,
                "type": "identification",
                "id": f"identification:{'c' * 64}",
                "artifact_id": ARTIFACT_ID,
                "software_release_id": "release:one:1.0",
                "status": "curated",
                "evidence": [
                    {
                        "kind": "observed",
                        "source_ref": {
                            "manifest": self.manifest_ref,
                            "entry": "K1",
                        },
                        "field": "normalized.title",
                        "value": "Program One 1.0",
                    }
                ],
            },
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, relative_path, record):
        path = self.root / relative_path
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    def test_queue_marks_only_evidence_source_as_identified(self):
        queue = curation_queue(Catalog.load(self.root), self.manifest_path)

        self.assertEqual(queue[0]["entry"], "K1")
        self.assertEqual(queue[0]["status"], "identified")
        self.assertEqual(queue[1]["entry"], "K2")
        self.assertEqual(queue[1]["status"], "pending")
        self.assertEqual(queue[1]["occurrences"][0]["artifact_id"], ARTIFACT_ID)

    def test_pending_view_preserves_editorial_title_as_review_context(self):
        queue = curation_queue(Catalog.load(self.root), self.manifest_path)
        text = format_curation_queue(queue, pending_only=True)

        self.assertNotIn("K1", text)
        self.assertIn("K2  [pending]  Program Two 2.0", text)
        self.assertIn("K2/Setup.exe", text)


if __name__ == "__main__":
    unittest.main()
