# rc1 validation gate

Status: **validated release candidate**.

The `0.1.0-rc1` candidate passed both validation gates on 2026-09-16:

- GitHub Actions passed the complete 39-test suite on the release-candidate path;
- the K-CD 15/2001 reference rebuild imported 153 Artifacts and 164 Occurrences,
  restored three semantic curation records, and resolved K37 as Winamp 2.76;
- `data/curation/kcd15-2001.json` is versioned in the repository and exercised by
  the automated reference rebuild test;
- the restored Identification remains
  `identification:97e260274a5258dae047c0f6294ee1da53b50d22a3f5e588e41da8b23aef5f04`.

The tag and GitHub prerelease must point to the commit that contains this status.
