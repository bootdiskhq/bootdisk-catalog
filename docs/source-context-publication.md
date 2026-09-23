# Source context in public projections

The presentation projection now includes `source_context` keyed by the exact
manifest SHA-256 and original entry ID. It does not write Catalog records or a
ReviewWorkspace.

For DTX, original wording comes only from `raw.Global`. For Director it comes
from the validated candidate intake's selected `description_source.text.cp1252_view`.
Whitespace and source language are preserved; no translation or language guess is
made. Normalized descriptions are not a fallback for original wording.

Menu groups and source issues retain pointers into the source manifest. Director
scope is explicitly `launch_files_only`. Pending observations can therefore be
published transparently before semantic identification, without inventing software,
version, distribution, package membership or a human approval.

For an existing review workspace, use `bootdisk_catalog.review WORKSPACE export
NEW_DIRECTORY` before presentation. This exports accepted graph records, not draft
claims or review history. Original source text is added independently and must not
be confused with an accepted semantic description.

The K-CD 1/2000 release is an observation publication: 21 pending source entries,
18 selected original descriptions and five source conflicts. File-inspection
observations remain available locally. Automatic field proposals/decisions and a
real multi-medium curator backend remain separate follow-up work; publishing the
source cards does not mark that automation complete.
