# Frontend prototype handoff

The first prototype can begin from one known-good vertical slice: K37 / Winamp 2.76.

Catalog can emit the semantic/source card with:

```bash
python -m bootdisk_catalog.presentation \
  ~/Projects/bootdisk/data/catalog/kcd15-2001 \
  ~/Projects/bootdisk/data/kcd15-2001-manifest.json \
  --entry K37
```

The frontend should then join the occurrence/source observations to the
`bootdisk-publish` output for browser-safe icon and screenshot derivatives.

A useful first page needs only:

- editorial/source title;
- curated Software name and version when identified;
- icon derivative;
- screenshot derivative;
- source/publication context;
- preserved/download object only when Publish policy allows it.

Pending entries may still be shown from editorial context if the UI labels them as
unreviewed rather than silently treating the editorial title as curated identity.
