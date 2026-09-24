# Tools source wording and append-only previews

`presentation.source_context` exposes Tools.dtx `InstruksNo` as a source observation,
not an approved description, version, distribution type or content classification.
It checks preserved CP1252 bytes, length, SHA-256, inventory, metadata binding,
section and field against the parsed observation. Missing Norwegian text stays missing.
Invalid evidence fails closed. Undefined CP1252 bytes require further investigation
rather than silently displaying replacement characters as original text.

`presentation --previous-manifest OLD` supports an explicitly selected append-only
expansion. Every old entry must remain unchanged, in order, with unchanged inventory
and all existing source fields; duplicate source IDs and competing decisions fail.
The disposable view retains previous semantic IDs/status and records their original
binding in `decision_source`. This does not rewrite an identification's evidence or
approve any new entry, even if it shares a folder/artifact with an identified entry.
The Catalog graph, review workspace, drafts, events and receipts are not migrated.

Build in a new directory: export the workspace's approved graph, import observations
for the new manifest separately, and combine records by ID, rejecting any conflicting
record. Retain the previous manifest and a full workspace snapshot. Never substitute
manifest hashes inside saved evidence. Reopening the existing curator still uses its
original workspace; expanded interactive curation requires a separate migration.

Qualification for K-CD 15/2001: 39 unchanged entries plus 29 Tools entries, 68 source
cards with Norwegian text. The parser qualification uses an earlier full inventory;
it is not a fresh complete-disc ingest or proof that every disc item is covered.
