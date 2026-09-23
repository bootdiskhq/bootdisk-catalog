# Embedded image occurrences

`python -m bootdisk_catalog.embedded_images IMAGES_JSON INGEST_MANIFEST CATALOG --output NEW_CATALOG`
adds verified image-resource observations to a new catalog snapshot. The existing
catalog and human review workspace are unchanged. The importer requires matching
manifest/entry bindings, container inventory hashes, resource types/ranges and
preserved resource hashes. Pixel, palette and bitmap-metadata bytes are artifacts;
each occurrence records the original source manifest, supplemental manifest hash,
entry, container identity and resource byte range. No software or approvals are
created. The ordinary presentation projection can now join Publish images by the
same original entry and exact observed pixel hash.
