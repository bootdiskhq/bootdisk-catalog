import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bootdisk_catalog import Catalog
from bootdisk_catalog.import_ingest import IngestImportError, import_manifest
from bootdisk_catalog.intake import LAUNCH_SCOPE, build_candidates, prepare_intake, main


def fixture():
    launcher = {"path": "Example/Setup.exe", "sha256": "a" * 64, "size": 100}
    return {"schema_version": "kcd-director-experimental-1", "file_inventory": [launcher],
            "entries": [{"source_id": "K1D1", "normalized": {
                "title": "Example 2000", "description": "DO NOT USE NORMALIZED REWRITE",
                "categories": ["programs"]},
                "interpretations": {"content_identity_scope": LAUNCH_SCOPE},
                "evidence": {"description_source": {"text": {"cp1252_view": "  Original omtale\r\n"}}},
                "issues": [], "files": {"referenced": {"direct_1": {
                    **launcher, "exists": True, "resolved_path": launcher["path"]}}, "inventory_refs": [launcher["path"]]},
                "content_identity": {"algorithm": "sha256", "file_count": 1}}]}


def encoded(value):
    return json.dumps(value).encode()


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_bytes(encoded(fixture()))
        self.output = self.root / "intake"

    def test_candidates_are_observations_not_claims(self):
        raw = self.manifest.read_bytes()
        result = prepare_intake(self.manifest, self.output)
        c = result["candidates"][0]
        self.assertEqual(c["key"], {"manifest": "sha256:" + hashlib.sha256(raw).hexdigest(), "entry": "K1D1"})
        self.assertEqual(c["observations"]["description"]["value"], "  Original omtale\r\n")
        self.assertEqual(c["observations"]["description"]["source_ref"]["pointer"],
                         "/entries/0/evidence/description_source/text/cp1252_view")
        self.assertTrue(all(v is None for v in c["claims"].values()))
        self.assertIsNone(c["decision"])
        self.assertIsNone(c["preservation"]["package_id"])
        self.assertEqual((self.output / "manifest.json").read_bytes(), raw)
        catalog = Catalog.load(self.output / "catalog")
        self.assertEqual(len(catalog.records_of_type("artifact")), 1)
        self.assertEqual(len(catalog.records_of_type("occurrence")), 1)
        for kind in ("package", "software", "software_release", "identification", "description"):
            self.assertEqual(catalog.records_of_type(kind), ())

    def test_direct_import_also_never_makes_director_packages(self):
        import_manifest(self.manifest, self.output)
        catalog = Catalog.load(self.output)
        self.assertEqual(catalog.records_of_type("package"), ())
        self.assertEqual(len(catalog.records_of_type("artifact")), 1)

    def test_resolved_casing_is_used_with_original_manifest_intact(self):
        m = fixture(); e = m["entries"][0]
        e["files"]["referenced"]["direct_1"]["path"] = "EXAMPLE/setup.EXE"
        self.manifest.write_bytes(encoded(m))
        prepare_intake(self.manifest, self.output)
        occurrence = Catalog.load(self.output / "catalog").records_of_type("occurrence")[0]
        self.assertEqual(occurrence["source_ref"]["path"], "Example/Setup.exe")
        self.assertEqual((self.output / "manifest.json").read_bytes(), encoded(m))

    def test_repeat_is_byte_identical_and_does_not_rewrite_files(self):
        first = prepare_intake(self.manifest, self.output)
        before = snapshot(self.output)
        mtimes = {p: p.stat().st_mtime_ns for p in self.output.rglob("*")}
        self.assertEqual(first, prepare_intake(self.manifest, self.output))
        self.assertEqual(before, snapshot(self.output))
        self.assertEqual(mtimes, {p: p.stat().st_mtime_ns for p in self.output.rglob("*")})

    def test_preserves_other_workspaces_and_rejects_edited_destination(self):
        workspace = self.root / "review"
        workspace.mkdir()
        state = b'{"draft":"unfinished", "events":["human approval"]}'
        (workspace / "review-state.json").write_bytes(state)
        prepare_intake(self.manifest, self.output)
        (self.output / "rapport.md").write_text("human notes")
        before = snapshot(self.output)
        for target in (workspace, self.output):
            with self.assertRaisesRegex(IngestImportError, "refusing to replace"):
                prepare_intake(self.manifest, target)
        self.assertEqual(before, snapshot(self.output))
        self.assertEqual((workspace / "review-state.json").read_bytes(), state)

    def test_changed_input_gets_new_identity_and_cannot_replace_snapshot(self):
        first = prepare_intake(self.manifest, self.output)
        self.manifest.write_bytes(self.manifest.read_bytes() + b"\n")
        with self.assertRaises(IngestImportError):
            prepare_intake(self.manifest, self.output)
        second = prepare_intake(self.manifest, self.root / "second")
        self.assertNotEqual(first["candidates"][0]["key"], second["candidates"][0]["key"])

    def test_shared_launchers_do_not_merge_candidates(self):
        m = fixture()
        second = copy.deepcopy(m["entries"][0]); second["source_id"] = "Spil1"
        second["normalized"]["title"] = "Other product"
        m["entries"].append(second)
        self.manifest.write_bytes(encoded(m))
        result = prepare_intake(self.manifest, self.output)
        catalog = Catalog.load(self.output / "catalog")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(len(catalog.records_of_type("artifact")), 1)
        self.assertEqual(len(catalog.records_of_type("occurrence")), 2)

    def test_conflicts_and_absent_description_are_preserved_without_guesses(self):
        m = fixture(); e = m["entries"][0]
        e["issues"] = ["conflicting_launch_targets", "missing_launch_file"]
        e["evidence"]["description_source"] = None
        result = build_candidates(encoded(m)); c = result["candidates"][0]
        self.assertEqual(c["source_issues"]["value"], e["issues"])
        self.assertIsNone(c["observations"]["description"])
        self.assertIn("description_not_selected", c["inspection_reasons"])
        self.assertEqual(result["summary"]["automatic_decisions"], 0)

    def test_no_launch_files_does_not_drop_candidate(self):
        m = fixture(); e = m["entries"][0]
        e["files"] = {"referenced": {"direct_1": {"exists": False, "is_file": False, "path": "absent.exe"}},
                      "inventory_refs": []}
        e["issues"] = ["missing_launch_file"]
        self.manifest.write_bytes(encoded(m))
        result = prepare_intake(self.manifest, self.output)
        self.assertEqual(result["summary"]["candidates"], 1)
        self.assertEqual(result["candidates"][0]["missing_references"][0]["value"], "absent.exe")
        self.assertEqual(Catalog.load(self.output / "catalog").records_of_type("artifact"), ())

    def test_bad_inputs_fail_without_publishing(self):
        mutations = [
            lambda m: m.update(schema_version="0.9"),
            lambda m: m["entries"].append(copy.deepcopy(m["entries"][0])),
            lambda m: m["entries"][0].update(source_id="../../escape"),
            lambda m: m["entries"][0]["files"]["referenced"].update({"../escape": {}}),
            lambda m: m["entries"][0]["interpretations"].clear(),
            lambda m: m["entries"][0]["files"].update(inventory_refs=[]),
            lambda m: m["file_inventory"][0].update(sha256="b" * 64),
            lambda m: m["entries"][0]["files"]["referenced"]["direct_1"].update(resolved_path="unobserved.exe"),
            lambda m: m["entries"][0]["files"]["referenced"]["direct_1"].update(is_file=False),
            lambda m: m["file_inventory"].append(copy.deepcopy(m["file_inventory"][0])),
            lambda m: m["entries"][0]["evidence"].update(description_source={"text": {}}),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                m = fixture(); mutation(m); self.manifest.write_bytes(encoded(m))
                with self.assertRaises(IngestImportError):
                    prepare_intake(self.manifest, self.output)
                self.assertFalse(self.output.exists())

    def test_import_failure_never_exposes_partial_intake(self):
        with patch("bootdisk_catalog.intake.import_manifest", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                prepare_intake(self.manifest, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".intake-*")), [])

    def test_existing_symlink_is_not_followed(self):
        target = self.root / "target"; target.mkdir()
        self.output.symlink_to(target, target_is_directory=True)
        with self.assertRaises(IngestImportError):
            prepare_intake(self.manifest, self.output)
        self.assertEqual(list(target.iterdir()), [])

    def test_concurrent_retries_publish_one_complete_snapshot(self):
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: prepare_intake(self.manifest, self.output), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(json.loads((self.output / "candidates.json").read_text()), results[0])
        self.assertEqual(list(self.root.glob(".intake-*")), [])

    def test_failed_publication_cleans_staging_and_retry_succeeds(self):
        with patch("bootdisk_catalog.intake.os.rename", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                prepare_intake(self.manifest, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".intake-*")), [])
        prepare_intake(self.manifest, self.output)

    def test_cli_accepts_snapshot_and_outputs_summary(self):
        with patch("builtins.print"):
            self.assertEqual(main([str(self.manifest), "--output", str(self.output)]), 0)


if __name__ == "__main__":
    unittest.main()
