# Review workspace development release 0.2.0-dev1

This Catalog development release is the backend foundation for **Bootdisk 1.2**.
It is not a finished 1.2 release. Claude's frontend proceeds independently against
the existing v1 adapter. This PR supplies Python operations and a development CLI;
no HTTP service, live JavaScript adapter or new inspector is delivered yet.

## Implemented

`ReviewWorkspace.call(method, request)` implements getQueue, getEntry, saveDraft,
defer, approve, undo and setResume. Method names and JSON responses match the
adapter contract. Python raises `ReviewError` with its structured `payload`; the
future service adapter maps it to a rejected Promise. Additive `defer_reason`
makes the saved defer reason readable on the entry, not just in backup history.

One atomic `review-state.json` snapshot holds the validated Catalog graph,
review entries, immutable historical event snapshots and operation receipts.
An advisory process lock serializes writers. Writes flush the temporary file,
replace the snapshot and sync its directory before acknowledgment. If acknowledgment
is uncertain, repeat the same operation ID and request; do not submit a new one.
A prior successful receipt takes precedence over a now-stale revision.

Approval builds a candidate graph in the existing `identify` module, validates it,
and saves it together with the decision event. The legacy identify CLI remains
append-only. Catalog IDs are resolved on the backend. Ambiguous shared edits are
rejected. New accepted field values need selected evidence and a reason. This is
human judgment supported by bound evidence, not automatic verification that prose
semantically proves a claim. Unknown version/distribution remains unresolved.

Draft text fields may temporarily be empty while typing; full validation runs on
approval. The contract's nonempty claim rules apply to approval, not each keystroke.
Unresolved typed versions are retained in review state but exported as `unknown`.
Unresolved descriptions remain `draft` catalog descriptions; existing presentation
filters publish only curated descriptions. Unapproved workspace drafts are never
exported into the catalog graph.

Undo preserves the latest draft and restores the graph/accepted interpretation
from the decision's prior state. It is a new historical event. This first version
conservatively rejects undo if any subsequent decision changed the graph, even
on another entry; automatic fine-grained shared-dependency reversal is deferred.
Autosaves and bookmarks do not by themselves block undo.

## Local use

Requires Python 3.10+ and POSIX file locking (macOS/Linux). From this repository:

```sh
python -m bootdisk_catalog.review /path/to/review init /path/to/imported-catalog /path/to/manifest.json
python -m bootdisk_catalog.review /path/to/review call getQueue /path/to/request.json
python -m bootdisk_catalog.review /path/to/review backup /path/to/new-backup.json
python -m bootdisk_catalog.review /path/to/restored-review restore /path/to/new-backup.json
python -m bootdisk_catalog.review /path/to/review export /path/to/new-exported-catalog
```

Example queue request (substitute the real manifest digest):

```json
{"manifest":"sha256:ae29b1d2976ee7c7439b2e12fe18b774d1d57e77c9a20bc3567d2e5079257281","filter":"pending"}
```

The review directory must be outside the imported catalog. Initialization never
overwrites an existing workspace. Backup and catalog export require new destination
paths. Backup contains drafts, history, receipts and bookmarks; ordinary semantic
curation export is not a substitute. Keep backups private/local: they contain
unfinished work. The imported catalog and source media remain untouched.

An exported catalog can be consumed by existing Catalog/Publish/Web build commands.
The workspace itself is not a normal record directory and must not be passed to
`Catalog.load` or the public website builder. Nothing is auto-published or committed.

A local workspace was initialized at `local-results/review-1.2-dev` with all 39
K-CD entries from the preserved manifest and current curation. No decisions were
changed in that workspace during the smoke check.

## Limits and next slice

- Bootstrap requires exactly one existing identification and one Norwegian
  release description per source entry. New/unidentified-disc onboarding is next
  work, not a claim of support for arbitrary media.
- Initial evidence is preserved Catalog evidence, not freshly extracted files.
  No fresh media verification occurs; known unreadable CAB and unsupported
  installer reports remain in the source review audit. Inspector issue integration
  must expose these in the UI before the 1.2 acceptance gate.
- Snapshot/event storage prioritizes correctness and recovery for this disc;
  full graph snapshots grow with semantic decisions. Benchmark/compact with
  preserved audit history before substantially larger collections.
- Backup restore is intended for trusted backups of this workspace version,
  not arbitrary third-party curation documents. No schema migration yet.
- Transport, origin/session protection, browser adapter and real UI integration
  remain to implement. No contract rename is required for Claude's fixture work.

## Validation

15 new behavior tests cover recovery/export isolation, approval and undo, retries,
stale revisions, failed/uncertain writes, actual competing processes, deferred
reasons, evidence validation, shared identity conflicts and backup/restore.
Run the full suite, optionally with mounted media:

```sh
BOOTDISK_KCD_ROOT='/Volumes/K-CD 15 2001' python -m unittest discover -s tests -v
```
