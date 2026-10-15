# ADR-009: Automatic source-attributed identification

Status: implemented as a bounded local rule, not a completed payload inspector.

Stian requested automatic processing rather than individual manual approvals.
ADR-008's suggestion-only boundary no longer suffices. We now permit machine
interpretations of explicit CD source claims, with a separate audit and without
claiming that a person approved them or that an installer has been decoded.

Rule `cd-source-identity-1` requires a complete name repeated as a whole name in
the original description, no source issues, exactly one explicit executable
reference, matching inventory and freshly read file hashes, and an exact Catalog
occurrence. The name and prose are correlated editorial evidence: this is **not**
independent proof of installed product identity. Therefore the result is always
`interpreted` (the existing frontend renders “Foreløpig identifisering”), never
`curated`. Version, distribution and content kind are not inferred. Existing
identifications and explicitly protected drafts are preserved.

A machine actor, rule version, immutable source key, description pointer and file
identity accompany each decision. IDs are source-local: shared installers and
identical names do not silently merge software between CD entries. Input catalogs
are never mutated. A complete candidate bundle is validated/restored in an isolated
snapshot; rejection or rollback means retaining the prior snapshot. Repeated
computation is deterministic and applying the same bundle is idempotent.

The API requires an explicit eligible entry set and accepts review protection
keys. Callers must pass those keys and preserve existing semantic records when
assembling a release; the API is not an endpoint for changing a live workspace.
For the October 15 run, eligible entries are pending records in the 426-entry
snapshot, review keys are loaded from the existing workspace, and the complete
workspace is checked byte-for-byte afterwards. Only software/status projections
are changed; original prose, pictures and source links stay unchanged.

Unmatched entries remain `inspecting` with machine-readable reasons, not a manual
approval queue. Missing file references, source conflicts, PDF guides, title
variants and opaque installer formats require additional machine rules. The
rule does not resolve earlier technical deferrals or authorize distribution.
A source interpretation must not be described as completed payload identification.

Next: decode supported installer members with bounded, hash-bound inspection;
corroborate product metadata and preserve conflicting version/edition evidence;
upgrade source interpretations only on stronger evidence. Add this snapshot
workflow to the authoritative review service with machine history and undo before
allowing live workspace writes. Hosted curation remains unavailable.
