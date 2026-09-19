# ADR 002: Public metadata is versioned in Git

Status: accepted

## Context

Bootdisk separates descriptions of preserved material from the material itself.
Program identities, versions, descriptions, evidence and checksums are useful as an
open dataset and must remain reviewable and reproducible as more K-CDs are added.
Binary files and web derivatives have different storage, licensing and delivery
requirements and do not belong in the Catalog repository.

## Decision

All public Catalog metadata and human curation is committed to Git. This includes:

- software and release identities;
- descriptions, categories and known license metadata;
- evidence-bearing identifications;
- source-entry references, file sizes and cryptographic hashes;
- the curated bundles required to rebuild Catalog state.

The website does not depend on live GitHub requests in the browser. A versioned
build reads a specific Catalog commit together with an Ingest manifest and a Publish
manifest, validates their references, and emits static frontend JSON. Bootdisk.no
hosts that generated presentation data plus published binary assets and derivatives.

Every release records the Catalog commit and the digests of its Ingest and Publish
inputs. A release must therefore be reproducible without treating the deployed
website as an authoritative metadata store.

## Consequences

Metadata can be reviewed, corrected, forked and cited independently of bootdisk.no.
The public site remains fast and operational when GitHub is unavailable. Adding a
new K-CD exercises the same data contracts rather than introducing runtime coupling
or disc-specific frontend code.
