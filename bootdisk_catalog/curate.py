"""Build a curator-facing review queue from ingest evidence and catalog state.

This module does not infer software identity. It joins an exact ingest manifest to
Catalog Occurrences and existing Identification evidence so a human can see what
still needs semantic review before making catalog claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .catalog import Catalog


class CurationError(Exception):
    """Raised when a curation queue cannot be derived safely."""


def _load_manifest(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        manifest = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CurationError(f"cannot read ingest manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("entries"), list):
        raise CurationError("ingest manifest must contain an entries array")
    return manifest, f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _identifications_for_source(
    catalog: Catalog, manifest_ref: str, entry_id: str
) -> list[dict[str, Any]]:
    matches = []
    for identification in catalog.records_of_type("identification"):
        # Curation state belongs to the evidence source, not merely to an Artifact.
        # This matters when byte-identical generic files occur in unrelated entries.
        if any(
            evidence.get("source_ref", {}).get("manifest") == manifest_ref
            and evidence.get("source_ref", {}).get("entry") == entry_id
            for evidence in identification["evidence"]
        ):
            matches.append(identification)
    return sorted(matches, key=lambda record: record["id"])


def curation_queue(
    catalog: Catalog, manifest_path: str | Path
) -> list[dict[str, Any]]:
    """Return a deterministic, evidence-aware review queue for one ingest manifest."""

    manifest, manifest_ref = _load_manifest(Path(manifest_path))
    occurrences = [
        occurrence
        for occurrence in catalog.records_of_type("occurrence")
        if occurrence["source_ref"].get("manifest") == manifest_ref
    ]

    by_entry: dict[str, list[dict[str, Any]]] = {}
    for occurrence in occurrences:
        entry_id = occurrence["source_ref"].get("entry")
        if entry_id:
            by_entry.setdefault(entry_id, []).append(occurrence)

    queue = []
    seen_entries: set[str] = set()
    for entry in manifest["entries"]:
        entry_id = entry.get("source_id")
        if not isinstance(entry_id, str) or not entry_id:
            raise CurationError("every ingest entry must have a non-empty source_id")
        if entry_id in seen_entries:
            raise CurationError(f"duplicate ingest entry source_id: {entry_id}")
        seen_entries.add(entry_id)

        normalized = entry.get("normalized")
        title = normalized.get("title") if isinstance(normalized, dict) else None
        entry_occurrences = sorted(
            by_entry.get(entry_id, []),
            key=lambda record: (
                record["source_ref"].get("path", ""), record["artifact_id"], record["id"]
            ),
        )
        identifications = _identifications_for_source(catalog, manifest_ref, entry_id)

        queue.append(
            {
                "entry": entry_id,
                "title": title,
                "status": "identified" if identifications else "pending",
                "occurrences": [
                    {
                        "artifact_id": occurrence["artifact_id"],
                        "path": occurrence["source_ref"].get("path"),
                    }
                    for occurrence in entry_occurrences
                ],
                "identifications": [record["id"] for record in identifications],
            }
        )

    # Preserve manifest order deliberately. Editorial/source order is evidence too,
    # and curation does not need to rewrite it merely to make K-numbers look numeric.
    return queue


def select_curation_entry(
    queue: list[dict[str, Any]], entry_id: str
) -> dict[str, Any]:
    """Select exactly one source entry from a derived curation queue."""

    matches = [item for item in queue if item["entry"] == entry_id]
    if not matches:
        raise CurationError(f"ingest entry not found in curation queue: {entry_id}")
    if len(matches) != 1:
        raise CurationError(f"ambiguous ingest entry in curation queue: {entry_id}")
    return matches[0]


def format_curation_queue(
    queue: list[dict[str, Any]], *, pending_only: bool = False
) -> str:
    """Render the review queue without turning editorial titles into catalog facts."""

    visible = [item for item in queue if not pending_only or item["status"] == "pending"]
    lines = []
    for item in visible:
        title = item["title"] if item["title"] is not None else "-"
        lines.append(f"{item['entry']}  [{item['status']}]  {title}")
        for occurrence in item["occurrences"]:
            lines.append(f"  {occurrence['artifact_id']}")
            lines.append(f"    path: {occurrence['path'] or '-'}")
        if not item["occurrences"]:
            lines.append("  no preserved occurrences")
    return "\n".join(lines)


def format_curation_entry(item: dict[str, Any]) -> str:
    """Render one source entry as compact human review context."""

    title = item["title"] if item["title"] is not None else "-"
    lines = [
        "Curation review:",
        f"  entry:  {item['entry']}",
        f"  status: {item['status']}",
        f"  editorial title: {title}",
        "",
        "Preserved occurrences:",
    ]
    for occurrence in item["occurrences"]:
        lines.append(f"  {occurrence['artifact_id']}")
        lines.append(f"    path: {occurrence['path'] or '-'}")
    if not item["occurrences"]:
        lines.append("  none")

    if item["identifications"]:
        lines.extend(["", "Existing identifications:"])
        lines.extend(f"  {identification_id}" for identification_id in item["identifications"])

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review ingest entries against evidence-backed catalog curation state"
    )
    parser.add_argument("catalog_root")
    parser.add_argument("manifest")
    parser.add_argument(
        "--pending", action="store_true", help="show only entries still needing curation"
    )
    parser.add_argument(
        "--entry", help="review one exact ingest source_id instead of the whole queue"
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="emit the review queue as JSON"
    )
    args = parser.parse_args(argv)

    catalog = Catalog.load(Path(args.catalog_root))
    queue = curation_queue(catalog, args.manifest)

    if args.entry:
        item = select_curation_entry(queue, args.entry)
        if args.pending and item["status"] != "pending":
            raise CurationError(f"ingest entry is already identified: {args.entry}")
        if args.as_json:
            print(json.dumps(item, indent=2, ensure_ascii=False))
        else:
            print(format_curation_entry(item))
        return 0

    if args.pending:
        queue = [item for item in queue if item["status"] == "pending"]

    if args.as_json:
        print(json.dumps(queue, indent=2, ensure_ascii=False))
    else:
        print(format_curation_queue(queue))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
