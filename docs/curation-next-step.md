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
