# ADR-003: Identify source-entry packages separately from files

Status: accepted

K5 (Bugnosis) and K17 (The Panorama Factory) share a byte-identical generic
InstallShield launcher. A launcher Artifact cannot identify either complete product.

A `package` reconstructs an entry's exact `files.inventory_refs` using the immutable
manifest's `file_inventory`. Its `package:sha256:` ID uses Ingest's existing sorted
UTF-8 path/NUL/file-digest/newline framing and is checked against `content_identity`.
Members refer to file Artifacts; their sizes and the total are also validated.
Packages include editorial images and documentation. They describe the observed
entry inventory, not a minimal installer, installed application, or complete runtime
closure. Paths are case-sensitive evidence inside this existing identity algorithm;
renaming a member changes the package identity.

An Identification targets exactly one `artifact_id` or `package_id`. Existing file
identifications remain valid. Package identifications do not attach a product name
to every member or to a shared launcher. Package records are reconstructed from
Ingest; curation bundles preserve only semantic records and their package references.
`view` exposes packages separately from individual artifacts.

The CLI accepts `--package package:sha256:... --manifest INGEST_MANIFEST` instead
of `--artifact`. The supplied manifest and entry must bind to that package identity.
Whole-manifest import reconstructs packages when inventory references are present;
focused single-file imports retain their prior behavior.

A successful import validates previously observed metadata. It does not certify a
fresh read of the media or remove an unresolved media-read error.
