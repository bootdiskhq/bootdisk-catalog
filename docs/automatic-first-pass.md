# Automated first pass: reproducible suggestions before decisions

Run with Python 3.10+ against a pristine Director candidate intake:

```sh
python -m bootdisk_catalog.first_pass /path/to/intake --output /path/to/new-result
```

The output parent must exist. `queue.json` follows [queue v1](automation-queue-v1.md)
and `rapport.md` is a readable report. Neither is a catalog decision. The input
is an immutable intake, not a review workspace. The command does not read source
binaries, run legacy programs, access the network or write semantic records.

Rules `director-first-pass-1`:

- Preserve a selected, nonblank original description exactly as a candidate.
- Suggest `game` only for the exact Director group `['games']`.
- Block these suggestions when source issues or missing launch references exist.
- Retain unknown version/edition and queue program-specific inspection separately.
- Route broad/mixed categories to inspection, not application/course guesses.
- Never infer identity from names or shared launcher hashes, versions from product
  years, or full edition from Freeware. Demo mentions are not parsed as decisions.

All current entries need further machine inspection. Therefore they remain in
`inspecting`, even when individual fields have candidates. This delivery does not
reduce the measured human workload yet. Source conflicts also remain machine
work; a future inspector must attempt resolution before emitting needs_review.

## Integrity and retries

The candidate document must equal a fresh projection of the exact preserved
manifest. Edited claims, decisions, source pointers and older projection shapes
are rejected. For an older intake, explicitly build a new isolated intake from
its manifest using `python -m bootdisk_catalog.intake`; never overwrite the old
snapshot or treat a review workspace as an intake. This is not a migration of
human work. DTX schema 0.9 is explicitly unsupported in this first producer.

Output is built in a temporary sibling then renamed, with serialized writes.
Exact repeats are no-ops; changed/edited destinations, symlinks and output inside
the intake are refused. Rule version and input hashes identify the computation.
There is no update/force/approve mode. Existing human decisions and drafts are
protected by being outside this pipeline, not by a claim of merged integration.

## Next implementation

1. Add program-context inspection in Ingest (README, setup metadata, executable
   versions) with file/member hashes, inspector version and explicit failure states.
2. Add a deliberate DTX input path and a boundary for existing human work, then
   qualify on the 39-entry reference workspace and the other three CD datasets.
3. Use inspection results to resolve conflicts before counting human exceptions.
4. Only then implement audited machine decisions, actor, revisions, idempotency,
   history and undo through the authoritative writer.
5. Wire the queue into the local service and Claude's read-only Web adapter.

The public site and its release version are unchanged by this work.
