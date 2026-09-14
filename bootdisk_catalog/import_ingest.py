"""Import preservation observations from a Bootdisk ingest manifest.

This module deliberately imports only facts that ingest can establish directly:
byte identity and where those bytes were observed. It does not create Software,
SoftwareRelease or Identification records because those are catalog interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .catalog import SCHEMA, Catalog, CatalogError


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class IngestImportError(CatalogError):
    """Raised when an ingest manifest cannot be imported safely."""


def _read_manifest(path: Path) -> tuple[dict[str, Any], str]:
    """Load one ingest manifest and return its data plus immutable file identity.

    The manifest's own SHA-256 is used in every source_ref. That lets catalog
    records continue to point at the exact evidence document even if the local
    filename or directory changes later.
    """

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise IngestImportError(f"cannot read ingest manifest {path}: {exc}") from exc

    digest = hashlib.sha256(raw).hexdigest()

    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IngestImportError(f"invalid ingest manifest {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise IngestImportError("ingest manifest root must be a JSON object")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise IngestImportError("ingest manifest must contain an entries list")

    return data, digest


def _find_entry(manifest: dict[str, Any], source_id: str) -> dict[str, Any]:
    matches = [
        entry
        for entry in manifest["entries"]
        if isinstance(entry, dict) and entry.get("source_id") == source_id
    ]

    if not matches:
        raise IngestImportError(f"ingest entry not found: {source_id}")
    if len(matches) > 1:
        raise IngestImportError(f"duplicate ingest source_id: {source_id}")

    return matches[0]


def _find_file(entry: dict[str, Any], role: str) -> dict[str, Any]:
    """Resolve an explicit file observation by semantic role.

    The first importer intentionally accepts only files present under
    files.referenced or files.discovered. It does not infer assets from arbitrary
    inventory paths, keeping the catalog boundary tied to explicit ingest facts.
    """

    files = entry.get("files")
    if not isinstance(files, dict):
        raise IngestImportError("ingest entry does not contain a files object")

    found: list[dict[str, Any]] = []
    for section_name in ("referenced", "discovered"):
        section = files.get(section_name, {})
        if not isinstance(section, dict):
            raise IngestImportError(f"files.{section_name} must be an object")
        candidate = section.get(role)
        if candidate is not None:
            if not isinstance(candidate, dict):
                raise IngestImportError(
                    f"files.{section_name}.{role} must be an object"
                )
            found.append(candidate)

    if not found:
        raise IngestImportError(f"file role not found in ingest entry: {role}")
    if len(found) > 1:
        raise IngestImportError(f"ambiguous file role in ingest entry: {role}")

    observation = found[0]

    if observation.get("exists") is not True or observation.get("is_file") is not True:
        raise IngestImportError(f"file role is not a preserved regular file: {role}")

    digest = observation.get("sha256")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise IngestImportError(f"file role has invalid sha256: {role}")

    size = observation.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise IngestImportError(f"file role has invalid size: {role}")

    observed_path = observation.get("path")
    if not isinstance(observed_path, str) or not observed_path:
        raise IngestImportError(f"file role has no observed path: {role}")

    return observation


def build_records(
    manifest_path: str | Path,
    source_id: str,
    role: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one Artifact and one Occurrence from explicit ingest observations."""

    path = Path(manifest_path)
    manifest, manifest_digest = _read_manifest(path)
    entry = _find_entry(manifest, source_id)
    observation = _find_file(entry, role)

    artifact_digest = observation["sha256"]
    artifact_id = f"artifact:sha256:{artifact_digest}"
    manifest_ref = f"sha256:{manifest_digest}"

    artifact = {
        "schema": SCHEMA,
        "type": "artifact",
        "id": artifact_id,
        "sha256": artifact_digest,
        "size": observation["size"],
    }

    # Occurrence identity is based on immutable manifest identity plus the ingest
    # entry and semantic role. The observed filesystem path remains evidence only.
    occurrence = {
        "schema": SCHEMA,
        "type": "occurrence",
        "id": f"occurrence:{manifest_digest}:{source_id}:{role}",
        "artifact_id": artifact_id,
        "source_ref": {
            "manifest": manifest_ref,
            "entry": source_id,
            "path": observation["path"],
        },
    }

    return artifact, occurrence


def write_records(
    manifest_path: str | Path,
    source_id: str,
    role: str,
    output_root: str | Path,
) -> tuple[Path, Path]:
    """Write imported records and validate the resulting catalog graph."""

    artifact, occurrence = build_records(manifest_path, source_id, role)
    output = Path(output_root)
    artifact_dir = output / "artifacts"
    occurrence_dir = output / "occurrences"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    occurrence_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_dir / f"sha256-{artifact['sha256']}.json"
    occurrence_path = occurrence_dir / (
        f"{source_id}-{role}-{artifact['sha256'][:12]}.json"
    )

    artifact_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    occurrence_path.write_text(
        json.dumps(occurrence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Validate what we just emitted using the same loader downstream consumers use.
    Catalog.load(output)
    return artifact_path, occurrence_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import one explicit ingest file observation into catalog JSON."
    )
    parser.add_argument("manifest", type=Path, help="path to ingest manifest JSON")
    parser.add_argument(
        "--entry",
        required=True,
        dest="source_id",
        help="ingest entry source_id, for example K24",
    )
    parser.add_argument(
        "--file",
        required=True,
        dest="role",
        help="explicit file role, for example installer, run or screenshot",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="catalog output directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        artifact_path, occurrence_path = write_records(
            args.manifest,
            args.source_id,
            args.role,
            args.output,
        )
    except IngestImportError as exc:
        raise SystemExit(f"catalog ingest import failed: {exc}") from exc

    print(f"artifact: {artifact_path}")
    print(f"occurrence: {occurrence_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
