import unittest

from bootdisk_catalog.catalog import SCHEMA
from bootdisk_catalog.contribution import (
    CONTRIBUTION_SCHEMA,
    contribution_from_bundle,
    validate_contribution,
)
from bootdisk_catalog.curation_bundle import BUNDLE_SCHEMA
from bootdisk_catalog.identify import IdentificationError


class ContributionTests(unittest.TestCase):
    def _bundle(self):
        return {
            "schema": BUNDLE_SCHEMA,
            "catalog_schema": SCHEMA,
            "records": [
                {"schema": SCHEMA, "type": "software", "id": "software:winamp", "name": "Winamp"}
            ],
        }

    def test_bundle_becomes_submitted_contribution_not_authoritative_curation(self):
        contribution = contribution_from_bundle(self._bundle())
        self.assertEqual(CONTRIBUTION_SCHEMA, contribution["schema"])
        self.assertEqual("submitted", contribution["status"])
        self.assertEqual("software:winamp", contribution["records"][0]["id"])
        self.assertEqual(1, validate_contribution(contribution))

    def test_rejects_reproducible_import_records(self):
        contribution = contribution_from_bundle(self._bundle())
        contribution["records"].append(
            {"schema": SCHEMA, "type": "artifact", "id": "artifact:sha256:" + "0" * 64}
        )
        with self.assertRaises(IdentificationError):
            validate_contribution(contribution)

    def test_rejects_duplicate_semantic_ids(self):
        contribution = contribution_from_bundle(self._bundle())
        contribution["records"].append(dict(contribution["records"][0]))
        with self.assertRaises(IdentificationError):
            validate_contribution(contribution)

    def test_upload_cannot_claim_reviewed_or_curated_status(self):
        contribution = contribution_from_bundle(self._bundle())
        contribution["status"] = "curated"
        with self.assertRaises(IdentificationError):
            validate_contribution(contribution)


if __name__ == "__main__":
    unittest.main()
