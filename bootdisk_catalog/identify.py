"""Create explicit catalog interpretations from already-preserved observations.

This module deliberately does not infer software identity from filenames, titles,
or hashes. A curator supplies the semantic identity and points the interpretation
back to an existing Artifact occurrence as evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .catalog import Catalog, CatalogError, SCHEMA


class IdentificationError(Exception):
    """Raised when an explicit catalog identification cannot be written safely."""


def _safe_filename(record_id: str) -> str:
    # Filenames are organizational only; stable catalog identity stays inside JSON.
    return re.sub(r"[^A-Za-z0-9._-]+", "_", record_id) + ".json"


def _identification_id(artifact_id: str, release_id: str) -> str:
    # The relationship itself is stable even if supporting evidence is enriched later.
    digest = hashlib.sha256(f"{artifact_id}\n{release_id}".encode("utf-8")).hexdigest()
    return f"identification:{digest}"


def _select_occurrence(
    catalog: Catalog, artifact_id: str, entry: str, manifest_path=None
) -> dict[str, Any]:
    try:
        artifact = catalog.record(artifact_id)
    except CatalogError as exc:
        raise IdentificationError(str(exc)) from exc

    if artifact["type"] == "package":
        if manifest_path is None:
            raise IdentificationError("package identification requires its ingest manifest")
        from .import_ingest import _read_manifest, _find_entry
        manifest, digest = _read_manifest(Path(manifest_path))
        source = _find_entry(manifest, entry)
        identity = source.get("content_identity", {})
        if artifact_id != "package:sha256:" + str(identity.get("manifest_sha256")):
            raise IdentificationError("package does not belong to the requested source entry")
        return {"source_ref": {"manifest": "sha256:" + digest, "entry": entry}}

    if artifact["type"] != "artifact":
        raise IdentificationError(f"catalog id is not an artifact: {artifact_id}")

    matches = [
        occurrence
        for occurrence in catalog.occurrences_for_artifact(artifact_id)
        if occurrence["source_ref"].get("entry") == entry
    ]
    if not matches:
        raise IdentificationError(
            f"no occurrence for artifact {artifact_id} in entry {entry}"
        )
    if len(matches) > 1:
        raise IdentificationError(
            f"multiple occurrences for artifact {artifact_id} in entry {entry}; "
            "the evidence source is ambiguous"
        )
    return matches[0]


def _record_path(root: Path, record: dict[str, Any]) -> Path:
    directories = {
        "software": "software",
        "software_release": "releases",
        "identification": "identifications",
        "description": "descriptions",
    }
    return root / directories[record["type"]] / _safe_filename(record["id"])


def _canonical_json(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, ensure_ascii=False) + "\n"


def _preflight_record(path: Path, record: dict[str, Any]) -> None:
    if not path.exists():
        return
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentificationError(
            f"cannot inspect existing catalog record {path}: {exc}"
        ) from exc
    if existing != record:
        raise IdentificationError(
            f"refusing to overwrite conflicting catalog record: {path}"
        )


def create_identification(
    catalog_root: str | Path,
    *,
    artifact_id: str,
    entry: str,
    software_id: str,
    software_name: str,
    release_id: str,
    version: str,
    evidence_field: str,
    evidence_value: str,
    status: str = "curated",
    manifest_path: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Write Software, SoftwareRelease and Identification records explicitly.

    The existing Occurrence supplies the immutable manifest+entry evidence source.
    Its filesystem path is intentionally omitted because the supplied evidence field
    describes the editorial entry, not necessarily the referenced file itself.
    """

    if status not in {"interpreted", "curated"}:
        raise IdentificationError(f"invalid identification status: {status!r}")

    root = Path(catalog_root)
    catalog = Catalog.load(root)
    occurrence = _select_occurrence(catalog, artifact_id, entry, manifest_path)

    occurrence_source = occurrence["source_ref"]
    source_ref = {
        "manifest": occurrence_source["manifest"],
        "entry": occurrence_source["entry"],
    }

    software = {
        "schema": SCHEMA,
        "type": "software",
        "id": software_id,
        "name": software_name,
    }
    release = {
        "schema": SCHEMA,
        "type": "software_release",
        "id": release_id,
        "software_id": software_id,
        "version": version,
    }
    identification = {
        "schema": SCHEMA,
        "type": "identification",
        "id": _identification_id(artifact_id, release_id),
        ("package_id" if catalog.record(artifact_id)["type"] == "package" else "artifact_id"): artifact_id,
        "software_release_id": release_id,
        "status": status,
        "evidence": [
            {
                # The source field is observed evidence. The semantic conclusion
                # drawn from it is represented separately by Identification.status.
                "kind": "observed",
                "source_ref": source_ref,
                "field": evidence_field,
                "value": evidence_value,
            }
        ],
    }

    records = (software, release, identification)
    paths = tuple(_record_path(root, record) for record in records)

    # Check every destination before writing anything so conflicts cannot leave a
    # half-written semantic relationship behind.
    for path, record in zip(paths, records):
        _preflight_record(path, record)

    for path, record in zip(paths, records):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_canonical_json(record), encoding="utf-8")

    # Reload the complete graph so broken IDs or references fail before success.
    Catalog.load(root)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add an explicit evidence-based software identification"
    )
    parser.add_argument("catalog_root")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--artifact", dest="artifact_id")
    target.add_argument("--package", dest="artifact_id")
    parser.add_argument("--manifest", dest="manifest_path", type=Path)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--software-id", required=True)
    parser.add_argument("--software-name", required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--field", required=True, dest="evidence_field")
    parser.add_argument("--value", required=True, dest="evidence_value")
    parser.add_argument(
        "--status", choices=("interpreted", "curated"), default="curated"
    )
    args = parser.parse_args(argv)

    software, release, identification = create_identification(
        args.catalog_root,
        artifact_id=args.artifact_id,
        entry=args.entry,
        software_id=args.software_id,
        software_name=args.software_name,
        release_id=args.release_id,
        version=args.version,
        evidence_field=args.evidence_field,
        evidence_value=args.evidence_value,
        status=args.status,
        manifest_path=args.manifest_path,
    )
    print(software["id"])
    print(release["id"])
    print(identification["id"])
    return 0




def apply_review_claims(records, entry):
    """Build and validate a complete candidate graph without performing writes.

    Used by the transactional review workspace; legacy CLI remains append-only.
    IDs are resolved here, never by the frontend. Ambiguous shared edits fail.
    """
    from copy import deepcopy
    from .catalog import LoadedRecord

    result = {r['id']: deepcopy(r) for r in records}
    claims = deepcopy(entry['draft']['claims'])
    target = entry['source']['target']
    target_field = target['kind'] + '_id'
    matches = [r for r in result.values() if r['type'] == 'identification' and r.get(target_field) == target['id']]
    if len(matches) != 1:
        raise ValueError('Målet har flere eller ingen identitetstolkninger; krever egen gjennomgang.')
    old = matches[0]
    old_release = result[old['software_release_id']]
    old_software = result[old_release['software_id']]
    identity = claims['identity']['value']
    software_id = identity['software_id']
    if software_id is None:
        # Reuse the existing identity for an unchanged name; new names get stable IDs.
        software_id = old_software['id'] if identity['name'] == old_software['name'] else 'software:review-' + hashlib.sha256(identity['name'].encode()).hexdigest()
    if identity['software_id'] is not None and software_id != old_software['id']:
        raise ValueError('Bytte til en annen eksisterende identitet krever egen gjennomgang.')
    software = deepcopy(result.get(software_id, dict(schema=SCHEMA, type='software', id=software_id, name=identity['name'])))
    if software['name'] != identity['name']:
        raise ValueError('Navnet samsvarer ikke med identiteten. Send en ny navnetolkning uten ID.')
    if claims['content_kind']['assessment'] == 'accepted':
        software['content_kind'] = claims['content_kind']['value']
    shared = [r for r in result.values() if r['type'] == 'identification' and r['id'] != old['id']
              and result[r['software_release_id']]['software_id'] == software_id]
    if shared and software != result.get(software_id):
        raise ValueError('Endringen ville påvirke andre kildeposter med samme programidentitet.')
    if any(e['source_ref'].get('manifest') != entry['key']['manifest'] or e['source_ref'].get('entry') != entry['key']['entry'] for e in old['evidence']):
        raise ValueError('Identiteten er delt mellom kildeposter og må gjennomgås separat.')
    identity['software_id'] = software_id
    version = claims['version']['value'] if claims['version']['assessment'] == 'accepted' else 'unknown'
    release_id = old_release['id'] if software_id == old_software['id'] and version == old_release['version'] else 'release:review-' + hashlib.sha256((software_id + '\n' + version).encode()).hexdigest()
    release = dict(schema=SCHEMA, type='software_release', id=release_id, software_id=software_id, version=version)
    if release_id in result and result[release_id] != release:
        raise ValueError('Utgivelsen har eksisterende metadata som krever egen gjennomgang.')
    evidence = []
    # Preserve previous observations as well as every explicitly selected source.
    for e in old['evidence']:
        if e not in evidence: evidence.append(deepcopy(e))
    selected = {i for c in claims.values() for i in c['evidence_ids']}
    for e in entry['evidence']:
        if e['id'] in selected:
            item = dict(kind='observed', source_ref=e['source_ref'], field=e['field'], value=e['observation'])
            if item not in evidence: evidence.append(item)
    ident = deepcopy(old)
    ident.update(id=_identification_id(target['id'], release_id), software_release_id=release_id,
                 status='curated' if claims['identity']['assessment'] == 'accepted' else 'interpreted', evidence=evidence,
                 distribution_kind=claims['distribution_kind']['value'] if claims['distribution_kind']['assessment'] == 'accepted' else 'unknown')
    prose = claims['description']
    descriptions = [r for r in result.values() if r['type'] == 'description' and r['subject_id'] == release_id and r['language'] == 'nb-NO']
    if len(descriptions) > 1:
        raise ValueError('Flere beskrivelser krever separat gjennomgang.')
    description = dict(schema=SCHEMA, type='description',
                       id=descriptions[0]['id'] if descriptions else 'description:review-' + hashlib.sha256((release_id + '\nnb-NO').encode()).hexdigest(),
                       subject_id=release_id, language='nb-NO', text=prose['value']['text'],
                       status='curated' if prose['assessment'] == 'accepted' else 'draft', evidence=deepcopy(evidence))
    if descriptions:
        for e in descriptions[0]['evidence']:
            if e not in description['evidence']: description['evidence'].append(deepcopy(e))
    if descriptions and descriptions[0] != description and any(r['software_release_id'] == release_id for r in shared):
        raise ValueError('Beskrivelsen er delt med andre kildeposter.')
    del result[old['id']]
    for r in (software, release, ident, description):
        result[r['id']] = r
    ordered = sorted(result.values(), key=lambda r: r['id'])
    Catalog(LoadedRecord(r, Path('<review-candidate>')) for r in ordered)
    return ordered, claims


if __name__ == "__main__":
    raise SystemExit(main())
