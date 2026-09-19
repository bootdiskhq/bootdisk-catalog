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
from typing import Any, Iterator

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


def _validate_observation(observation: dict[str, Any], role: str) -> dict[str, Any]:
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


def _find_file(entry: dict[str, Any], role: str) -> dict[str, Any]:
    """Resolve one explicit file observation by semantic role."""

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

    return _validate_observation(found[0], role)


def _iter_observations(
    manifest: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Yield every explicit preserved file observation in manifest order.

    Missing observations are evidence too, but they do not describe preserved
    bytes and therefore cannot become Artifact records. Structurally invalid
    observations still fail the import rather than being silently ignored.
    """

    seen_source_ids: set[str] = set()
    for entry in manifest["entries"]:
        if not isinstance(entry, dict):
            raise IngestImportError("ingest entries must be JSON objects")

        source_id = entry.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise IngestImportError("ingest entry has invalid source_id")
        if source_id in seen_source_ids:
            raise IngestImportError(f"duplicate ingest source_id: {source_id}")
        seen_source_ids.add(source_id)

        files = entry.get("files")
        if not isinstance(files, dict):
            raise IngestImportError(f"ingest entry {source_id} has no files object")

        roles: dict[str, dict[str, Any]] = {}
        for section_name in ("referenced", "discovered"):
            section = files.get(section_name, {})
            if not isinstance(section, dict):
                raise IngestImportError(
                    f"entry {source_id}: files.{section_name} must be an object"
                )
            for role, observation in section.items():
                if role in roles:
                    raise IngestImportError(
                        f"entry {source_id}: ambiguous file role: {role}"
                    )
                if not isinstance(observation, dict):
                    raise IngestImportError(
                        f"entry {source_id}: files.{section_name}.{role} must be an object"
                    )
                roles[role] = observation

        for role, observation in roles.items():
            # A declared-but-missing file has no byte identity to import.
            if observation.get("exists") is not True or observation.get("is_file") is not True:
                continue
            yield source_id, role, _validate_observation(observation, role)


def _records_for_observation(
    manifest_digest: str,
    source_id: str,
    role: str,
    observation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact_digest = observation["sha256"]
    artifact_id = f"artifact:sha256:{artifact_digest}"

    artifact = {
        "schema": SCHEMA,
        "type": "artifact",
        "id": artifact_id,
        "sha256": artifact_digest,
        "size": observation["size"],
    }

    # Occurrence identity uses the immutable evidence document plus its semantic
    # location. The observed filesystem path remains evidence, never identity.
    occurrence = {
        "schema": SCHEMA,
        "type": "occurrence",
        "id": f"occurrence:{manifest_digest}:{source_id}:{role}",
        "artifact_id": artifact_id,
        "source_ref": {
            "manifest": f"sha256:{manifest_digest}",
            "entry": source_id,
            "path": observation["path"],
        },
    }
    return artifact, occurrence


def build_records(
    manifest_path: str | Path,
    source_id: str,
    role: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one Artifact and one Occurrence for focused debugging/tests."""

    manifest, manifest_digest = _read_manifest(Path(manifest_path))
    entry = _find_entry(manifest, source_id)
    observation = _find_file(entry, role)
    return _records_for_observation(manifest_digest, source_id, role, observation)


def _write_json(path: Path, record: dict[str, Any]) -> None:
    """Write deterministically without silently replacing conflicting catalog data."""

    content = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise IngestImportError(f"cannot read existing catalog record {path}: {exc}") from exc
        if existing != content:
            raise IngestImportError(f"refusing to overwrite conflicting catalog record: {path}")
        return
    path.write_text(content, encoding="utf-8")


def _write_record_pair(
    artifact: dict[str, Any],
    occurrence: dict[str, Any],
    source_id: str,
    role: str,
    output: Path,
) -> tuple[Path, Path]:
    artifact_dir = output / "artifacts"
    occurrence_dir = output / "occurrences"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    occurrence_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_dir / f"sha256-{artifact['sha256']}.json"
    occurrence_path = occurrence_dir / (
        f"{source_id}-{role}-{artifact['sha256'][:12]}.json"
    )
    _write_json(artifact_path, artifact)
    _write_json(occurrence_path, occurrence)
    return artifact_path, occurrence_path


def write_records(
    manifest_path: str | Path,
    source_id: str,
    role: str,
    output_root: str | Path,
) -> tuple[Path, Path]:
    """Write one focused observation and validate the resulting catalog graph."""

    artifact, occurrence = build_records(manifest_path, source_id, role)
    paths = _write_record_pair(artifact, occurrence, source_id, role, Path(output_root))
    Catalog.load(Path(output_root))
    return paths


def import_manifest(
    manifest_path: str | Path,
    output_root: str | Path,
) -> tuple[int, int]:
    """Import all explicit preserved file observations from one ingest manifest.

    Artifact records naturally deduplicate by SHA-256 while every source entry and
    role receives its own Occurrence. This preserves the distinction between the
    bytes themselves and each place those bytes were observed.
    """

    manifest, manifest_digest = _read_manifest(Path(manifest_path))
    output = Path(output_root)
    artifact_ids: set[str] = set()
    occurrence_count = 0

    for source_id, role, observation in _iter_observations(manifest):
        artifact, occurrence = _records_for_observation(
            manifest_digest, source_id, role, observation
        )
        _write_record_pair(artifact, occurrence, source_id, role, output)
        artifact_ids.add(artifact["id"])
        occurrence_count += 1

    from .packages import import_packages
    import_packages(manifest, output)

    # Validate the complete graph only after all references have been materialized.
    Catalog.load(output)
    return len(artifact_ids), occurrence_count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import explicit preservation observations from an ingest manifest."
    )
    parser.add_argument("manifest", type=Path, help="path to ingest manifest JSON")
    parser.add_argument(
        "--entry",
        dest="source_id",
        help="optional source_id filter for focused debugging",
    )
    parser.add_argument(
        "--file",
        dest="role",
        help="optional file-role filter for focused debugging",
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

    # Filters form a pair: accepting only one would make CLI semantics surprising
    # and could accidentally imply cross-entry or cross-role selection behavior.
    if (args.source_id is None) != (args.role is None):
        raise SystemExit("catalog ingest import failed: --entry and --file must be used together")

    try:
        if args.source_id is not None:
            artifact_path, occurrence_path = write_records(
                args.manifest, args.source_id, args.role, args.output
            )
            print(f"artifact: {artifact_path}")
            print(f"occurrence: {occurrence_path}")
        else:
            artifact_count, occurrence_count = import_manifest(args.manifest, args.output)
            print(f"artifacts: {artifact_count}")
            print(f"occurrences: {occurrence_count}")
    except IngestImportError as exc:
        raise SystemExit(f"catalog ingest import failed: {exc}") from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
