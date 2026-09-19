"""Load and validate Bootdisk catalog records as an ID-addressed graph.

The authoritative data remains JSON. This module builds disposable in-memory
indexes so callers can navigate relationships without turning filesystem layout
into part of catalog identity.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable


SCHEMA = "bootdisk-catalog-0.1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA256_REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "software": ("schema", "type", "id", "name"),
    "software_release": ("schema", "type", "id", "software_id", "version"),
    "artifact": ("schema", "type", "id", "sha256", "size"),
    "package": ("schema", "type", "id", "members", "total_size"),
    "occurrence": ("schema", "type", "id", "artifact_id", "source_ref"),
    "identification": (
        "schema",
        "type",
        "id",
        "software_release_id",
        "status",
        "evidence",
    ),
    "description": (
        "schema",
        "type",
        "id",
        "subject_id",
        "language",
        "text",
        "status",
        "evidence",
    ),
}

ID_PREFIXES = {
    "software": "software:",
    "software_release": "release:",
    "artifact": "artifact:sha256:",
    "package": "package:sha256:",
    "occurrence": "occurrence:",
    "identification": "identification:",
    "description": "description:",
}

IDENTIFICATION_STATUSES = {"interpreted", "curated"}
IDENTIFICATION_DISTRIBUTION_KINDS = {"full", "demo", "trial", "update", "unknown"}
DESCRIPTION_STATUSES = {"draft", "curated"}
EVIDENCE_KINDS = {"observed", "derived", "interpreted", "curated"}
LANGUAGE_TAG_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")


class CatalogError(Exception):
    """Base exception for catalog loading and lookup errors."""


class CatalogValidationError(CatalogError):
    """Raised when catalog records violate the catalog contract."""


@dataclass(frozen=True)
class LoadedRecord:
    """A record plus its source file, retained only for diagnostics."""

    data: dict[str, Any]
    path: Path


class Catalog:
    """An immutable-by-convention in-memory view of catalog JSON records."""

    def __init__(self, records: Iterable[LoadedRecord]) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._paths: dict[str, Path] = {}
        self._by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for loaded in records:
            self._add_record(loaded)

        self._validate_references()

    @classmethod
    def load(cls, root: str | Path) -> "Catalog":
        """Load every JSON record beneath *root*.

        Directory names and filenames intentionally have no semantic meaning.
        Records are addressed exclusively by their internal stable IDs.
        """

        root_path = Path(root)
        if not root_path.exists():
            raise CatalogError(f"catalog root does not exist: {root_path}")
        if not root_path.is_dir():
            raise CatalogError(f"catalog root is not a directory: {root_path}")

        loaded: list[LoadedRecord] = []
        for path in sorted(root_path.rglob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CatalogValidationError(f"cannot load {path}: {exc}") from exc

            if not isinstance(data, dict):
                raise CatalogValidationError(
                    f"catalog record must be a JSON object: {path}"
                )
            loaded.append(LoadedRecord(data=data, path=path))

        return cls(loaded)

    def record(self, record_id: str) -> dict[str, Any]:
        """Return one record by stable catalog ID."""

        try:
            return self._records[record_id]
        except KeyError as exc:
            raise CatalogError(f"unknown catalog id: {record_id}") from exc

    def records_of_type(self, record_type: str) -> tuple[dict[str, Any], ...]:
        return tuple(self._by_type.get(record_type, ()))

    def releases_for_software(self, software_id: str) -> tuple[dict[str, Any], ...]:
        self._require_type(software_id, "software")
        return tuple(
            record
            for record in self._by_type["software_release"]
            if record["software_id"] == software_id
        )

    def identifications_for_artifact(
        self, artifact_id: str
    ) -> tuple[dict[str, Any], ...]:
        self._require_type(artifact_id, "artifact")
        return tuple(
            record
            for record in self._by_type["identification"]
            if record.get("artifact_id") == artifact_id
        )

    def artifacts_for_release(
        self, software_release_id: str
    ) -> tuple[dict[str, Any], ...]:
        self._require_type(software_release_id, "software_release")
        artifact_ids = {
            record["artifact_id"]
            for record in self._by_type["identification"]
            if record["software_release_id"] == software_release_id and "artifact_id" in record
        }
        return tuple(self._records[record_id] for record_id in sorted(artifact_ids))

    def occurrences_for_artifact(
        self, artifact_id: str
    ) -> tuple[dict[str, Any], ...]:
        self._require_type(artifact_id, "artifact")
        return tuple(
            record
            for record in self._by_type["occurrence"]
            if record.get("artifact_id") == artifact_id
        )

    def release_for_identification(self, identification_id: str) -> dict[str, Any]:
        identification = self._require_type(identification_id, "identification")
        return self._records[identification["software_release_id"]]

    def artifact_for_identification(self, identification_id: str) -> dict[str, Any]:
        identification = self._require_type(identification_id, "identification")
        if "artifact_id" not in identification:
            raise CatalogError("identification targets a package, not a single artifact")
        return self._records[identification["artifact_id"]]

    def descriptions_for_subject(
        self, subject_id: str
    ) -> tuple[dict[str, Any], ...]:
        self.record(subject_id)
        return tuple(
            record
            for record in self._by_type["description"]
            if record["subject_id"] == subject_id
        )

    def _add_record(self, loaded: LoadedRecord) -> None:
        record = loaded.data
        record_type = record.get("type")

        if record_type not in REQUIRED_FIELDS:
            raise CatalogValidationError(
                f"unknown catalog record type in {loaded.path}: {record_type!r}"
            )

        self._validate_record_shape(record, loaded.path)
        record_id = record["id"]

        if record_id in self._records:
            first_path = self._paths[record_id]
            raise CatalogValidationError(
                f"duplicate catalog id {record_id!r}: {first_path} and {loaded.path}"
            )

        self._records[record_id] = record
        self._paths[record_id] = loaded.path
        self._by_type[record_type].append(record)

    def _validate_record_shape(self, record: dict[str, Any], path: Path) -> None:
        record_type = record["type"]
        missing = [
            field for field in REQUIRED_FIELDS[record_type] if field not in record
        ]
        if missing:
            raise CatalogValidationError(
                f"missing required fields in {path}: {', '.join(missing)}"
            )

        if record["schema"] != SCHEMA:
            raise CatalogValidationError(
                f"unsupported schema in {path}: {record['schema']!r}"
            )

        record_id = record["id"]
        if not isinstance(record_id, str) or not record_id.startswith(
            ID_PREFIXES[record_type]
        ):
            raise CatalogValidationError(
                f"invalid id for {record_type} in {path}: {record_id!r}"
            )

        if record_type == "artifact":
            self._validate_artifact(record, path)
        elif record_type == "package":
            self._validate_package(record, path)
        elif record_type == "occurrence":
            self._validate_source_ref(record["source_ref"], path, "source_ref")
        elif record_type == "identification":
            self._validate_identification(record, path)
        elif record_type == "description":
            self._validate_description(record, path)

    def _validate_artifact(self, record: dict[str, Any], path: Path) -> None:
        digest = record["sha256"]
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise CatalogValidationError(f"invalid sha256 in {path}: {digest!r}")

        expected_id = f"artifact:sha256:{digest}"
        if record["id"] != expected_id:
            raise CatalogValidationError(
                f"artifact id must match sha256 in {path}: expected {expected_id!r}"
            )

        size = record["size"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise CatalogValidationError(f"invalid artifact size in {path}: {size!r}")

    def packages_for_release(self, release_id):
        self._require_type(release_id, "software_release")
        ids = {r["package_id"] for r in self._by_type["identification"]
               if r["software_release_id"] == release_id and "package_id" in r}
        return tuple(self._records[i] for i in sorted(ids))

    def _validate_package(self, record, path):
        members = record["members"]
        if not isinstance(members, list) or not members:
            raise CatalogValidationError("package members must be a non-empty list")
        paths = set()
        frames = []
        total = 0
        for member in members:
            if not isinstance(member, dict):
                raise CatalogValidationError("package member must be an object")
            name = member.get("path")
            artifact_id = member.get("artifact_id")
            if not isinstance(artifact_id, str):
                raise CatalogValidationError("package member requires an artifact_id")
            digest = artifact_id.removeprefix("artifact:sha256:")
            size = member.get("size")
            if (not isinstance(name, str) or not name or name in paths
                    or any(c in name for c in "\0\n\r")
                    or name.startswith("/") or ".." in name.split("/")):
                raise CatalogValidationError("invalid or duplicate package member path")
            if (not SHA256_RE.fullmatch(digest)
                    or member.get("artifact_id") != "artifact:sha256:" + digest
                    or not isinstance(size, int) or isinstance(size, bool) or size < 0):
                raise CatalogValidationError("invalid package member identity or size")
            paths.add(name)
            frames.append((name, digest))
            total += size
        digest = hashlib.sha256("".join(
            name + "\0" + value + "\n" for name, value in sorted(frames)
        ).encode("utf-8")).hexdigest()
        if record["id"] != "package:sha256:" + digest:
            raise CatalogValidationError("package id must match its member inventory")
        if (not isinstance(record["total_size"], int)
                or isinstance(record["total_size"], bool) or record["total_size"] != total):
            raise CatalogValidationError("package total_size must match its members")

    def _validate_identification(
        self, record: dict[str, Any], path: Path
    ) -> None:
        targets = [key for key in ("artifact_id", "package_id") if key in record]
        if len(targets) != 1:
            raise CatalogValidationError("identification requires exactly one artifact_id or package_id")
        status = record["status"]
        if status not in IDENTIFICATION_STATUSES:
            raise CatalogValidationError(
                f"invalid identification status in {path}: {status!r}"
            )

        distribution_kind = record.get("distribution_kind")
        if (
            distribution_kind is not None
            and distribution_kind not in IDENTIFICATION_DISTRIBUTION_KINDS
        ):
            raise CatalogValidationError(
                f"invalid identification distribution_kind in {path}: "
                f"{distribution_kind!r}"
            )

        evidence = record["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise CatalogValidationError(
                f"identification evidence must be a non-empty list in {path}"
            )

        for index, item in enumerate(evidence):
            label = f"evidence[{index}]"
            if not isinstance(item, dict):
                raise CatalogValidationError(f"{label} must be an object in {path}")

            missing = [
                field
                for field in ("kind", "source_ref", "field", "value")
                if field not in item
            ]
            if missing:
                raise CatalogValidationError(
                    f"missing fields in {label} in {path}: {', '.join(missing)}"
                )

            if item["kind"] not in EVIDENCE_KINDS:
                raise CatalogValidationError(
                    f"invalid knowledge kind in {label} in {path}: {item['kind']!r}"
                )

            self._validate_source_ref(item["source_ref"], path, label)

    def _validate_description(self, record: dict[str, Any], path: Path) -> None:
        language = record["language"]
        if not isinstance(language, str) or not LANGUAGE_TAG_RE.fullmatch(language):
            raise CatalogValidationError(
                f"invalid description language in {path}: {language!r}"
            )

        text = record["text"]
        if not isinstance(text, str) or not text.strip():
            raise CatalogValidationError(
                f"description text must not be empty in {path}"
            )

        status = record["status"]
        if status not in DESCRIPTION_STATUSES:
            raise CatalogValidationError(
                f"invalid description status in {path}: {status!r}"
            )

        evidence = record["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise CatalogValidationError(
                f"description evidence must be a non-empty list in {path}"
            )
        for index, item in enumerate(evidence):
            label = f"evidence[{index}]"
            if not isinstance(item, dict):
                raise CatalogValidationError(f"{label} must be an object in {path}")
            missing = [
                field
                for field in ("kind", "source_ref", "field", "value")
                if field not in item
            ]
            if missing:
                raise CatalogValidationError(
                    f"missing fields in {label} in {path}: {', '.join(missing)}"
                )
            if item["kind"] not in EVIDENCE_KINDS:
                raise CatalogValidationError(
                    f"invalid knowledge kind in {label} in {path}: {item['kind']!r}"
                )
            self._validate_source_ref(item["source_ref"], path, label)

    def _validate_source_ref(
        self, source_ref: Any, path: Path, label: str
    ) -> None:
        if not isinstance(source_ref, dict):
            raise CatalogValidationError(f"{label} must be an object in {path}")

        manifest = source_ref.get("manifest")
        if not isinstance(manifest, str) or not SHA256_REF_RE.fullmatch(manifest):
            raise CatalogValidationError(
                f"{label}.manifest must be an immutable sha256 reference in {path}"
            )

        entry = source_ref.get("entry")
        if entry is not None and not isinstance(entry, str):
            raise CatalogValidationError(
                f"{label}.entry must be a string when present in {path}"
            )

        # Paths can be preserved evidence, but they are never accepted as identity.
        observed_path = source_ref.get("path")
        if observed_path is not None and not isinstance(observed_path, str):
            raise CatalogValidationError(
                f"{label}.path must be a string when present in {path}"
            )

    def _validate_references(self) -> None:
        for release in self._by_type["software_release"]:
            self._expect_reference(release, "software_id", "software")

        for occurrence in self._by_type["occurrence"]:
            self._expect_reference(occurrence, "artifact_id", "artifact")

        for identification in self._by_type["identification"]:
            target = "package" if "package_id" in identification else "artifact"
            self._expect_reference(identification, target + "_id", target)
            self._expect_reference(
                identification, "software_release_id", "software_release"
            )

        for package in self._by_type["package"]:
            for member in package["members"]:
                artifact = self._require_type(member["artifact_id"], "artifact")
                if artifact["size"] != member["size"]:
                    raise CatalogValidationError("package member size differs from artifact")

        for description in self._by_type["description"]:
            target_id = description.get("subject_id")
            target = self._records.get(target_id)
            if target is None:
                raise CatalogValidationError(
                    f"broken reference: {description['id']}.subject_id -> {target_id}"
                )
            if target["type"] not in {"software", "software_release"}:
                raise CatalogValidationError(
                    f"wrong reference type: {description['id']}.subject_id -> "
                    f"{target_id} is {target['type']}, expected software or software_release"
                )

    def _expect_reference(
        self, owner: dict[str, Any], field: str, expected_type: str
    ) -> None:
        target_id = owner.get(field)
        if not isinstance(target_id, str):
            raise CatalogValidationError(
                f"{owner['id']}.{field} must contain a catalog id"
            )

        target = self._records.get(target_id)
        if target is None:
            raise CatalogValidationError(
                f"broken reference: {owner['id']}.{field} -> {target_id}"
            )

        if target["type"] != expected_type:
            raise CatalogValidationError(
                f"wrong reference type: {owner['id']}.{field} -> {target_id} "
                f"is {target['type']}, expected {expected_type}"
            )

    def _require_type(self, record_id: str, expected_type: str) -> dict[str, Any]:
        record = self.record(record_id)
        if record["type"] != expected_type:
            raise CatalogError(
                f"catalog id {record_id!r} is {record['type']}, "
                f"expected {expected_type}"
            )
        return record
