# Compressed workshop artwork observations

The embedded image importer accepts explicit zlib resource locations. It verifies the preserved container against the ingest inventory, decodes a bounded stream, checks its exact length/boundary and compares the declared decoded subrange to the resource bytes. The occurrence retains the compressed offset, compressed/expanded lengths and decoded subrange offset. A decoded size must not be mistaken for a byte range in the compressed container.

D6 direct-color artwork has no CLUT. For the declared `argb32-d6-rle257-or-raw` encoding, pixels and metadata generate occurrences; a palette is forbidden. Other encodings retain the existing required palette behavior. No software identity, version or approval is created.

Qualification: 162 supplementary source entries from six mounted K-CDs imported into separate Catalog directories, each with its original artwork. Two missing menu launch files remain explicit issues. The active curator workspace was not touched. The old 207 public cards remain byte-identical in the combined web projection.
