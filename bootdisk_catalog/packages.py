"""Reconstruct source-entry inventories as packages, distinct from file bytes.

The ingest path/NUL/SHA-256/newline framing is preserved exactly. These packages
include editorial assets and are observations, not claims of installation closure.
"""
from pathlib import Path

from .catalog import SCHEMA, Catalog, LoadedRecord
from .import_ingest import IngestImportError, _write_json


def import_packages(manifest, output):
    # Director inventories contain literal launch targets, not source-entry
    # folders. Never turn the shared launcher set into a package identity.
    if manifest.get("schema_version") == "kcd-director-experimental-1":
        return
    inventory = manifest.get("file_inventory")
    entries = [e for e in manifest["entries"] if "inventory_refs" in e.get("files", {})]
    if not entries:
        return
    if not isinstance(inventory, list):
        raise IngestImportError("package inventory requires file_inventory")
    by_path = {}
    for item in inventory:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise IngestImportError("invalid package inventory item")
        if item["path"] in by_path:
            raise IngestImportError("duplicate inventory path")
        by_path[item["path"]] = item
    records = {}
    for entry in entries:
        refs = entry["files"]["inventory_refs"]
        identity = entry.get("content_identity", {})
        if not isinstance(refs, list) or not refs or any(not isinstance(p, str) for p in refs):
            raise IngestImportError("package inventory_refs must be non-empty paths")
        if len(refs) != len(set(refs)):
            raise IngestImportError("duplicate package inventory reference")
        members = []
        for path in sorted(refs):
            if path not in by_path:
                raise IngestImportError(f"missing package inventory member: {path}")
            item = by_path[path]
            artifact = {"schema": SCHEMA, "type": "artifact",
                        "id": "artifact:sha256:" + str(item.get("sha256")),
                        "sha256": item.get("sha256"), "size": item.get("size")}
            old = records.get(artifact["id"])
            if old is not None and old != artifact:
                raise IngestImportError("conflicting package artifact sizes")
            records[artifact["id"]] = artifact
            members.append({"path": path, "artifact_id": artifact["id"], "size": artifact["size"]})
        if identity.get("algorithm") != "sha256" or identity.get("file_count") != len(members):
            raise IngestImportError("invalid package content identity")
        package = {"schema": SCHEMA, "type": "package",
                   "id": "package:sha256:" + str(identity.get("manifest_sha256")),
                   "total_size": identity.get("total_size"), "members": members}
        records[package["id"]] = package
    # Verify the complete reconstruction before writing package records.
    Catalog(LoadedRecord(r, Path("<manifest>")) for r in records.values())
    for record in records.values():
        directory = Path(output) / ("packages" if record["type"] == "package" else "artifacts")
        directory.mkdir(parents=True, exist_ok=True)
        _write_json(directory / ("sha256-" + record["id"].split(":")[-1] + ".json"), record)
