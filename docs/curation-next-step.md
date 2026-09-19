# Curation after 0.1.0-rc1

The focused `curate --entry` review and the explicit `identify` writer are kept as
separate commands in rc1 on purpose. This makes the trust boundary obvious while
the workflow is still being exercised on real media.

A later curator UI may combine those operations interactively, but it should call
the existing identification writer rather than implement a second semantic write
path. The UI must continue to require an explicit Artifact/Occurrence choice and
must not infer Software identity from filenames, hashes, or editorial titles.

This is workflow polish, not a blocker for the frontend prototype: the frontend can
already consume identified entries through the presentation projection while
pending entries retain honest editorial source context.

## Distribution-kind roadmap

K-CD media may contain complete commercial programs, freeware, demos, trials and
updates. Catalog can record this distinction on an Identification as `full`,
`demo`, `trial`, `update` or `unknown`.

A later ingest/curation assistant should propose a distribution kind from preserved
evidence such as installer names, executable metadata, README and license files,
and the source publication's description. A proposal must remain `unknown` until a
curator accepts the evidence. Absence of words such as “demo” is not evidence that
an artifact is a full version.
