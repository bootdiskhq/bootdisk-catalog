# K-CD 15/2001 payload review — 2026-09-20

Eight provisional identities have been promoted using hash-bound observations
inside their source packages. The bundle now has 35 curated identifications and
four provisional ones. Versions and distribution status are separate claims;
all eight retain `distribution_kind: unknown`.

| Entry | Finding | Limit |
| --- | --- | --- |
| K23 | CPU-Z 1.10 appears in the embedded HTML report; the ZIP's cpuz.exe is byte-identical to the loose executable | Generic PE version 1.0.0.1 is not used as product version |
| K12 | Icebreaker package embeds source ChangeLog and spec identifying 1.2.1 | Embedded source version is confirmed; a separate compiled-game version has not been read |
| K11 | Font Xplorer Lite 1.2.2 README and freeware EULA recovered from raw DEFLATE streams | Freeware Lite is not promoted to the paid full-featured product |
| K10 | FloppyImage setup title and internal Floppy Image.exe path agree with source metadata | Payload version and license remain unparsed |
| K26 | Komputer for alle register setup title and Norwegian Kfa register.hlp reference | Internal summer2001 authoring path does not establish a release date/version |
| K40 | INSTALL/SETUP.INI identifies Hemera Photo-Objects Sampler | No version or full/demo conclusion from the Sampler name |
| K18 | Installer contains references to Pan1.jpg through Pan7.jpg under PF Eksempelfiler | References corroborate collection identity; no claim of fully reconstructed JPEG payloads |
| K3 | Director file contains named Bille/Trille figures and Norwegian demo markers | Markers corroborate identity; no claim of proven active demo restrictions or exact edition |

Evidence records carry the exact enclosing-file SHA-256 and either literal byte
offsets, ZIP member name/hash, or raw DEFLATE offset/size, output hash and CRC32.
The Font Xplorer streams' following little-endian CRC32 words match the decoded
bytes. No historical executable or extracted installer script was executed.

Original-media verification can be reproduced with:

```sh
BOOTDISK_KCD_ROOT='/Volumes/K-CD 15 2001' python -m unittest discover -s tests -v
```

The optional test checks 22 observations directly against media; CI explicitly
skips that test without media, while still checking the reference-bundle rebuild.

## Remaining provisional identities

- K4 Blockout, K6 ClickPuzzle and K19 PuzzleJig have a `Gentee installer` stub.
  The available archive reader did not decode their payloads; compressed bytes
  and installer filenames alone do not justify product/version confirmation.
- K9 Fire Fighter likewise could not be decoded by the available archive reader
  or a bounded raw-DEFLATE probe. It remains provisional.

The source-directory completeness issue is unchanged: FirstPage/DATA1.CAB cannot
be read on this host. This review does not claim a new full-disc ingest.
