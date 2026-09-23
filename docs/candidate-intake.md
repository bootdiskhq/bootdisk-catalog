# Candidate intake for a newly observed Director CD

From the Catalog checkout, with Python 3.10+:

```sh
python -m bootdisk_catalog.intake /path/to/manifest.json \
  --output /path/to/new-intake
```

The parent of the output directory must already exist. The command reads a
`kcd-director-experimental-1` manifest; the CD need not remain mounted. No binaries
are run or read. No catalog, workspace or frontend needs to be prepopulated.

The output contains:

- `manifest.json`: exact input bytes; all menu texts and source evidence survive.
- `catalog/`: validated Artifacts and Occurrences, without Packages, Software,
  SoftwareRelease, Identification or Description claims.
- `candidates.json`: `bootdisk-candidate-intake-1`, with rule version
  `director-observations-1`, deterministic source keys, source observations,
  launch-file scope, source issues, inspection reasons and summary counts.
- `rapport.md`: readable overview with the selected original CD descriptions.

Pointers in observations are JSON Pointers into the exact manifest, identified by
SHA-256. Titles/menu groups are the ingest projection; descriptions are copied
from `evidence.description_source.text.cp1252_view`, including whitespace, rather
than the normalized description. Language is not inferred. If the parser could
not select one description, it remains absent; other observed texts remain in
the preserved manifest for subsequent inspection.

Director observations omit DTX's `is_file` flag. The importer requires their
`resolved_path`, hash and size to agree with exactly one file-inventory row. The
Occurrence uses that resolved spelling; the original requested spelling remains
in the exact manifest. Missing references remain candidate evidence, not Artifacts.

`state: candidate`, `decision: null` and null claims mean **not approved**, not
approved-with-unknown. `inspection_reasons` are work for machine inspection, not
a demand for a human to approve every missing field. `source_issues` retain
ingest's issue codes without pretending that a source conflict is resolved.
The report does not certify that a clean entry has correct software identity.

An exact repeat leaves the intake unchanged. Changed input requires a new output
directory. Existing notes, decisions, foreign directories and symlinks are never
overwritten. A failed build leaves no final intake directory. Exit 0 means the
snapshot was prepared (possibly with source issues); exit 2 means failure.

Launch files alone are not full program packages. Use ingest extraction/preservation
for original bytes; keep the source disc/image for dependencies not extracted.
Do not put the intake root inside a catalog or pass it to `Catalog.load`; load its
`catalog/` child. The existing curator service still uses its existing workspace,
not this new snapshot. See [ADR-007](adr-007-candidate-intake.md) for the boundary.

## Verification

```sh
python -m unittest discover -s tests -v
```

Synthetic tests cover shared launchers, missing files and descriptions, conflicts,
inventory disagreement, path traversal, duplicate source IDs, exact retries,
changed input, existing edits/workspaces, symlinks and failed writes. Original
CD bytes are not included in the repository. Run the command against a local
ingest manifest to qualify a real disc separately.

## K-CD 1/2000 qualification (2026-09-23)

The local full-disc ingest manifest produced 21 candidates, 18 selected original
descriptions and 5 entries with source issues. The preservation graph contains
20 distinct Artifacts and 37 Occurrences, with zero Packages or semantic records.
This is compatible with 21 start-file paths because some launcher bytes repeat.
Exact rerun produced the same snapshot; the pre-existing 15/2001 review-state file
was hash-checked before and after and remained unchanged. The intake makes zero
automatic decisions. Original media and generated intake files remain local.
