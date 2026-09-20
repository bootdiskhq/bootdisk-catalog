# ADR-004: Local curator with a Catalog-owned write boundary

Status: accepted for 1.2 implementation; not yet implemented
Date: 2026-09-20

## Context

The public archive is a static, rebuildable projection. Stian needs an independent
curator before the next K-CD: evidence and suggestions beside editable claims,
followed by a single approve-and-next action. Frontend and Catalog must progress
in parallel without inventing competing sources of truth.

## Decision

Bootdisk Web owns a separate local curator page and its interaction design.
Bootdisk Catalog owns a local service, authoritative validation and all semantic
writes. The service extends/refactors the existing identification writer: that
writer currently refuses conflicting overwrites and is **not** already a revisioned
editing API. No frontend code writes catalog JSON or invents catalog record IDs.

The frontend consumes the versioned asynchronous adapter in
[curator-contract-v1.md](curator-contract-v1.md). Initially Claude implements a
fixture adapter and the screen; Codex implements Catalog persistence and the real
service adapter. Both implement the same calls and outcomes. Fixture mode is
visibly labelled and cannot claim to have saved real catalog data. An unavailable
real service must never silently fall back to fixture success.

Ingest retains immutable observations. Inspection reads mounted media without
running installers, adds hash-bound observations, and reports missing media,
unreadable files and unsupported formats explicitly. Publish retains asset
ownership. The curator never treats an entry-package hash as an individual file
hash (ADR-003), nor a filename as accepted product identity.

The local service serves the curator on the same loopback origin, checks the
expected origin and a session token for writes, and does not enable arbitrary
cross-origin access. Source paths are resolved through registered evidence, not
arbitrary paths supplied by a browser. Exact HTTP transport and service startup
are backend work; the adapter interface is the frontend handoff boundary.

The public release allowlist must exclude the curator, fixtures, draft state and
write service. Existing archive URLs and the public 1.0 projection contract remain
compatible. A new local build/start path is integrated later; do not silently add
a curator to the public release builder.

## Responsibility and delivery

- Claude: screen, accessible controls/focus, keyboard interaction, fixture adapter,
  frontend behavior tests and screenshots, in bootdisk-web only.
- Codex: review-state storage, semantic writer evolution, validation, evidence
  inspection, real adapter/service and integration tests, in bootdisk-catalog and
  the separately coordinated integration step.
- Stian: practical independent acceptance session; resolve product preferences.

Changes to this contract are a reviewed dependency PR before either side relies
on them. A frontend PR may be merged against fixtures, but 1.2 is not complete
until the real service passes the independent curation gate.

## Alternatives and consequences

Direct browser edits of catalog files would duplicate validation and make recovery
fragile. Browser storage alone would make accepted knowledge dependent on one
browser. A hosted editor would add deployment/account needs to a local workflow.
The chosen boundary keeps the public archive simple but introduces a local service
and an integration step. No framework migration, production deployment or second
catalog writer is part of the frontend assignment.
