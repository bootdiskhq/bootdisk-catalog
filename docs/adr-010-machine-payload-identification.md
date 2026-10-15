# ADR-010: Machine decisions backed by decoded program metadata

Status: implemented and qualified on the current seven-disc batch.

Stian explicitly requested automatic completion and publication. A machine may now
write a `curated` identity when a bounded archive reader finds matching program
metadata. `curated` represents an accepted Catalog interpretation; it does not
assert that a person clicked approval. Evidence explicitly records actor=machine.

Rule `payload-product-identity-1` requires CD title agreement with both ProductName
and FileDescription inside a decoded executable member, a single nonconflicting
numeric ProductVersion, and no warnings or embedded NULs. Comma-separated numeric
version components are displayed with dots; the original values remain in the
evidence. ProductVersion alone is used, never FileVersion. An exact version suffix
may be removed from the CD title only when the same ProductVersion supports it.
Setup/uninstall members and known installer frameworks cannot establish identity.
Conflicting qualifying members or language resources stop a decision.

The batch runner checks manifest/container bytes, the catalog occurrence and the
single distinct launch target. It requires a complete bounded member selection,
re-extracts qualifying members, verifies their hashes and reparses their bytes.
Existing human decisions are excluded. Only preliminary machine identities from
ADR-009 can be superseded, with replaced IDs retained in the audit. The previous
bundle and snapshots remain available for rollback. Source prose, pictures and
unknown distribution are preserved. Nothing implies redistribution permission.

This is a bounded pass, not a universal installer decoder. Seven-Zip read 52 of
167 unique containers; 115 were unsupported. The selection covers executable,
DLL, text, INI/INF/DIZ and renamed .___/.ex_ members, with 8 MiB/member, 32 members,
64 MiB aggregate selection and 20 seconds per subprocess. Larger/omitted members,
other file types, nested packages and unsupported formats remain explicit machine
work. Native program execution is never used. The rule API is reusable; the
multi-disc batch runner remains a local qualification workflow, not a hosted
curation endpoint or an automatic integration with new-disc ingest.
