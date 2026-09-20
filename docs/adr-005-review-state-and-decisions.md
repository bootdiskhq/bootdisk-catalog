# ADR-005: Drafts, explicit decisions and append-only review history

Status: accepted for 1.2 implementation; not yet implemented
Date: 2026-09-20

## Context

35 of 39 identities on K-CD 15/2001 are curated, yet 36 entries have an unresolved
field. One completion flag would hide uncertainty. Frequent saves and rapid
navigation must not lose work, publish guesses, or overwrite a newer decision.

## Decision

Review state is a separate persisted Catalog-side workspace keyed by immutable
manifest digest plus entry ID. It is not embedded in the source manifest or the
public projection. Drafts and history survive restart and are included in an
explicit review-workspace backup/restore format, separate from the existing
semantic curation bundle. That backup extension is backend implementation work.

Each entry has an opaque revision, queue state (`pending`, `deferred`, `reviewed`),
a draft, current accepted interpretation, open-field reasons and decision history.
Queue state describes this review pass; catalog `interpreted`/`curated` describes
identity confidence. Neither replaces the other. Reviewing an entry with an
unknown version is allowed; the open-field queue continues to expose it.

Identity, version, content kind, distribution and description are independently
reviewable claims. Proposals and accepted values stay visibly distinct. `unknown`
and an explanation are valid; UI must not coerce them to a guess. Distribution
has the existing values `full`, `demo`, `trial`, `update`, `unknown`; freeware does
not automatically mean `full`. No new catalog `not_applicable` enum is introduced
by the frontend; explain collection/version cases in the reason field.

Autosave persists only a draft. Both “Godkjenn og neste” and “Lagre og neste”
explicitly commit the reviewed claims (the second label is used after edits).
Skipping preserves the latest draft, requires a defer reason and advances only
after acknowledgment. A reviewed entry may retain provisional identity if the
curator explicitly retains uncertainty. Identity is promoted only by an explicit
supported identity decision, not by approving another field.

Every mutation includes the expected revision and a unique operation ID. Backend
checks the operation ID before the revision: an exact retry returns the original
receipt, while reuse with another payload is an error. Stale writes return a
conflict with current state, leave the local draft intact and require a deliberate
reconciliation. No blind overwrite or silent last-write-wins behavior.

An approved decision atomically persists the validated semantic change, resulting
review state and an append-only history event (previous/new claims, source evidence,
reason, actor and server timestamp). Only acknowledge once durable. On failure,
retain the old accepted state and the draft. Shared software/release edits must
not silently change other entries: this first contract allows only updates the
backend can resolve without an ambiguous shared-record edit; otherwise reject
with `shared_record_conflict` for a separate resolution workflow.

Undo is a new compensating event, not deletion. It targets the latest reversible
semantic decision for this entry, requires the current revision and revalidates
shared-record dependencies. Restore previous accepted claims, preserve the current
draft, and return the entry to pending. If later/shared edits make reversal unsafe,
report a conflict. Autosaves do not erase the last reversible decision. Server
supplies the allowed undo action; frontend must not reconstruct it from timestamps.

## Consequences and verification

Browser edits need ordered saves, visible dirty/saving/saved/error states and stable
operation IDs on network retries. Approval must flush the latest draft first;
navigation waits for successful receipt. Evidence is retained even when a claim is
reversed. Drafts/deferred claims never become published truth through a rebuild.

Test restart recovery, timeouts after a committed write, stale tabs, failed writes,
shared-record conflicts, skip with unsaved edits, and undo after autosave. Full-disc
completeness remains separate: reviewing FirstPage cannot clear its unreadable CAB.
See [adapter contract](curator-contract-v1.md) and [acceptance gate](curation-next-step.md).
