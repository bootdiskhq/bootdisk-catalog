# RTF source context

Presentation prefers an existing original DTX `raw.Global`. If it is absent,
it can display ingest's `rtf-ansi-text-1` observation at
`evidence.description_rtf.text`. Catalog does not parse RTF or reopen media.
Before projecting it, Catalog checks exact embedded byte hash/size against both
the explicit discovered description file and its inventory row. Unsupported or
missing text stays absent. Invalid provenance fails rather than silently falling
back. Original whitespace is retained; no language, identity or curated
Description claim is inferred. The frontend pointer binds the value to its
original manifest and source entry.

K-CD 1/2001 supplies 33 original RTF descriptions for 34 entries. Intercent's
referenced description file is absent. Existing Global-based and Director
presentations retain their current behavior.
