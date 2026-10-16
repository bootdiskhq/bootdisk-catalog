# Source rows without package files

K-CD 11/2001 K9 names CR Self Extractor Builder with an empty Folder and no file
inventory. K-CD 12/2001 K9 similarly names LetterBox. Keep these source rows, but
do not create a shared empty package identity for them. Source documentation is
independent of a file package.

The importer accepts an empty inventory_refs list only with the exact empty
SHA-256 content identity (zero files, zero bytes, digest of empty input). Any
inconsistent identity remains an error. Nonempty package validation is unchanged.

Tests cover skipping the empty package while preserving other packages and
rejecting inconsistent counts, sizes and hashes. No source metadata is rewritten.
