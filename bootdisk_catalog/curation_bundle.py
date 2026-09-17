"""Export and restore human-curated Catalog knowledge independently of imports.

Artifacts and Occurrences are reproducible from ingest manifests. Software identity,
releases, identifications and descriptions are human knowledge and therefore need a
portable, versionable representation of their own.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalog import Catalog, SCHEMA
from .identify import IdentificationError, _canonical_json, _preflight_record, _record_path

BUNDLE_SCHEMA = "bootdisk-catalog-curation-0.1"
CURATED_TYPES = (
    "software",
    "software_release",
    "identification",
    "description",
)


def export_bundle(catalog: Catalog) -> dict[str, Any]:
    """Return only semantic records that cannot be reconstructed from Ingest."""
    records = []
    for record_type in CURATED_TYPES:
        records.extend(catalog.records_of_type(record_type))
    records.sort(key=lambda record: (record["type"], record["id"]))
    return {"schema": BUNDLE_SCHEMA, "catalog_schema": SCHEMA, "records": records}


def restore_bundle(catalog_root: str | Path, bundle: dict[str, Any]) -> int:
    """Restore a curation bundle without overwriting conflicting knowledge."""
    if bundle.get("schema") != BUNDLE_SCHEMA or bundle.get("catalog_schema") != SCHEMA:
        raise IdentificationError("unsupported curation bundle schema")
    records = bundle.get("records")
    if not isinstance(records, list):
        raise IdentificationError("curation bundle records must be an array")
    if any(record.get("type") not in CURATED_TYPES for record in records):
        raise IdentificationError("curation bundle contains a non-curated record type")

    root = Path(catalog_root)
    paths = [_record_path(root, record) for record in records]
    # Preflight the complete bundle first. A conflict must never leave a partially
    # restored semantic graph on top of reproducible import data.
    for path, record in zip(paths, records):
        _preflight_record(path, record)
    for path, record in zip(paths, records):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_canonical_json(record), encoding="utf-8")
    Catalog.load(root)
    return len(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preserve or restore human-curated Catalog knowledge")
    subparsers = parser.add_subparsers(dest="command", required=True)
    export = subparsers.add_parser("export")
    export.add_argument("catalog_root")
    export.add_argument("output", type=Path)
    restore = subparsers.add_parser("restore")
    restore.add_argument("catalog_root")
    restore.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)

    if args.command == "export":
        bundle = export_bundle(Catalog.load(Path(args.catalog_root)))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"curation records: {len(bundle['records'])}")
        return 0

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    print(f"curation records restored: {restore_bundle(args.catalog_root, bundle)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
