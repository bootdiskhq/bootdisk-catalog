"""Build disposable frontend projections from Catalog and ingest evidence.

The projection is intentionally not authoritative Catalog data. It joins editorial
source context to evidence-backed semantic identity so a frontend can present real
content without duplicating the preservation or catalog models.
"""

from __future__ import annotations

import argparse
import base64
import configparser
import hashlib
import json
from pathlib import Path
from typing import Any

from .catalog import Catalog, CatalogError
from .curate import curation_queue, _load_manifest
from .intake import build_candidates, DIRECTOR_SCHEMA


def _tools_description(manifest, entry):
    """Validate the Norwegian observation against the preserved DTX bytes."""
    evidence = entry.get("evidence", {})
    claim = evidence.get("description_tools")
    if claim is None:
        return None
    if not isinstance(claim, dict):
        raise CatalogError("invalid Tools description evidence")
    sources = [s for s in manifest.get("source", {}).get("supplemental_metadata", [])
               if s.get("resolved_path", s.get("path")) == claim.get("path")]
    if len(sources) != 1:
        raise CatalogError("Tools description requires one preserved metadata source")
    source = sources[0]
    try:
        raw = base64.b64decode(source.get("raw_base64", ""), validate=True)
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read_string(raw.decode("cp1252"))
        section = dict(parser[entry["source_id"]])
    except (ValueError, TypeError, KeyError, UnicodeError, configparser.Error) as exc:
        raise CatalogError("invalid preserved Tools metadata") from exc
    binding = {"path": source.get("resolved_path", source.get("path")), "sha256": hashlib.sha256(raw).hexdigest(),
               "section": entry["source_id"]}
    inventory = [f for f in manifest.get("file_inventory", []) if f.get("path") == binding["path"]]
    if not (source.get("encoding") == "cp1252" and source.get("size") == len(raw)
            and source.get("sha256") == binding["sha256"]
            and len(inventory) == 1 and inventory[0].get("sha256") == binding["sha256"]
            and inventory[0].get("size") == len(raw)
            and evidence.get("metadata_source") == binding
            and all(claim.get(k) == v for k, v in binding.items())
            and claim.get("field") == "InstruksNo" and claim.get("language") == "nb-NO"
            and source.get("sections", {}).get(entry["source_id"]) == section
            and entry.get("raw") == section
            and claim.get("text") == section.get("InstruksNo")):
        raise CatalogError("Tools description does not match preserved metadata")
    text = claim.get("text")
    return text if isinstance(text, str) and text.strip() else None


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
        tools = _tools_description(manifest, entry)
        original = entry.get("raw", {}).get("Global")
        description = observation(original, "raw/Global") if isinstance(original, str) and original.strip() else None
        is_tools = "description_tools" in entry.get("evidence", {})
        if is_tools:
            description = observation(tools, "evidence/description_tools/text") if tools is not None else None
        rtf = None if is_tools else entry.get("evidence", {}).get("description_rtf")
        if description is None and isinstance(rtf, dict) and isinstance(rtf.get("text"), str) and rtf["text"].strip():
            file = entry.get("files", {}).get("discovered", {}).get("description_rtf", {})
            inventory = [f for f in manifest.get("file_inventory", []) if f.get("path") == rtf.get("path")]
            try:
                raw = base64.b64decode(rtf.get("raw_base64", ""), validate=True)
            except (ValueError, TypeError) as exc:
                raise CatalogError("invalid RTF source bytes") from exc
            if not (rtf.get("method") == "rtf-ansi-text-1" and file.get("exists") is True
                    and rtf.get("path") == file.get("resolved_path", file.get("path"))
                    and len(inventory) == 1 and rtf.get("size") == len(raw)
                    and rtf.get("sha256") == hashlib.sha256(raw).hexdigest()
                    and all(rtf.get(k) == file.get(k) == inventory[0].get(k) for k in ("sha256", "size"))):
                raise CatalogError("RTF source does not match observed file")
            description = observation(rtf["text"], "evidence/description_rtf/text")
        result[entry["source_id"]] = {
            "key": key,
            "description": description,
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
    catalog: Catalog, manifest_path: str | Path, *, previous_manifest: str | Path | None = None
) -> list[dict[str, Any]]:
    """Return frontend-ready source cards without creating new catalog facts."""

    cards = []
    contexts = source_context(manifest_path)
    inherited = {}
    if previous_manifest is not None:
        old, _ = _load_manifest(Path(previous_manifest))
        new, _ = _load_manifest(Path(manifest_path))
        old_entries = old["entries"]
        new_entries = new["entries"]
        # A strict append-only expansion. No decisions are copied into a new
        # evidence document; the disposable view retains their original binding.
        if (len(new_entries) <= len(old_entries)
                or new_entries[:len(old_entries)] != old_entries
                or len({e["source_id"] for e in new_entries}) != len(new_entries)
                or old.get("file_inventory") != new.get("file_inventory")
                or any(new.get("source", {}).get(k) != v for k, v in old.get("source", {}).items())):
            raise CatalogError("previous manifest is not an unchanged append-only source")
        inherited = {card["entry"]: card for card in presentation_projection(catalog, previous_manifest)}
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
    for card in cards:
        previous = inherited.get(card["entry"])
        if previous is not None:
            if card["software"]:
                raise CatalogError("expanded manifest already has decisions; resolve explicitly")
            card["software"] = previous["software"]
            card["curation_status"] = previous["curation_status"]
            card["decision_source"] = previous["source_context"]["key"]
    return cards


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a disposable frontend projection from Catalog and ingest evidence"
    )
    parser.add_argument("catalog_root")
    parser.add_argument("manifest")
    parser.add_argument("--previous-manifest", help="verified append-only predecessor; retain original decision binding")
    parser.add_argument("--entry", help="emit one exact source entry")
    parser.add_argument("--identified", action="store_true", help="emit only identified entries")
    args = parser.parse_args(argv)

    catalog = Catalog.load(Path(args.catalog_root))
    cards = presentation_projection(catalog, args.manifest, previous_manifest=args.previous_manifest)
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
