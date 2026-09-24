# ADR-008: Keep first-pass suggestions outside authoritative decisions

Status: accepted for the local automation development requested by Stian.

The manual per-entry workflow does not scale. Before allowing machine decisions,
we need reproducible field suggestions and a machine inspection queue, without
misrepresenting absent evidence as a completed or human-reviewed record.

Use pristine Director intake snapshots as the initial boundary. Recompute their
observation projection before applying rules. Produce a separate queue with exact
source keys, readable evidence, field status, rule version and input hashes.
Original descriptions stay verbatim. Broad categories, product-name numbers,
shared launchers and ambiguous edition prose cannot become accepted claims.

Retained unknowns and machine tasks are separate dimensions. An unresolved source
issue is not automatically a request for human input. The first producer therefore
never emits needs_review or a decision. Human decisions/drafts remain in the
existing workspace, which is not a valid input or output destination to overwrite.

The Web team receives a versioned read-only queue contract and explicitly synthetic
future-state fixtures. No endpoint or write action is invented in the prototype.
Public allowlisting and hosted access boundaries remain unchanged.

This establishes rule-candidate routing, not rule qualification for semantic
writing. Inspection, DTX support, reconciliation with existing human work and
machine actor/history/undo are separate required steps. Report their absence
alongside real-disc results so a zero human-exception count is not read as success.
