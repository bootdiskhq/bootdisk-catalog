import unittest


class ReleaseCandidateSmokeTests(unittest.TestCase):
    def test_public_workflow_modules_import(self):
        # Keep the release-candidate command surface importable as one vertical slice.
        import bootdisk_catalog.curate  # noqa: F401
        import bootdisk_catalog.identify  # noqa: F401
        import bootdisk_catalog.import_ingest  # noqa: F401
        import bootdisk_catalog.presentation  # noqa: F401
        import bootdisk_catalog.view  # noqa: F401


if __name__ == "__main__":
    unittest.main()
