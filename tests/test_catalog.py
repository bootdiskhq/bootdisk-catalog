import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog, CatalogValidationError


SCHEMA = "bootdisk-catalog-0.1"
ARTIFACT_DIGEST = "a" * 64
MANIFEST_DIGEST = "b" * 64
ARTIFACT_ID = f"artifact:sha256:{ARTIFACT_DIGEST}"


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def write(self, relative_path, record):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record), encoding="utf-8")

    def valid_records(self):
        return {
            "software": {
                "schema": SCHEMA,
                "type": "software",
                "id": "software:winamp",
                "name": "Winamp",
            },
            "release": {
                "schema": SCHEMA,
                "type": "software_release",
                "id": "release:winamp:2.76",
                "software_id": "software:winamp",
                "version": "2.76",
                "display_name": "Winamp 2.76",
            },
            "artifact": {
                "schema": SCHEMA,
                "type": "artifact",
                "id": ARTIFACT_ID,
                "sha256": ARTIFACT_DIGEST,
                "size": 1234567,
            },
            "occurrence": {
                "schema": SCHEMA,
                "type": "occurrence",
                "id": "occurrence:kcd-15-2001:0018:winamp276",
                "artifact_id": ARTIFACT_ID,
                "source_ref": {
                    "manifest": f"sha256:{MANIFEST_DIGEST}",
                    "entry": "0018",
                    "path": "Tools/Winamp/winamp276_full.exe",
                },
            },
            "identification": {
                "schema": SCHEMA,
                "type": "identification",
                "id": "identification:artifact-a:winamp-2.76",
                "artifact_id": ARTIFACT_ID,
                "software_release_id": "release:winamp:2.76",
                "status": "curated",
                "distribution_kind": "demo",
                "evidence": [
                    {
                        "kind": "observed",
                        "source_ref": {
                            "manifest": f"sha256:{MANIFEST_DIGEST}",
                            "entry": "0018",
                        },
                        "field": "title",
                        "value": "WinAmp 2.76",
                    }
                ],
            },
            "description": {
                "schema": SCHEMA,
                "type": "description",
                "id": "description:release:winamp:2.76:nb-NO",
                "subject_id": "release:winamp:2.76",
                "language": "nb-NO",
                "text": "Winamp 2.76 er bevart som K37.",
                "status": "curated",
                "evidence": [
                    {
                        "kind": "curated",
                        "source_ref": {
                            "manifest": f"sha256:{MANIFEST_DIGEST}",
                            "entry": "0018",
                        },
                        "field": "normalized.title",
                        "value": "WinAmp 2.76",
                    }
                ],
            },
        }

    def write_valid_catalog(self):
        records = self.valid_records()
        # Paths are intentionally unrelated to IDs. Relationships must survive
        # arbitrary filesystem reorganization.
        self.write("somewhere/a.json", records["software"])
        self.write("elsewhere/b.json", records["release"])
        self.write("bytes/c.json", records["artifact"])
        self.write("history/d.json", records["occurrence"])
        self.write("claims/e.json", records["identification"])
        self.write("prose/f.json", records["description"])

    def test_loads_and_resolves_graph_by_id_not_path(self):
        self.write_valid_catalog()
        catalog = Catalog.load(self.root)

        releases = catalog.releases_for_software("software:winamp")
        self.assertEqual([r["id"] for r in releases], ["release:winamp:2.76"])

        artifacts = catalog.artifacts_for_release("release:winamp:2.76")
        self.assertEqual([a["id"] for a in artifacts], [ARTIFACT_ID])

        occurrences = catalog.occurrences_for_artifact(ARTIFACT_ID)
        self.assertEqual(
            [o["id"] for o in occurrences],
            ["occurrence:kcd-15-2001:0018:winamp276"],
        )

        identifications = catalog.identifications_for_artifact(ARTIFACT_ID)
        self.assertEqual(
            [i["id"] for i in identifications],
            ["identification:artifact-a:winamp-2.76"],
        )

        release = catalog.release_for_identification(
            "identification:artifact-a:winamp-2.76"
        )
        self.assertEqual(release["id"], "release:winamp:2.76")
        self.assertEqual(
            catalog.descriptions_for_subject("release:winamp:2.76")[0]["language"],
            "nb-NO",
        )

    def test_rejects_duplicate_ids_even_when_files_differ(self):
        software = self.valid_records()["software"]
        self.write("one.json", software)
        self.write("different/name.json", software)

        with self.assertRaisesRegex(CatalogValidationError, "duplicate catalog id"):
            Catalog.load(self.root)

    def test_rejects_broken_internal_reference(self):
        records = self.valid_records()
        records["release"]["software_id"] = "software:does-not-exist"
        self.write("software.json", records["software"])
        self.write("release.json", records["release"])

        with self.assertRaisesRegex(CatalogValidationError, "broken reference"):
            Catalog.load(self.root)

    def test_artifact_id_must_equal_content_identity(self):
        artifact = self.valid_records()["artifact"]
        artifact["id"] = f"artifact:sha256:{'c' * 64}"
        self.write("artifact.json", artifact)

        with self.assertRaisesRegex(
            CatalogValidationError, "artifact id must match sha256"
        ):
            Catalog.load(self.root)

    def test_source_reference_cannot_be_only_a_filesystem_path(self):
        records = self.valid_records()
        records["occurrence"]["source_ref"] = {
            "path": "Tools/Winamp/winamp276_full.exe"
        }
        self.write("artifact.json", records["artifact"])
        self.write("occurrence.json", records["occurrence"])

        with self.assertRaisesRegex(
            CatalogValidationError, "immutable sha256 reference"
        ):
            Catalog.load(self.root)

    def test_identification_requires_evidence(self):
        records = self.valid_records()
        records["identification"]["evidence"] = []
        self.write("software.json", records["software"])
        self.write("release.json", records["release"])
        self.write("artifact.json", records["artifact"])
        self.write("identification.json", records["identification"])

        with self.assertRaisesRegex(
            CatalogValidationError, "evidence must be a non-empty list"
        ):
            Catalog.load(self.root)

    def test_identification_rejects_unknown_distribution_kind(self):
        records = self.valid_records()
        records["identification"]["distribution_kind"] = "magazine-ish"
        self.write("software.json", records["software"])
        self.write("release.json", records["release"])
        self.write("artifact.json", records["artifact"])
        self.write("identification.json", records["identification"])

        with self.assertRaisesRegex(
            CatalogValidationError, "invalid identification distribution_kind"
        ):
            Catalog.load(self.root)

    def test_description_requires_evidence(self):
        records = self.valid_records()
        records["description"]["evidence"] = []
        self.write("software.json", records["software"])
        self.write("release.json", records["release"])
        self.write("description.json", records["description"])

        with self.assertRaisesRegex(
            CatalogValidationError, "description evidence must be a non-empty list"
        ):
            Catalog.load(self.root)

    def test_description_subject_must_be_software_or_release(self):
        records = self.valid_records()
        records["description"]["subject_id"] = ARTIFACT_ID
        self.write("artifact.json", records["artifact"])
        self.write("description.json", records["description"])

        with self.assertRaisesRegex(CatalogValidationError, "expected software or"):
            Catalog.load(self.root)


if __name__ == "__main__":
    unittest.main()
