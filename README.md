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

## Reviewing the curation queue

`bootdisk_catalog.curate` joins an exact ingest manifest to the catalog's immutable Occurrence and Identification evidence. It is a review surface: editorial titles are shown as context, but are never promoted to Software identity automatically.

```bash
python -m bootdisk_catalog.curate \
  /path/to/catalog \
  /path/to/ingest-manifest.json
```

Each ingest entry is shown as `pending` or `identified`, together with its preserved Artifact occurrences and source paths. To concentrate on unfinished work:

```bash
python -m bootdisk_catalog.curate \
  /path/to/catalog \
  /path/to/ingest-manifest.json \
  --pending
```

Curation state is tied to the Identification's evidence source (`manifest` + `entry`), not merely to an Artifact hash. This is deliberate: byte-identical generic files such as `Setup.exe` can occur in unrelated editorial entries without causing one entry's interpretation to leak into another.

`--json` emits the same queue as structured data for future interactive tooling. This first workflow step remains read-only; semantic claims are still committed explicitly with `bootdisk_catalog.identify`.

## Adding explicit software identifications

`bootdisk_catalog.identify` adds semantic catalog interpretation only when a curator supplies it explicitly. It does not infer software identity from a filename, hash or editorial title.

The command starts from an existing Artifact and one of its Occurrences. The Occurrence anchors the evidence to the immutable ingest-manifest identity and source entry. The curator then supplies stable Software and SoftwareRelease identities plus the source field/value supporting the interpretation.

Example for a curated Winamp 2.76 identification:

```bash
python -m bootdisk_catalog.identify \
  /path/to/catalog \
  --artifact artifact:sha256:b609c58ca767f0809fe30775e2dd9f28315f85f2972196b2a5aca4a84a2964ad \
  --entry K37 \
  --software-id software:winamp \
  --software-name Winamp \
  --release-id release:winamp:2.76 \
  --version 2.76 \
  --field normalized.title \
  --value "WinAmp 2.76"
```

This creates or safely reuses:

- `Software` (`software:winamp`);
- `SoftwareRelease` (`release:winamp:2.76`);
- an evidence-bearing `Identification` from the Artifact to that release.

The source field is recorded as `observed` evidence, while the semantic conclusion remains separately marked as `curated` (or `interpreted` when requested). Re-running the same identification is idempotent; conflicting existing records are never silently overwritten.

## Preserving curated knowledge

Artifacts and Occurrences can be rebuilt from an Ingest manifest. `Software`, `SoftwareRelease` and `Identification` records represent human interpretation and cannot safely be reconstructed by inference. They must therefore be preserved separately before a generated Catalog tree is discarded or rebuilt.

Export the semantic records into a versioned curation bundle:

```bash
python -m bootdisk_catalog.curation_bundle export \
  /path/to/catalog \
  /path/to/curation/source.json
```

A complete rebuild is then deliberately two-stage:

```bash
python -m bootdisk_catalog.import_ingest \
  /path/to/ingest-manifest.json \
  --output /path/to/catalog

python -m bootdisk_catalog.curation_bundle restore \
  /path/to/catalog \
  /path/to/curation/source.json
```

The bundle contains only semantic records; reproducible Artifact and Occurrence records are not duplicated into it. Restore preflights the entire bundle before writing and refuses conflicting existing semantic records, then reloads the complete Catalog graph for validation.

This gives the Catalog two explicit preservation inputs:

```text
Ingest manifest   -> observed Artifacts and Occurrences
Curation bundle   -> Software, Releases and Identifications
                         |
                         v
                  reconstructed Catalog
```

The curation bundle is preservation data, not disposable build output. A working Catalog directory may be regenerated, but the bundle should be retained and versioned alongside the source collection's other preservation metadata.

Repository-owned reference bundles live under `data/curation/`, named for the preserved source collection. These files are reviewed and versioned like code. The test suite restores each reference bundle over a minimal regenerated observation graph and verifies its stable semantic identities. The first reference bundle is `data/curation/kcd15-2001.json`, whose acceptance record is K37 identified as Winamp 2.76.

## Viewing cataloged software

`bootdisk_catalog.view` derives a software-centered presentation from the authoritative catalog graph. It does not write new catalog facts and can always be rebuilt from the JSON records.

Human-readable view:

```bash
python -m bootdisk_catalog.view \
  /path/to/catalog \
  software:winamp
```

Example shape:

```text
Software:
  Winamp (software:winamp)

Release:
  2.76 (release:winamp:2.76)

Artifact:
  artifact:sha256:b609c58ca767f0809fe30775e2dd9f28315f85f2972196b2a5aca4a84a2964ad
  size: 2229552

Occurrence:
  entry: K37
  path:  WinAmp/WinAmp276_full.exe
```

The same derived projection can be emitted as JSON for tooling or a future presentation layer:

```bash
python -m bootdisk_catalog.view \
  /path/to/catalog \
  software:winamp \
  --json
```

This keeps presentation concerns separate from catalog truth while giving command-line tools and future frontends one consistent traversal of `Software -> SoftwareRelease -> Artifact -> Occurrence`.

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
- a frontend;
- source-format parsing;
- automatic software identification;
- external preservation-manifest semantic resolution beyond immutable references.

The goal is to keep the catalog boundary explicit: ingest tells Catalog what was observed; Catalog adds interpretation without rewriting preservation evidence.

## Source-entry packages

Whole-manifest import also reconstructs `package` records from entry inventory
references when present. Use `--package package:sha256:... --manifest MANIFEST`
instead of `--artifact` when identifying a multi-file source entry. A package and
an individual file are separate identities; shared installer launchers do not imply
shared software identity. See [ADR-003](docs/adr-003-source-entry-packages.md) for
scope, validation, compatibility, and why an entry package includes editorial files.

## Next release: independent curation

The [1.2.0 curator delivery gate](docs/curation-next-step.md) must pass before the
next K-CD import. The [K-CD 15/2001 review audit](docs/kcd15-2001-remaining-work.md)
records unresolved claims and media exceptions for all 39 entries.

## Review backend development release

Catalog `0.2.0-dev1` supplies the transactional review workspace for Bootdisk 1.2.
See [setup, guarantees and remaining integration work](docs/review-workspace-dev1.md).
The HTTP service and live browser adapter are still pending.
