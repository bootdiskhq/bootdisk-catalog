# bootdisk-catalog

Catalog identity, interpretation and relationship model for Bootdisk.

This repository is the component home for the catalog domain defined by the project-level architecture decisions in `bootdiskhq/bootdisk`.

## Core rule

Catalog relationships are expressed through stable record IDs, never through JSON filenames or directory paths.

```text
software:winamp
        ^
        |
release:winamp:2.76
        ^
        |
identification:...
        |
        v
artifact:sha256:...
        |
        v
occurrence:...
```

JSON records are authoritative. Filesystem layout is only an organizational convenience.

Reverse relationships are derived in memory and are not duplicated into authoritative JSON. A future database, search index or frontend projection may be generated from the JSON catalog, but remains disposable unless a later ADR changes that decision.

## What the implementation does

`bootdisk_catalog.Catalog` currently:

- recursively loads JSON catalog records;
- validates schema, record type and stable ID form;
- rejects duplicate catalog IDs;
- verifies that an Artifact ID matches its SHA-256 content identity;
- resolves and type-checks internal references;
- requires Occurrence and Identification evidence to use immutable manifest content references rather than local filesystem identity;
- provides simple in-memory navigation in both forward and reverse directions.

The implementation intentionally uses only the Python standard library.

## Importing ingest observations

`bootdisk_catalog.import_ingest` is the preservation-to-catalog bridge. Its normal mode consumes the complete ingest manifest and imports every explicit preserved regular-file observation under `files.referenced` and `files.discovered`.

For each observation it creates:

- an `Artifact` from observed SHA-256 and size;
- an `Occurrence` describing where that artifact was observed.

Artifacts naturally deduplicate by SHA-256. If the same bytes occur in several entries or roles, the catalog contains one Artifact and separate Occurrences for each observation.

Declared missing/non-file observations are not converted to Artifacts because no preserved byte identity exists. Structurally invalid observations fail the import rather than being silently ignored.

The importer does **not** create `Software`, `SoftwareRelease` or `Identification` records. Those are catalog interpretation and must be added with evidence rather than inferred from filenames or titles.

The importer addresses the source manifest by the SHA-256 of the exact manifest file. Local manifest filenames and directories therefore do not become catalog identity.

Normal whole-manifest import:

```bash
python -m bootdisk_catalog.import_ingest \
  /path/to/ingest-manifest.json \
  --output /path/to/catalog
```

For focused debugging, `--entry` and `--file` may be supplied together:

```bash
python -m bootdisk_catalog.import_ingest \
  /path/to/ingest-manifest.json \
  --entry K24 \
  --file installer \
  --output /path/to/catalog
```

The output is written beneath `artifacts/` and `occurrences/` and is reloaded through `Catalog` for graph validation before the command succeeds.

## Running the tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

No virtual environment or package installation is required.

## Deliberately not implemented

This component does not currently provide:

- a database;
- an ORM;
- an HTTP API;
- a search engine;
- a frontend projection;
- source-format parsing;
- automatic software identification;
- external preservation-manifest semantic resolution beyond immutable references.

The goal is to keep the catalog boundary explicit: ingest tells Catalog what was observed; Catalog adds interpretation without rewriting preservation evidence.
