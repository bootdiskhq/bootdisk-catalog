# ADR-007: Receive unidentified Director candidates outside the review workspace

Status: accepted for the controlled K-CD 1/2000 trial.

## Context

The existing local curator starts from one Identification and one Norwegian
Description per source entry. Importing a new disc must not require us to invent
those claims first. K-CD 1/2000 also establishes a preservation distinction:
Director `inventory_refs` contain literal launch targets, whereas the previous
DTX folder inventories supported source-entry Package records (ADR-003).
Identical setup launchers do not establish identical products or packages.

## Decision

Introduce an isolated, immutable candidate intake with a versioned contract.
An intake contains the exact ingest manifest, a preservation-only catalog, a
deterministic candidate document and a readable report. It is not a new catalog
record type and is not a ReviewWorkspace. Existing semantic writers remain the
only route to accepted claims; no decisions or human approvals are manufactured.

Candidate identity is the exact manifest SHA-256 plus source entry ID, independent
of title, source mount point and launch-file hash. Changed manifest bytes produce
a new snapshot, not an implicit replacement or reconciliation. Candidates retain
source observation pointers, original selected text and unresolved source issues.
All identity/version/content-kind/distribution/language claims remain unset.
Menu groups are observations, not automatic content-kind decisions. A missing
selected description does not justify a synthetic description.

For `kcd-director-experimental-1`, the preservation importer creates Artifacts and
Occurrences only; it must not produce Packages from launch references. Candidate
intake additionally checks the explicit Director scope and reference/inventory
agreement. The existing DTX package import remains unchanged. Candidate intake
currently rejects other schemas rather than silently guessing their semantics.

Build and graph-check the complete intake in a temporary sibling directory, then
publish by directory rename. Serialize intake writers with a local file lock.
An exact retry is a no-op; changed or edited output is rejected. No update mode,
force flag, source-media execution, network access or public publication exists.
The original manifest is copied, not edited. Source binaries are not copied by
Catalog: ingest's separate extraction remains the owner of those bytes.

## Consequences and next boundary

We can receive the new disc without changing the old review workspace. A machine
inspection queue can now address candidates before identity is established.
This does not yet automate semantic decisions or expose candidates in the current
curator frontend. The v1 curator's entry-key validation and assumption of existing
identifications must be adapted deliberately in a later contract revision, along
with qualified decision rules, actor/history/undo and the exception overview.

Intake is a reproducible local observation snapshot, not a backup of the full CD
and not a power-loss durability promise. Identical retries are checked by content;
cross-manifest reconciliation remains explicit future work. No claim is made that
the Director parser covers all sections of the CD.
