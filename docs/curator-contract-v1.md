# Curator adapter contract v1

Status: agreed implementation target for 1.2; no live API exists yet.
Owner: Catalog. Frontend may implement this exact interface against fixtures.
Schema discriminator: `bootdisk-curator-v1`. Additive fields are allowed; changing
required fields or semantics requires a coordinated new version.

## Asynchronous interface

Every method returns a Promise. Inputs/outputs are JSON-compatible. `key` is
`{manifest: "sha256:<64 lowercase hex>", entry: "K23"}`. IDs/revisions are opaque.
Frontend must not derive record IDs or hash data to create authoritative IDs.

| Method | Input | Successful result |
| --- | --- | --- |
| `getQueue` | `{manifest, filter}`; filter `pending`, `deferred`, `open_fields`, `all` | `{schema, items, resume_key}` |
| `getEntry` | `{key}` | entry document described below |
| `saveDraft` | `{key, expected_revision, operation_id, draft}` | mutation receipt |
| `defer` | `{key, expected_revision, operation_id, reason}` | receipt; latest saved draft retained, queue state deferred |
| `approve` | `{key, expected_revision, operation_id}` | receipt; atomically approves the saved draft, queue state reviewed |
| `undo` | `{key, expected_revision, operation_id, decision_id}` | receipt; restores preceding accepted claims, queue state pending |
| `setResume` | `{key}` | `{schema, resume_key}`; idempotent convenience bookmark only |

Queue is numerically ordered by entry within the manifest. Each item has `key`,
`title`, `queue_state`, `identification_status` (`interpreted`, `curated`, or null),
`open_fields` (claim-name array). These are current server-derived values. There
is no pagination in v1. `resume_key` is nullable; if filtered out, use the first
item and do not change its review status. Counts describe the loaded filter.

A mutation receipt is `{schema, operation_id, entry, decision_id}`. `entry` is a
fresh full entry document, including the new revision; `decision_id` is null for
draft/defer, the new event ID for approve/undo. After successful approve/defer,
refresh the queue and open the next higher entry in the active filter, wrap to
its first entry if needed, or show queue complete when empty. Undo stays on the
restored entry. Never advance after a rejected or uncertain mutation.

Serialize writes per entry. Flush pending autosave before approve/defer and use
the returned revision. Edits made during a save need another save; an old receipt
must not replace newer input or mark it saved. Disable editing during the short
approve/defer/undo operation. Explicit selection of another entry also waits for
a successful save, or stays with the failed draft. `setResume` failure is a visible
bookmark warning, not a failure of an already committed semantic decision.

Retry a timed-out mutation with its original operation ID and identical payload.
The backend returns the original receipt for a committed retry. Do not substitute
a new ID, advance, or replay automatically after changing the payload. The adapter
must preserve the in-flight request for safe retry while the page is open; a browser
reload recovers durable state via `getEntry` before offering another decision.

## Entry document

Required fields:

- `schema`, `key`, opaque `revision`, `queue_state`.
- `source`: `{title, description, target, members}`. `target` is exactly
  `{kind: "package"|"artifact", id}`; members are `{path, sha256, size}`.
  Source metadata is immutable and is not editable as interpreted identity.
- `accepted`: null or `{identification_status, claims}`. Claims have the same
  structure as draft claims below. This projection is not a catalog record.
- `draft`: `{claims}`; initialized by backend from current interpretation or
  proposals; returned even when the user has not edited anything.
- `proposals`: array of `{field, value, evidence_ids, reason}`; never silently
  accepted. `value` matches that field's draft value type.
- `evidence`: array of `{id, source_ref, field, observation}`. `source_ref` includes
  manifest/entry and optional path. `observation` is the preserved JSON value
  (text or object, including hash/offset/member when available). Render it safely
  as text/structured fields, never as HTML or executable links. Fixture evidence
  comes directly from the reference bundle; not every editorial claim has a file hash.
