# Source readiness v4: localized titles and multiline Tools prose

Norwegian TitelNO/TitelNo variants are accepted only when the normalized title,
raw entry and recorded section match the independently parsed preserved K.DTX
bytes. The metadata hash and size must match the file inventory. Conflicting fields,
forged values and changed preserved bytes are rejected. The source pointer names
the exact original field. This is source documentation, not product identification.

Tools prose may contain unindented continuation lines. The bounded
`dtx-prose-continuation-1` projection is independently reproduced here, and its
line-number claim must agree with the preserved document. Repeated original prose
is not deduplicated or rewritten. The helper in this repository is a source-proof
validator; Ingest remains the source parser. The contract and tests must be updated
together if the projection grammar changes.

The emitted rule is source-catalog-readiness-4. Web must accept v4 before attaching
source documents/building collections. Earlier rules remain readable in published
baselines. No human decision or authoritative identity is created by these changes.

Validation: 182 tests, 181 passed and one optional test skipped. Local HTTP test
permissions are required. Real-media acceptance resolves all 73 title tasks in the
seven 2008/2009 samples; all corresponding Norwegian titles exist in original bytes.
