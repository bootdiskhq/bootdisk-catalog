# K-CD 15/2001 — remaining work

Snapshot dated 2026-09-20. All 39 entries have an interpretation; 35 identities are curated and four remain provisional. A curated identity does **not** certify version, license, distribution or complete extraction. This is not a new full-disc verification.

| Entry | Software | Identity | Version | Distribution |
| --- | --- | --- | --- | --- |
| K1 | software:aliens-vs-predator-2 | curated | unknown | demo |
| K3 | software:bille-og-trille | curated | unknown | unknown |
| K4 | software:blockout | interpreted | unknown | unknown |
| K5 | software:bugnosis | curated | unknown | unknown |
| K6 | software:clickpuzzle | interpreted | unknown | unknown |
| K7 | software:dr-goo | curated | unknown | unknown |
| K8 | software:deer-avenger | curated | 4 | demo |
| K9 | software:fire-fighter | interpreted | unknown | unknown |
| K10 | software:floppy-image | curated | unknown | unknown |
| K11 | software:font-xplorer-lite | curated | 1.2.2 | unknown |
| K12 | software:ice-breaker | curated | 1.2.1 | unknown |
| K13 | software:mechcommander | curated | 2 | demo |
| K14 | software:workpace | curated | unknown | unknown |
| K15 | software:mutant-xpiders | curated | 1.5 | unknown |
| K16 | software:docucom-pdf-driver | curated | unknown | unknown |
| K17 | software:panorama-factory | curated | 2.3 | trial |
| K18 | software:pf-eksempelbilder | curated | unknown | unknown |
| K19 | software:puzzlejig | interpreted | unknown | unknown |
| K20 | software:red-faction | curated | unknown | demo |
| K21 | software:resize-browser | curated | unknown | unknown |
| K22 | software:shoot-and-relax | curated | unknown | trial |
| K23 | software:cpu-z | curated | 1.10 | unknown |
| K24 | software:acrobat-reader | curated | 5.0 | unknown |
| K25 | software:digitalkameraskolen | curated | unknown | unknown |
| K26 | software:kfa-arsregister | curated | unknown | unknown |
| K27 | software:powerpoint-skolen | curated | unknown | unknown |
| K29 | software:internet-explorer | curated | 5.5 | unknown |
| K30 | software:1st-page | curated | 2000 | unknown |
| K31 | software:hjemmesideskolen-ekspert | curated | unknown | unknown |
| K32 | software:wordskolen | curated | unknown | unknown |
| K33 | software:word-ekspert-skolen | curated | unknown | unknown |
| K34 | software:outlookskolen | curated | unknown | unknown |
| K35 | software:avg-antivirus | curated | 6.0 | unknown |
| K37 | software:winamp | curated | 2.76 | unknown |
| K38 | software:winzip | curated | 8.0 | unknown |
| K39 | software:xnview | curated | 1.21 | unknown |
| K40 | software:photo-objects-sampler | curated | unknown | unknown |
| K41 | software:bruk-photo-objects | curated | unknown | unknown |
| K42 | software:larabie-fonts-kcd15-2001 | curated | unknown | unknown |

## Exceptions and next actions

- K4, K6, K19: Gentee payload decoding still required before promoting identity/version. Header inspection confirms embedded PAK boundaries (see payload review); no decoded product claims yet.
- K9: installer payload format remains unresolved. Preserve the source title as a proposal and queue manual investigation; do not run the historical executable.
- FirstPage/DATA1.CAB: current host denies reads. The 887-file manifest remains preserved; 886 source-file hashes were verified in the prior review. A new complete ingest cannot be claimed. A readable owner-supplied copy is needed for the last file.
- K12: 1.2.1 is confirmed in embedded source; compiled-game version remains separately unverified.
- K3: internal demo symbols do not alone establish the delivered edition.
- K10, K18, K26: installer references corroborate identity; referenced payloads are not fully reconstructed.
- Every `unknown` above remains an explicit open field. For collections/courses, determine whether version is applicable instead of inventing a version. Freeware, Lite and Sampler names do not alone settle distribution.

The accompanying [machine-readable snapshot](../data/curation/kcd15-2001-review-audit.json) binds this review to the exact bundle hash. Regenerate/update it when the bundle changes. It is a review report, not an authoritative catalog record or an import bundle.

## Repeatable human process

1. Open an entry with its original editorial title, description, package members and existing interpretation visible together.
2. Read README, license and setup metadata; inspect executable product metadata. Compare sources rather than trusting filenames or generic launcher versions.
3. If needed, inspect archive members without running installers. Keep the enclosing hash, member path or byte offset, method and decoded hash with each observation. Unsupported extraction becomes a visible unresolved item.
4. Decide identity, version, content kind and distribution separately. Record the reason and evidence for each accepted claim; keep uncertain fields unknown.
5. Save the decision, retain prior values/evidence, and proceed to the next unresolved entry. Revisit deferred entries from the same queue.

See the [1.2 curation delivery gate](curation-next-step.md) for turning this process into a fast independent workflow.
