# 1.2.0: independent, fast human curation

**Delivery gate: this workflow must be usable before importing the next K-CD.**
The read-only archive preview is not the curator. This replaces the earlier plan
that treated curator UI as optional polish. This is planned work, not functionality
already delivered by 1.1.0-rc2.

## One screen, one decision, next entry

Start with a queue of unresolved entries. Keep source title/description, package
members, readable evidence and editable interpretation together. Pre-fill proposals
with their reasons; do not make the user reconstruct the investigation or edit JSON.
Offer **Approve and next**, **Save changes and next**, **Skip for now**, and **Undo**.
Return to the same position after reopening. Show remaining entries and unresolved
fields separately: a confirmed identity can still have an unknown version.

Provide keyboard shortcuts with visible hints, predictable focus and no firing while
typing in an input. Autosave drafts locally with visible saved/error state; explicit
approval writes authoritative catalog claims. An interrupted save must never show a
false success or lose edits. Skipping preserves the draft and a reason, and keeps the
entry discoverable. Undo restores the previous decision while retaining the history.

Identity, version, content kind and distribution are separate decisions. Keep
`unknown` available. A curator must be able to finish a review with documented
uncertainty; unsupported installers must not block the rest of a disc. Do not label
an entry fully resolved merely because its identity is curated. Do not bulk-accept
unsupported guesses. License observations remain evidence, not an invented full/demo
classification.

## Delivery sequence and ownership

1. **Catalog: review state and write contract.** Define drafts, per-field unresolved
   reasons, deferred items and decision history. Reuse the existing identification
   writer and validation; extend its artifact/package target support, rather than
   introducing a second semantic writer. Reject stale writes, preserve previous
   evidence and make undo auditable. Review state must not mutate ingest manifests.
2. **Ingest/inspection: reusable observations.** Read from mounted media with read
   permissions. Start with text/INI, executable metadata and supported archive members.
   Bind every result to source hash and member/offset. Report unreadable files and
   unsupported compression as structured outcomes. Cache by source hash and inspector
   version. Apply size/time limits and safe member paths; never execute installer code.
   Gentee support is a follow-up decoder candidate, with dependency/license review.
3. **Web plus local service: working curator.** Add the queue and evidence/decision
   screen, drafts, explicit save, shortcuts, next/skip/undo and recovery. The static
   public archive stays a projection; the local service owns catalog writes. Handle
   disconnected service and missing/unmounted media with actionable messages.
4. **Integration and release.** Rebuild the published view from accepted catalog
   decisions, verify evidence links, exercise the complete flow on K-CD 15/2001, and
   deliver via PR, tests, review and green-CI merge. No next-disc import until the
   acceptance session below passes.

## Acceptance session with Stian

- Starting from the normal app, independently find and curate an unresolved entry;
  no terminal, assistant, JSON or Git editing is required.
- Verify a suggested claim against readable source evidence, correct one field,
  approve it and automatically reach the next unresolved entry.
- Skip an opaque installer, locate it again, and see the retained reason/draft.
- Close/reopen with an unfinished edit; recover it. Undo an accepted decision and
  confirm the previous values and evidence history remain available.
- Exercise unreadable DATA1.CAB, unavailable media, failed saves and a stale concurrent
  edit. No silent lost work, automatic promotion or false complete-disc claim.
- Review ten representative entries, including simple and difficult ones. Record
  elapsed time, clicks, keyboard use and interruptions. For a prefilled, adequately
  supported proposal, approval and advance require one action. Set the practical
  speed target with Stian after this measured session; deep research time is separate.
- Rebuild the archive and confirm accepted changes survive restart/export/restore;
  drafts and skipped proposals must not appear as approved catalog truth.

## Real-disc regression cases

Use the [39-entry audit](kcd15-2001-remaining-work.md), not invented happy-path data:
CPU-Z's generic PE version versus product 1.10; Icebreaker's source versus binary
version; Font Xplorer Lite freeware versus full distribution; Bille/Trille demo
symbols; collection/course entries; Gentee and unknown installer formats; shared
launcher hashes versus whole-package identity; and the unreadable CAB.

The [payload review](kcd15-2001-payload-review.md) records the current investigation.
The JSON review snapshot is a planning input, not the future review-state schema.

## Parallel implementation handoff

[ADR-004](adr-004-local-curator-boundary.md) assigns frontend and service ownership.
[ADR-005](adr-005-review-state-and-decisions.md) fixes the draft/decision semantics.
The [v1 adapter contract](curator-contract-v1.md) and
[real-entry fixtures](curator-fixtures-v1.json) let frontend work start independently.
Claude's work order lives in bootdisk-web: `docs/claude-curator-work-order.md`.
