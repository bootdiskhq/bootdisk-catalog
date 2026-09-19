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
from .curate import curation_queue


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
                "release_id": release["id"],
                "version": release["version"],
                "identification_id": identification["id"],
                "status": identification["status"],
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
    for item in curation_queue(catalog, manifest_path):
        cards.append(
            {
                "entry": item["entry"],
                # The title remains explicitly editorial source context. A frontend may
                # display it even while semantic identification is still pending.
                "editorial_title": item["title"],
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
