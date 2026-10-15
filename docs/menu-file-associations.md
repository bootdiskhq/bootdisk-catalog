# Static menu-file explanations

Source readiness rule 2 retains original issue codes and missing paths, and adds
`file_association.explanation` (pattern + Norwegian explanation) and
`runtime_verified: false`. Explained observations use the existing `observed`
status. This means a path was observed, not that a program is installable or that
an alternate reference has been repaired. No executable target is selected.

Three bounded patterns remove the generic machine inspection task:

* Every direct reference is absent, every continuation reference is present in
  the same manifest, and all referenced paths are accounted for.
* The continuation contains the direct target plus additional existing files in
  one source handler. This describes multiple literal calls, not their runtime
  reachability or sequence.
* A direct literal has trailing control characters and otherwise matches the
  existing continuation path. The raw literal is never cleaned or rewritten.

Unknown issues, unresolved controls, unrelated existing targets, unsafe paths,
and incomplete evidence retain machine inspection. No title similarity,
cross-disc substitution, human approval or software identity is inferred.
Original manifests, curator decisions and public source warnings are unchanged.
This is a Catalog interpretation of Ingest observations, not a parser repair.

## Acceptance against the ten rc16 cases

15 October 2026: all referenced existing files were independently read from the
mounted CDs and matched manifest SHA-256. Rule qualification against the exact
source manifests explains six missing-alternative cases, one multi-file handler
(Terragen & Firmament), and one damaged literal (MarbleJongg 2000).
Billeder til Geometra retains conflict; Albert Åberg retains needs_inspection.
All ten remain documented source posts. Runtime behavior remains untested.

Remaining technical work: inspect the Geometra controls and the unresolved
Albert continuation cast link. Do not place these in a human approval queue or
silently choose an installer. Public wording/UI for these detailed explanations
can be added in a later web release; this change does not deploy a website.
