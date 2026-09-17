# ADR 001: Curated descriptions are catalog knowledge

Status: accepted

## Context

Ingest can reproduce observed files and editorial metadata, but it cannot reproduce
human-written program descriptions. Keeping prose only in a generated presentation
or in the web application would therefore make it disappear during a full rebuild.

## Decision

A description is a first-class `description` record in the Catalog. It:

- targets either a `software` or `software_release` record through `subject_id`;
- carries an explicit language tag and review status;
- contains non-empty evidence tied to an immutable ingest-manifest digest;
- is included in curation export, restore and contribution validation;
- is never generated from filenames or editorial titles without human review.

`draft` means the prose is still under editorial review. `curated` means both the
wording and its evidence have been reviewed. Presentation and web layers may choose
which statuses and languages to publish, but they must not become the authoritative
store for the prose.

## Consequences

Descriptions survive a complete Catalog rebuild together with identities and
releases. The first reference record describes Winamp 2.76 in Norwegian and is
anchored to the same preserved K37 observation as its identification. Richer claims
or external research will require additional preserved evidence before they can be
marked curated.
