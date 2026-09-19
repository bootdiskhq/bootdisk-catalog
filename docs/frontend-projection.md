# Frontend projection

`bootdisk_catalog.presentation` builds disposable source-entry cards by joining an
exact ingest manifest to the evidence-backed Catalog graph.

```bash
python -m bootdisk_catalog.presentation \
  /path/to/catalog \
  /path/to/ingest-manifest.json
```

Use `--entry K37` for one source entry or `--identified` to emit only entries with
semantic Catalog identity.

The JSON projection exposes:

- source entry ID;
- editorial title as source context;
- curation state;
- identified Software and SoftwareRelease records when present;
- curated, language-tagged descriptions for identified releases;
- the identified artifact's distribution kind when known (`full`, `demo`,
  `trial`, `update` or `unknown`);
- preserved Artifact IDs and source paths.

Draft descriptions remain in the authoritative Catalog but are deliberately omitted
from this publication-facing projection.

The projection deliberately contains source paths rather than invented web URLs.
`bootdisk-publish` remains responsible for publication policy, stable published
objects and web derivatives such as thumbnails. The prototype frontend can join
Catalog presentation cards to Publish output without either component taking
ownership of the other's facts.

This file is documentation of a disposable view, not a new authoritative schema.
