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

## Release requirement: source category as content-kind evidence

Required for 1.2.0, reported during Stian's curator acceptance session: content kind
can currently appear as “Belagt” without the original CD category being available
among the readable evidence choices. Generic checked sources do not explain that
classification. Implemented in the local workspace and curator; final user acceptance of the additions remains.

- **Catalog owns the change.** Expose the preserved original CD category as a source
  observation, with its exact wording and source-entry provenance. Link the
  content-kind assessment to that observation and retain an explicit rationale
  for mapping the CD category to Catalog's content kind. Do not silently equate
  broad CD categories with a specific content kind.
- **Ingest:** first verify where the original category is already preserved. Reuse
  it without changing existing manifests; change ingest only if preservation is
  incomplete.
- **Web:** show “Kategori på CD-en: <original category>” in readable evidence beside
  the content-kind assessment. Make the original category and the curator's
  interpretation visibly distinct; keep technical identifiers in details.
- **Existing workspaces:** audit inherited “Belagt” content-kind claims for an
  inspectable basis. Surface missing support as unresolved/requiring review; do
  not overwrite user drafts, decisions or history during migration. A title or
  other source can support an assessment when the reasoning is explicit; the
  presence of a category is not a universal prerequisite for manual curation.
- **Publish:** no change expected unless implementation reveals a projection need.

Acceptance: for a game entry, Stian can see the original CD category, understand
why it supports “Spill”, and select that evidence. Also test a broad/ambiguous
category and an entry without category evidence: neither is automatically marked
“Belagt”. Verify evidence links and rationale survive save, approval, restart and
export, and existing user work survives migration. Deliver through the normal
PR/test/review/green-CI merge workflow before the 1.2.0 release.

## Release requirement: distribution evidence

The same 1.2.0 release gate applies to distribution (demo, full, trial, update,
unknown). Show the preserved CD statement that supports the assessment, not just
an evidence ID or unrelated checked observations. Implemented locally; final user acceptance remains.

The existing ingest parser preserves raw `Licens` as `normalized.license` and
`Global` as `normalized.description`. The preserved K13 description explicitly
calls MechCommander 2 a demo; other entries have Freeware/Shareware license values
or no license value. Do not assume the CD supplies a definitive edition for every
entry. Freeware/Shareware describe licensing and do not by themselves establish
full/demo/trial distribution.

- **Catalog:** expose original license statements and relevant CD description,
  README or installer text as attributable evidence. Preserve original wording;
  link the distribution assessment to the supporting observation and rationale.
  Keep license and distribution as separate concepts. Missing or contradictory
  evidence requires an explicit unresolved assessment rather than a guessed edition.
- **Web:** display readable labels such as “Lisens oppgitt på CD-en: Freeware” and
  the actual demo/trial/full statement beside distribution evidence choices.
- **Ingest/Publish:** reuse preserved observations; only extend ingest if relevant
  original information is missing. No publish change expected.
- Audit inherited “Belagt” distribution claims with the same protection for user
  drafts, decisions and history as the category-evidence requirement above.

Acceptance: verify an explicit demo statement (K13), a Freeware/Shareware statement
without decisive edition evidence, missing information and conflicting sources.
No automatic promotion from a license label to full/demo/trial. Check readable
provenance, selection, rationale, approval, restart/export and migration preservation.
Deliver with the category-evidence work before 1.2.0 through PR/test/review/green CI.

Hosted curation is separately gated by [ADR-006](adr-006-hosted-curator-access.md).
The local release does not open curator access on the internet.

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
