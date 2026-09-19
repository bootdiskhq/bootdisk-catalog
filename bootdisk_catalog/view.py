"""Project the catalog graph into a stable software-centered presentation.

The JSON catalog remains authoritative. This module builds a disposable view from
existing relationships so command-line output and future presentation layers can
share the same traversal semantics without duplicating catalog facts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalog import Catalog, CatalogError


def _occurrence_sort_key(occurrence: dict[str, Any]) -> tuple[str, str, str, str]:
    source = occurrence["source_ref"]
    return (
        source.get("manifest", ""),
        source.get("entry", ""),
        source.get("path", ""),
        occurrence["id"],
    )


def software_view(catalog: Catalog, software_id: str) -> dict[str, Any]:
    """Return a deterministic presentation projection for one Software record.

    The projection contains no new catalog claims. Every relationship is derived
    from the authoritative ID-addressed graph and can therefore be rebuilt at any
    time.
    """

    software = catalog.record(software_id)
    if software["type"] != "software":
        raise CatalogError(
            f"catalog id {software_id!r} is {software['type']}, expected software"
        )

    releases = []
    for release in sorted(
        catalog.releases_for_software(software_id), key=lambda record: record["id"]
    ):
        artifacts = []
        for artifact in catalog.artifacts_for_release(release["id"]):
            occurrences = sorted(
                catalog.occurrences_for_artifact(artifact["id"]),
                key=_occurrence_sort_key,
            )
            artifacts.append(
                {
                    "id": artifact["id"],
                    "sha256": artifact["sha256"],
                    "size": artifact["size"],
                    "occurrences": [
                        {
                            "id": occurrence["id"],
                            "source_ref": dict(occurrence["source_ref"]),
                        }
                        for occurrence in occurrences
                    ],
                }
            )

        releases.append(
            {
                "id": release["id"],
                "version": release["version"],
                "artifacts": artifacts,
                "packages": [dict(p) for p in catalog.packages_for_release(release["id"])],
            }
        )

    return {
        "id": software["id"],
        "name": software["name"],
        "releases": releases,
    }


def format_software_view(view: dict[str, Any]) -> str:
    """Render a software projection as compact human-readable text."""

    lines = ["Software:", f"  {view['name']} ({view['id']})"]

    if not view["releases"]:
        lines.extend(["", "Releases:", "  none"])
        return "\n".join(lines)

    for release in view["releases"]:
        lines.extend(["", "Release:", f"  {release['version']} ({release['id']})"])

        for package in release.get("packages", []):
            lines.extend(["", "Package:", f"  {package['id']}",
                          f"  files: {len(package['members'])}",
                          f"  size: {package['total_size']}"])

        if not release["artifacts"]:
            lines.extend(["", "Artifact:", "  none"])
            continue

        for artifact in release["artifacts"]:
            lines.extend(
                [
                    "",
                    "Artifact:",
                    f"  {artifact['id']}",
                    f"  size: {artifact['size']}",
                ]
            )

            if not artifact["occurrences"]:
                lines.extend(["", "Occurrence:", "  none"])
                continue

            for occurrence in artifact["occurrences"]:
                source = occurrence["source_ref"]
                lines.extend(
                    [
                        "",
                        "Occurrence:",
                        f"  entry: {source.get('entry', '-')}",
                        f"  path:  {source.get('path', '-')}",
                    ]
                )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Present one Software record through its catalog relationships"
    )
    parser.add_argument("catalog_root")
    parser.add_argument("software_id")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit the derived presentation projection as JSON",
    )
    args = parser.parse_args(argv)

    catalog = Catalog.load(Path(args.catalog_root))
    view = software_view(catalog, args.software_id)

    if args.as_json:
        print(json.dumps(view, indent=2, ensure_ascii=False))
    else:
        print(format_software_view(view))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
