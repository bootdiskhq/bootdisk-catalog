# Local curator service (Catalog 0.2.0-dev2)

The browser can now use the durable review workspace through the seven v1 adapter
operations. The service binds only to 127.0.0.1. This is a local development tool,
not a hosted authentication service and not the completed Bootdisk 1.2 release.

## Start

After initializing a workspace as described in [dev1](review-workspace-dev1.md):

```sh
python -m bootdisk_catalog.service /path/to/review \
  --web-root /path/to/bootdisk-web \
  --port 8772 \
  --issues data/curation/kcd15-2001-inspection-issues.json
```

Open the URL printed by the command, including `?mode=local`. Start without
`--issues` for another source; reports referencing an entry outside the workspace
are rejected. Existing inspection issues are dated observations, not a fresh
media scan. In particular, the unreadable FirstPage CAB remains unresolved.

Keep the process running while editing. A service restart rotates its session
credential. Reopen the page after restarting; saved drafts/history remain on disk.
If a request timed out, retry the same operation while the session remains active.
Do not discard unsaved text to troubleshoot a connection problem.

The UI shows “Lokal kuratering – ekte katalogdata”. Its simulation controls are
hidden. A connection failure never falls back to fixtures. The original static
fixture page still works under a separate static server without `mode=local`.

## Transport

GET `/api/session`, with `X-Bootdisk-Client: bootdisk-curator-v1`, returns schema,
manifest and an ephemeral session token. POST `/api/<adapterMethod>` accepts the
unchanged JSON request from the adapter; headers include the client discriminator,
`X-Bootdisk-Token` and the browser's exact Origin. Reads use POST as well to keep
one adapter protocol. There is no automatic retry in transport; the controller
owns exact operation replay. Structured workspace errors are returned intact.

Host, Origin, session token and cross-site fetch checks reject foreign requests.
No cross-origin access is enabled, and pages cannot be framed. Request bodies
are limited to 2 MiB. Only an explicit list of curator HTML/JS/CSS can be served;
no directory browsing, arbitrary paths, original files, workspace snapshots or
backup files. The session header prevents cross-origin script tags from obtaining
credentials. These controls do not defend against an already compromised local
OS user. Do not proxy or expose this development service on a public interface.

## Additive entry fields

`history` includes only approve/defer/undo events for the current entry: kind,
decision_id, at, actor, reason and previous/new accepted claims. It excludes
whole-graph snapshots and other entries. Stored receipts include their historical
view so an exact retry stays identical. `defer_reason` is separately readable.
Inspection reports attach read-only issues in the transport; they never rewrite
the ingest manifest, a decision or its evidence.

## Verification and remaining work

HTTP tests exercise real sockets, access restrictions, unavailable paths,
malformed input, draft/approve/retry/undo, conflict responses, restart persistence
and issue/history rendering data. Existing Catalog tests still verify graph rules.
A browser smoke test used a copy of all 39 entries: edit CPU-Z, approve, advance,
reload, find the decision and undo while keeping the draft.

Next: independent ten-entry usability session with Stian; fuller inspector support,
shared-identity resolution and new-disc bootstrap remain follow-up work. The dev1
conservative undo limit still applies. Approval never publishes to bootdisk.no;
export and public release remain separate operations.

## Source category and distribution evidence

The workspace includes exact category labels from `normalized.categories`, the CD
license (`raw.Licens`, falling back to the preserved normalized value), and the CD
description. No category or license is automatically converted into a decision.
For accepted content-kind and distribution claims, approval requires selected
source evidence and a written rationale. A human must judge whether it actually
supports the claim, including contradictions; validation cannot establish that from
arbitrary source text. Freeware alone is not evidence of a full edition.

Existing workspaces can be updated with:

```sh
python -m bootdisk_catalog.review WORKSPACE enrich-sources MANIFEST
```

Use the original manifest with its exact digest. The operation locks the workspace,
creates `before-source-evidence-*.json`, adds observations and changes entry
revisions. It does not change draft/accepted values, evidence selections, decisions,
retry receipts, graph records or resume position. Repeat calls do nothing. Stale
browser writes receive a conflict rather than overwriting work; reload after saved
changes. Existing accepted classifications without rationale are visibly flagged
for review and included in the open-fields queue, even on reviewed entries. They
remain historical decisions until the curator explicitly changes or confirms them.

Tests cover migration preservation, wrong manifests, stale writes, approval,
restart and exported evidence. Original media does not need to be remounted.

## Original CD descriptions

Descriptions reproduce the original CD `Global` text verbatim, falling back to the
preserved normalized description only when raw metadata is unavailable. Spelling
and punctuation are not rewritten. The curator shows the description read-only;
server validation also rejects edits. Notes belong in the claim rationale.

New workspaces apply this rule at initialization. To update existing workspaces:

```sh
python -m bootdisk_catalog.review WORKSPACE restore-descriptions MANIFEST
```

This explicitly authorized migration updates description text in the approved graph,
accepted claim and draft, with original-text evidence, and adds per-entry history.
It takes an exact `before-original-descriptions-*.json` backup first; previous drafts
and accepted wording are also retained in migration events. It leaves other fields,
queue state and prior history unchanged. Missing source text, shared descriptions,
or the wrong manifest fail without writing. Re-running is a no-op. Revisions change,
so reload a saved browser session after migration. An older undo that would restore
pre-migration graph text is rejected by the existing graph-conflict check; the backup
retains that earlier state. Export uses the restored original text. Public deployment
remains a separate step.
