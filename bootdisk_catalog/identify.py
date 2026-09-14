"""Create explicit catalog interpretations from already-preserved observations.

This module deliberately does not infer software identity from filenames, titles,
or hashes. A curator supplies the semantic identity and points the interpretation
back to an existing Artifact occurrence as evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .catalog import Catalog, CatalogError, SCHEMA


class IdentificationError(Exception):
    """Raised when an explicit catalog identification cannot be written safely."""


def _safe_filename(record_id: str) -> str:
    # Filenames are organizational only; stable catalog identity stays inside JSON.
    return re.sub(r"[^A-Za-z0-9._-]+", "_", record_id) + ".json"


def _identification_id(artifact_id: str, release_id: str) -> str:
    # The relationship itself is stable even if supporting evidence is enriched later.
    digest = hashlib.sha256(f"{artifact_id}\n{release_id}".encode("utf-8")).hexdigest()
    return f"identification:{digest}"


def _select_occurrence(
    catalog: Catalog, artifact_id: str, entry: str
) -> dict[str, Any]:
    try:
        artifact = catalog.record(artifact_id)
    except CatalogError as exc:
        raise IdentificationError(str(exc)) from exc

    if artifact["type"] != "artifact":
        raise IdentificationError(f"catalog id is not an artifact: {artifact_id}")

    matches = [
        occurrence
        for occurrence in catalog.occurrences_for_artifact(artifact_id)
        if occurrence["source_ref"].get("entry") == entry
    ]
    if not matches:
        raise IdentificationError(
            f"no occurrence for artifact {artifact_id} in entry {entry}"
        )
    if len(matches) > 1:
        raise IdentificationError(
            f"multiple occurrences for artifact {artifact_id} in entry {entry}; "
            "the evidence source is ambiguous"
        )
    return matches[0]


def _record_path(root: Path, record: dict[str, Any]) -> Path:
    directories = {
        "software": "software",
        "software_release": "releases",
        "identification": "identifications",
    }
    return root / directories[record["type"]] / _safe_filename(record["id"])


def _canonical_json(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, ensure_ascii=False) + "\n"


def _preflight_record(path: Path, record: dict[str, Any]) -> None:
    if not path.exists():
        return
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentificationError(
            f"cannot inspect existing catalog record {path}: {exc}"
        ) from exc
    if existing != record:
        raise IdentificationError(
            f"refusing to overwrite conflicting catalog record: {path}"
        )


def create_identification(
    catalog_root: str | Path,
    *,
    artifact_id: str,
    entry: str,
    software_id: str,
    software_name: str,
    release_id: str,
    version: str,
    evidence_field: str,
    evidence_value: str,
    status: str = "curated",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Write Software, SoftwareRelease and Identification records explicitly.

    The existing Occurrence supplies the immutable manifest+entry evidence source.
    Its filesystem path is intentionally omitted because the supplied evidence field
    describes the editorial entry, not necessarily the referenced file itself.
    """

    if status not in {"interpreted", "curated"}:
        raise IdentificationError(f"invalid identification status: {status!r}")

    root = Path(catalog_root)
    catalog = Catalog.load(root)
    occurrence = _select_occurrence(catalog, artifact_id, entry)

    occurrence_source = occurrence["source_ref"]
    source_ref = {
        "manifest": occurrence_source["manifest"],
        "entry": occurrence_source["entry"],
    }

    software = {
        "schema": SCHEMA,
        "type": "software",
        "id": software_id,
        "name": software_name,
    }
    release = {
        "schema": SCHEMA,
        "type": "software_release",
        "id": release_id,
        "software_id": software_id,
        "version": version,
    }
    identification = {
        "schema": SCHEMA,
        "type": "identification",
        "id": _identification_id(artifact_id, release_id),
        "artifact_id": artifact_id,
        "software_release_id": release_id,
        "status": status,
        "evidence": [
            {
                # The source field is observed evidence. The semantic conclusion
                # drawn from it is represented separately by Identification.status.
                "kind": "observed",
                "source_ref": source_ref,
                "field": evidence_field,
                "value": evidence_value,
            }
        ],
    }

    records = (software, release, identification)
    paths = tuple(_record_path(root, record) for record in records)

    # Check every destination before writing anything so conflicts cannot leave a
    # half-written semantic relationship behind.
    for path, record in zip(paths, records):
        _preflight_record(path, record)

    for path, record in zip(paths, records):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_canonical_json(record), encoding="utf-8")

    # Reload the complete graph so broken IDs or references fail before success.
    Catalog.load(root)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add an explicit evidence-based software identification"
    )
    parser.add_argument("catalog_root")
    parser.add_argument("--artifact", required=True, dest="artifact_id")
    parser.add_argument("--entry", required=True)
    parser.add_argument("--software-id", required=True)
    parser.add_argument("--software-name", required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--field", required=True, dest="evidence_field")
    parser.add_argument("--value", required=True, dest="evidence_value")
    parser.add_argument(
        "--status", choices=("interpreted", "curated"), default="curated"
    )
    args = parser.parse_args(argv)

    software, release, identification = create_identification(
        args.catalog_root,
        artifact_id=args.artifact_id,
        entry=args.entry,
        software_id=args.software_id,
        software_name=args.software_name,
        release_id=args.release_id,
        version=args.version,
        evidence_field=args.evidence_field,
        evidence_value=args.evidence_value,
        status=args.status,
    )
    print(software["id"])
    print(release["id"])
    print(identification["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
