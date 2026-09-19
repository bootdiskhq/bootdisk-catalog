# Catalog 0.1 architecture summary

Authoritative Catalog state is small JSON records connected by stable IDs:

`Software -> SoftwareRelease <- Identification -> Artifact -> Occurrence`

Occurrence preserves where exact bytes were observed. Identification records the
human/evidence-backed semantic interpretation. Derived views and frontend
projections are rebuildable and are not catalog truth.

Public metadata and curation are versioned in Git. Website JSON is a static,
rebuildable projection of a specific Catalog commit; published binaries and web
derivatives remain outside the Catalog repository.

The rc1 boundary is intentionally sufficient for a prototype presentation layer,
not a claim that the domain model is finished.
