# Bootdisk Catalog 0.1 release candidate

The 0.1 release candidate is intentionally small. Its purpose is to provide a
stable semantic layer that a prototype frontend can consume without making the
Catalog responsible for preservation or publication.

## Required vertical slice

The release candidate is ready when the repository can:

1. import explicit preserved observations from an ingest manifest;
2. load and validate the JSON-first Catalog graph;
3. review one manifest or one exact source entry without inferring identity;
4. create an explicit evidence-backed Software/Release Identification;
5. derive a software-centered presentation view from authoritative JSON;
6. run the complete unit-test suite automatically for every pull request.

## Frontend boundary

The prototype frontend should treat the repositories as separate inputs:

- **Ingest** supplies source/editorial observations and original file provenance.
- **Catalog** supplies semantic software identity and evidence-backed relationships.
- **Publish** supplies web-safe published assets and derivatives such as thumbnails.

Catalog does not copy icons, screenshots, installers, or thumbnails into its own
records. A frontend projection may join those inputs, but the join is disposable;
the authoritative evidence remains in the component outputs.

## Deliberately deferred

The 0.1 release candidate does not require:

- package/distribution grouping;
- numeric ordering of source entry IDs;
- automatic software identification;
- publisher/developer/platform/language metadata;
- a database;
- frontend-specific reverse indexes stored as authoritative data.

These can be added when real presentation or preservation requirements justify
them rather than speculatively expanding the domain model.
