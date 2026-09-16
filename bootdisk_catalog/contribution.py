"""Validate portable curation contributions before they become Catalog truth.

A contribution is intentionally not a curation bundle. It is an untrusted proposal
that may be uploaded, reviewed and only later promoted into authoritative records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalog import SCHEMA
from .curation_bundle import BUNDLE_SCHEMA, CURATED_TYPES
from .identify import IdentificationError

CONTRIBUTION_SCHEMA = "bootdisk-catalog-contribution-0.1"
CONTRIBUTION_STATUS = "submitted"


def contribution_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Wrap preserved semantic records as a reviewable upload proposal."""
    if bundle.get("schema") != BUNDLE_SCHEMA or bundle.get("catalog_schema") != SCHEMA:
        raise IdentificationError("unsupported curation bundle schema")
    records = bundle.get("records")
    if not isinstance(records, list):
        raise IdentificationError("curation bundle records must be an array")
    contribution = {
        "schema": CONTRIBUTION_SCHEMA,
        "catalog_schema": SCHEMA,
        "status": CONTRIBUTION_STATUS,
        "records": records,
    }
    validate_contribution(contribution)
    return contribution


def validate_contribution(contribution: dict[str, Any]) -> int:
    """Validate the portable boundary without accepting the proposal as truth."""
    if contribution.get("schema") != CONTRIBUTION_SCHEMA:
        raise IdentificationError("unsupported contribution schema")
    if contribution.get("catalog_schema") != SCHEMA:
        raise IdentificationError("unsupported catalog schema")
    if contribution.get("status") != CONTRIBUTION_STATUS:
        raise IdentificationError("uploaded contribution status must be submitted")
    records = contribution.get("records")
    if not isinstance(records, list):
        raise IdentificationError("contribution records must be an array")
    if any(not isinstance(record, dict) for record in records):
        raise IdentificationError("contribution records must be objects")
    if any(record.get("type") not in CURATED_TYPES for record in records):
        raise IdentificationError("contribution contains a non-curated record type")
    ids = [record.get("id") for record in records]
    if any(not isinstance(record_id, str) or not record_id for record_id in ids):
        raise IdentificationError("contribution records require stable ids")
    if len(ids) != len(set(ids)):
        raise IdentificationError("contribution contains duplicate record ids")
    return len(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or validate a Bootdisk curation contribution")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("bundle", type=Path)
    prepare.add_argument("output", type=Path)

    validate = subparsers.add_parser("validate")
    validate.add_argument("contribution", type=Path)
    args = parser.parse_args(argv)

    if args.command == "prepare":
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        contribution = contribution_from_bundle(bundle)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(contribution, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"contribution records: {len(contribution['records'])}")
        return 0

    contribution = json.loads(args.contribution.read_text(encoding="utf-8"))
    print(f"contribution records valid: {validate_contribution(contribution)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