- `issues`: array of `{code, field, message}`; field is a claim name or null for
  a media/package issue. Initial codes: `identity_provisional`, `version_unknown`,
  `distribution_unknown`, `unsupported_archive`, `media_unavailable`,
  `read_permission_denied`. Unknown codes still render their supplied message.
- `undo`: null or `{decision_id, label}` for the last allowed reversible decision.

Each claim in `draft.claims` is `{value, assessment, evidence_ids, reason}`.
All five claim keys are required; `evidence_ids` is an array of IDs in this entry.
`assessment` is `accepted` (human-supported claim) or `unresolved` (retained
uncertainty). Nonempty reason is required for unresolved claims. Supported claims
require at least one evidence ID. The backend validates the claimed evidence, not
just its existence. Approval may keep unresolved claims; it does not certify them.

| Claim | Value |
| --- | --- |
| `identity` | `{software_id, name}`; software_id is an existing server-supplied ID or null for a new/corrected identity, name is nonempty text |
| `version` | nonempty text; use literal `unknown` with unresolved assessment when not established |
| `content_kind` | `application`, `game`, `course`, `image_collection`, `font_collection`, `reference`; unresolved is allowed for a proposal |
| `distribution_kind` | `full`, `demo`, `trial`, `update`, `unknown`; unknown must remain unresolved |
| `description` | `{language: "nb-NO", text}`; text nonempty |

When editing a name for a different identity, send software_id null; backend
resolves/creates IDs or returns validation/conflict, never lets the browser rename
shared records implicitly. Human edits do not set `assessment` to accepted without
an explicit supported decision. Existing curated claims start accepted; provisional
identity starts unresolved. Field-level review metadata is new review-workspace
state, not a claim that the current catalog schema already stores it.

## Error object (Promise rejection)

`{code, message, retryable, field_errors, current_entry}`. `field_errors` is a map
of claim name to readable explanation (empty when irrelevant); `current_entry`
is a fresh entry on revision conflict, otherwise null. Codes:

| Code | UI behavior |
| --- | --- |
| `validation_failed` | Keep edits; show field errors; no advance |
| `revision_conflict` | Keep local draft and show current server state; explicit reconciliation then new operation |
| `shared_record_conflict` | Keep edits; explain need for shared-identity resolution; no overwrite |
| `service_unavailable`, `write_failed` | Keep edits; visible retry; never fake successful save |
| `undo_conflict` | Keep state; refresh server undo availability and explain |
| `operation_id_reused` | Stop retry and show error; requires correcting client request |

Unknown error codes show their message and retain edits. `retryable` is advisory,
not permission for an unbounded retry loop. Missing media normally appears in
`issues` while preserved metadata stays usable; it must not blank the whole entry.

## Fixtures and scope

[Example documents](curator-fixtures-v1.json) contain K23 CPU-Z and K4 Blockout,
real source/evidence references, and **simulated review state/revisions**. Their
accepted/draft claim assessments are an adapter projection for development, not
new catalog decisions. The fixture adapter must additionally simulate failed
saves, conflicts, undo and missing media. It should namespace browser persistence
by schema and fixture dataset, support an explicit reset, and stay visibly in
fixture mode. It must not alter the reference curation bundle.

This interface is deliberately separate from the frozen public frontend 1.0 data
contract. HTTP paths, service discovery, disk layout, event journal implementation,
actor identity, migration and review-workspace backup are backend responsibilities.
They do not block the fixture frontend; they do block integrated release acceptance.

## Backend development notes (0.2.0-dev1)

The Python workspace implements these operations; HTTP/browser wiring is pending.
An additive nullable `defer_reason` on entries exposes the saved skip reason.
Draft text fields may be empty during typing; nonempty values and review reasons
are enforced on approval. A newly accepted or changed supported claim requires a
reason linking it to the selected evidence (`validation_failed` otherwise).
See [backend limits and setup](review-workspace-dev1.md), including conservative
undo conflicts after subsequent graph changes. These details do not rename any
adapter method or require new frontend-generated catalog IDs.
