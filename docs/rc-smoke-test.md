# 0.1.0-rc1 smoke test

Run against the K-CD 15/2001 reference dataset after pulling the release-candidate branch.

```bash
python -m unittest discover -s tests -v

python -m bootdisk_catalog.curate \
  ~/Projects/bootdisk/data/catalog/kcd15-2001 \
  ~/Projects/bootdisk/data/kcd15-2001-manifest.json \
  --entry K37

python -m bootdisk_catalog.presentation \
  ~/Projects/bootdisk/data/catalog/kcd15-2001 \
  ~/Projects/bootdisk/data/kcd15-2001-manifest.json \
  --entry K37
```

Expected semantic checks:

- the full test suite is green;
- K37 is `identified`, not `pending`;
- K37 retains editorial title `WinAmp 2.76` as source context;
- the presentation projection resolves K37 to `software:winamp` and
  `release:winamp:2.76`;
- the projection still exposes preserved occurrence paths for later joining to
  Publish assets.

Do not treat source paths in the projection as public URLs. Published assets and
thumbnail URLs belong to `bootdisk-publish`.

## Validation record

The reference run passed on 2026-09-16:

- 153 Artifacts imported;
- 164 Occurrences imported;
- three curated semantic records restored;
- K37 restored as identified Winamp 2.76;
- Identification ID remained
  `identification:97e260274a5258dae047c0f6294ee1da53b50d22a3f5e588e41da8b23aef5f04`.

The repository-owned curation bundle is also covered by
`tests/test_reference_curation.py` so later changes cannot silently invalidate the
acceptance record.
