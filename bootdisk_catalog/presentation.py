"""Build disposable frontend projections from Catalog and ingest evidence.

The projection is intentionally not authoritative Catalog data. It joins editorial
source context to evidence-backed semantic identity so a frontend can present real
content without duplicating the preservation or catalog models.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalog import Catalog
from .curate import curation_queue, _load_manifest
from .intake import build_candidates, DIRECTOR_SCHEMA


def source_context(manifest_path):
    """Project original wording as observations, never as approved software facts."""
    path = Path(manifest_path)
    manifest, manifest_ref = _load_manifest(path)
    if manifest.get("schema_version") == DIRECTOR_SCHEMA:
        candidates = build_candidates(path.read_bytes())["candidates"]
        return {c["key"]["entry"]: {
            "key": c["key"], "description": c["observations"]["description"],
            "menu_groups": c["observations"]["menu_groups"],
            "issues": c["source_issues"], "preservation_scope": "launch_files_only",
        } for c in candidates}
    result = {}
    for position, entry in enumerate(manifest["entries"]):
        key = {"manifest": manifest_ref, "entry": entry["source_id"]}
        def observation(value, pointer):
            return {"value": value, "source_ref": {**key, "pointer": f"/entries/{position}/{pointer}"}}
        original = entry.get("raw", {}).get("Global")
        result[entry["source_id"]] = {
            "key": key,
            "description": observation(original, "raw/Global") if isinstance(original, str) and original.strip() else None,
            "menu_groups": observation(entry.get("normalized", {}).get("categories", []), "normalized/categories"),
            "issues": observation(entry.get("issues", []), "issues"),
        }
    return result


def _curated_descriptions(catalog: Catalog, subject_id: str) -> list[dict[str, str]]:
    return sorted(
        (
            {
                "description_id": description["id"],
                "language": description["language"],
                "text": description["text"],
            }
            for description in catalog.descriptions_for_subject(subject_id)
            if description["status"] == "curated"
        ),
        key=lambda item: (item["language"], item["description_id"]),
    )


def _identified_releases(catalog: Catalog, identification_ids: list[str]) -> list[dict[str, Any]]:
    releases = []
    seen: set[str] = set()
    for identification_id in identification_ids:
        identification = catalog.record(identification_id)
        release = catalog.release_for_identification(identification_id)
        software = catalog.record(release["software_id"])
        if release["id"] in seen:
            continue
        seen.add(release["id"])
        releases.append(
            {
                "software_id": software["id"],
                "software_name": software["name"],
                "content_kind": software.get("content_kind"),
                "release_id": release["id"],
                "version": release["version"],
                "identification_id": identification["id"],
                "status": identification["status"],
                "package_id": identification.get("package_id"),
                "distribution_kind": identification.get("distribution_kind"),
                "descriptions": _curated_descriptions(catalog, release["id"]),
            }
        )
    return sorted(releases, key=lambda item: (item["software_id"], item["release_id"]))


def presentation_projection(
    catalog: Catalog, manifest_path: str | Path
) -> list[dict[str, Any]]:
    """Return frontend-ready source cards without creating new catalog facts."""

    cards = []
    contexts = source_context(manifest_path)
    for item in curation_queue(catalog, manifest_path):
        cards.append(
            {
                "entry": item["entry"],
                # The title remains explicitly editorial source context. A frontend may
                # display it even while semantic identification is still pending.
                "editorial_title": item["title"],
                "source_context": contexts[item["entry"]],
                "curation_status": item["status"],
                "software": _identified_releases(catalog, item["identifications"]),
                # Paths are source observations. Publish is responsible for turning
                # suitable source assets into web-safe URLs/derivatives later.
                "occurrences": item["occurrences"],
            }
        )
    return cards


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a disposable frontend projection from Catalog and ingest evidence"
    )
    parser.add_argument("catalog_root")
    parser.add_argument("manifest")
    parser.add_argument("--entry", help="emit one exact source entry")
    parser.add_argument("--identified", action="store_true", help="emit only identified entries")
    args = parser.parse_args(argv)

    catalog = Catalog.load(Path(args.catalog_root))
    cards = presentation_projection(catalog, args.manifest)
    if args.entry:
        cards = [card for card in cards if card["entry"] == args.entry]
        if not cards:
            parser.error(f"source entry not found: {args.entry}")
    if args.identified:
        cards = [card for card in cards if card["curation_status"] == "identified"]

    print(json.dumps(cards, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
