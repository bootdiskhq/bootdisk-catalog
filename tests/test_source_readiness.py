import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest

from bootdisk_catalog.source_readiness import assess_manifest, title_evidence


class SourceReadinessTests(unittest.TestCase):
    def manifest(self, issues=()):
        return {"schema_version": "0.9", "source": {"sections": {
            "K1": {"Titel": "Ad-aware", "Global": "AdAware fjerner reklameprogrammer."}}},
            "entries": [{"source_id": "K1", "raw": {
                "Titel": "Ad-aware", "Global": "AdAware fjerner reklameprogrammer."},
                "normalized": {"title": "Ad-aware"}, "issues": list(issues),
                "files": {"referenced": {"installer": {"path": "Setup.exe", "exists": True}}}}]}

    def assess(self, manifest):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"manifest.json"
            path.write_text(json.dumps(manifest))
            before = path.read_bytes()
            result = assess_manifest(path)["K1"]
            self.assertEqual(path.read_bytes(), before)
            return result

    def test_source_name_does_not_require_exact_repeat_in_prose(self):
        result = self.assess(self.manifest())
        self.assertEqual(result["status"], "documented")
        self.assertEqual(result["machine_tasks"], [])
        self.assertEqual(result["human_questions"], [])
        self.assertNotIn("version", result)

    def test_conflict_retained_without_invalidating_source_title(self):
        result = self.assess(self.manifest(["conflicting_launch_targets"]))
        self.assertEqual(result["status"], "documented")
        self.assertEqual(result["file_association"]["status"], "conflict")
        self.assertEqual(result["machine_tasks"], ["inspect_file_association"])

    def test_missing_file_is_not_missing_identity_or_human_question(self):
        manifest = self.manifest(["missing_launch_file"])
        manifest["entries"][0]["files"]["referenced"]["installer"]["exists"] = False
        result = self.assess(manifest)
        self.assertEqual(result["status"], "documented")
        self.assertEqual(result["file_association"]["missing"], ["Setup.exe"])
        self.assertEqual(result["human_questions"], [])

    def test_unknown_issue_still_requires_machine_inspection(self):
        result = self.assess(self.manifest(["new_parser_problem"]))
        self.assertIn("inspect_unknown_source_issue", result["machine_tasks"])
        self.assertEqual(result["status"], "needs_inspection")

    def test_changed_normalized_title_is_not_documented(self):
        manifest = self.manifest()
        manifest["entries"][0]["normalized"]["title"] = "Different product"
        self.assertEqual(self.assess(manifest)["status"], "needs_inspection")

    def test_changed_raw_title_is_not_documented(self):
        manifest = self.manifest()
        manifest["entries"][0]["raw"]["Titel"] = "Different product"
        self.assertEqual(self.assess(manifest)["status"], "needs_inspection")

    def test_director_preserved_bytes_and_whitespace(self):
        text = "Dance eJay\r\r"
        manifest = {"schema_version": "kcd-director-experimental-1"}
        entry = {"normalized": {"title": "Dance eJay"}, "evidence": {"selection": {
            "title": {"base64": base64.b64encode(text.encode()).decode(), "cp1252_view": text}}}}
        self.assertIsNotNone(title_evidence(manifest, entry))
        broken = copy.deepcopy(entry)
        broken["evidence"]["selection"]["title"]["cp1252_view"] = "Other"
        self.assertIsNone(title_evidence(manifest, broken))

    def test_course_does_not_need_executable(self):
        manifest = self.manifest()
        manifest["entries"][0]["files"]["referenced"] = {"run": {"path": "Course.pdf", "exists": True}}
        self.assertEqual(self.assess(manifest)["machine_tasks"], [])

    def test_explained_missing_alternative_retains_source_warning(self):
        from test_file_association import FileAssociationTests
        manifest = self.manifest()
        manifest['entries'][0].update(FileAssociationTests().alternative())
        result = self.assess(manifest)
        self.assertEqual(result['file_association']['status'], 'observed')
        self.assertEqual(result['file_association']['missing'], ['old.exe'])
        self.assertIn('missing_launch_file', result['file_association']['issues'])
        self.assertFalse(result['file_association']['runtime_verified'])
        self.assertEqual(result['machine_tasks'], [])
        self.assertEqual(result['status'], 'documented')
        self.assertEqual(result['human_questions'], [])

    def test_unknown_schema_has_no_title_binding(self):
        manifest = self.manifest()
        manifest["schema_version"] = "future"
        self.assertIsNone(title_evidence(manifest, manifest["entries"][0]))
