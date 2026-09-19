import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog import Catalog
from bootdisk_catalog.catalog import CatalogValidationError
from bootdisk_catalog.import_ingest import import_manifest, IngestImportError
from bootdisk_catalog.identify import create_identification, IdentificationError
from bootdisk_catalog.curation_bundle import export_bundle, restore_bundle
from bootdisk_catalog.curate import curation_queue
from bootdisk_catalog.view import software_view


def fixture():
    shared = hashlib.sha256(b"generic launcher").hexdigest()
    inventory = []
    entries = []
    for entry, folder in [("K5", "Bugnosis"), ("K17", "Panorama Factory")]:
        files = [{"path": folder + "/Setup.exe", "sha256": shared, "size": 16},
                 {"path": folder + "/data.cab", "sha256": hashlib.sha256(folder.encode()).hexdigest(), "size": len(folder)}]
        digest = hashlib.sha256("".join(f["path"] + "\0" + f["sha256"] + "\n" for f in sorted(files, key=lambda f:f["path"])).encode()).hexdigest()
        inventory.extend(files)
        entries.append({"source_id": entry, "normalized": {"title": folder},
            "files": {"referenced": {"installer": dict(files[0], exists=True, is_file=True)},
                      "inventory_refs": [f["path"] for f in files]},
            "content_identity": {"algorithm": "sha256", "file_count": 2,
                                 "total_size": 16 + len(folder), "manifest_sha256": digest}})
    return {"entries": entries, "file_inventory": inventory}


class PackageTests(unittest.TestCase):
    def test_shared_launcher_does_not_become_software_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "manifest.json"
            manifest = fixture(); source.write_text(json.dumps(manifest))
            catalog_root = root / "catalog"; import_manifest(source, catalog_root)
            package_id = "package:sha256:" + manifest["entries"][0]["content_identity"]["manifest_sha256"]
            create_identification(catalog_root, artifact_id=package_id, entry="K5",
                manifest_path=source, software_id="software:bugnosis", software_name="Bugnosis",
                release_id="release:bugnosis:unknown", version="unknown",
                evidence_field="normalized.title", evidence_value="Bugnosis")
            catalog = Catalog.load(catalog_root)
            self.assertEqual(len(catalog.records_of_type("artifact")), 3)
            self.assertEqual(len(catalog.records_of_type("package")), 2)
            self.assertEqual([e["status"] for e in curation_queue(catalog, source)], ["identified", "pending"])
            view = software_view(catalog, "software:bugnosis")["releases"][0]
            self.assertEqual(view["artifacts"], [])
            self.assertEqual(view["packages"][0]["id"], package_id)
            rebuilt = root / "rebuilt"; import_manifest(source, rebuilt)
            restore_bundle(rebuilt, export_bundle(catalog))
            self.assertEqual(curation_queue(Catalog.load(rebuilt), source), curation_queue(catalog, source))
            with self.assertRaises(IdentificationError):
                create_identification(catalog_root, artifact_id=package_id, entry="K17",
                    manifest_path=source, software_id="software:wrong", software_name="Wrong",
                    release_id="release:wrong:unknown", version="unknown", evidence_field="title", evidence_value="Wrong")

    def test_inventory_corruption_is_rejected(self):
        for mutation in ("hash", "missing", "duplicate", "size"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); m = copy.deepcopy(fixture())
                if mutation == "hash": m["file_inventory"][1]["sha256"] = "0" * 64
                if mutation == "missing": m["file_inventory"].pop(1)
                if mutation == "duplicate": m["entries"][0]["files"]["inventory_refs"].append("Bugnosis/Setup.exe")
                if mutation == "size": m["entries"][0]["content_identity"]["total_size"] += 1
                path = root / "manifest.json"; path.write_text(json.dumps(m))
                with self.assertRaises((IngestImportError, CatalogValidationError)):
                    import_manifest(path, root / "catalog")
