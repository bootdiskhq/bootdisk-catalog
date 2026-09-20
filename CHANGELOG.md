# Changelog

## 0.2.0-dev1 — backend foundation for Bootdisk 1.2

- Isolated, atomic review workspace with durable drafts, queues and resume bookmarks.
- Explicit approval through the Catalog writer, revision conflicts, idempotent retry and compensating undo.
- Append-only decision history, full-workspace backup/restore and approved-only catalog export.
- CLI/Python entry point; HTTP service and browser adapter are not implemented yet.
- First bootstrap requires one existing identification and Norwegian release description per entry.

## Earlier unreleased documentation

- Hash-bound 39-entry review audit with unresolved identity, version and distribution fields.
- Explicit 1.2.0 human-curation delivery gate before the next K-CD import.
- Gentee payload boundary triage and remaining media/extraction exceptions.

## 0.1.0-rc1

First Bootdisk Catalog release candidate.

- JSON-first stable-ID catalog graph and validation
- whole-manifest import of explicit preserved file observations
- Artifact deduplication with independent source Occurrences
- explicit evidence-backed Software/Release Identification
- evidence-aware curation queue and focused entry review
- software-centered derived view
- frontend-oriented disposable presentation projection
- automated pull-request unit tests
- portable export and conflict-safe restore of curated semantic knowledge
- versioned K-CD 15/2001 reference curation bundle
- automated reference rebuild preserving K37 as Winamp 2.76

The release candidate deliberately keeps source parsing in Ingest and publication
assets/derivatives in Publish. It does not introduce a database or automatic
software identification.
