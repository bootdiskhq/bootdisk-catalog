# HTML source evidence

For `kcd-html-1`, Catalog validates preserved index and page bytes against the
inventory, replays the pinned Ingest HTML selector and compares title, description,
license, category and local file/image bindings. Altered text, wrong selector,
wrong file bindings and forged missing-file observations fail closed.

This format requires the matching `bootdisk_ingest` checkout on PYTHONPATH.
Existing DTX/Director paths do not acquire that runtime dependency. There is no
new approval or installed-product identification: the result is documented CD
source wording with independent file-association state. Source versions and
licenses remain observations, not curated SoftwareRelease facts.

Seven focused tests cover valid evidence and negative cases. Real-media acceptance
is recorded with the coordinator's 2012 intake report. A missing Ingest checkout
skips these integration tests explicitly; it must not be counted as passing.
