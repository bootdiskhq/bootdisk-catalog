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
