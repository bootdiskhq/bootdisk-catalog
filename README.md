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
- external preservation-manifest loading.

The goal of this first implementation is to prove that Bootdisk catalog data can be navigated correctly from authoritative JSON using stable IDs alone.
