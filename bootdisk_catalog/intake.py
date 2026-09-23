"""Stage unapproved Director candidates without bootstrapping semantic claims.

The intake is an immutable, reproducible observation snapshot, deliberately
separate from Catalog records and ReviewWorkspace drafts/decisions.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .catalog import CatalogError, SHA256_RE
from .import_ingest import IngestImportError, _iter_observations, import_manifest

SCHEMA = "bootdisk-candidate-intake-1"
RULE_VERSION = "director-observations-1"
DIRECTOR_SCHEMA = "kcd-director-experimental-1"
LAUNCH_SCOPE = "resolved literal launch files only, not software package"
SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


def _require(condition, message):
    if not condition:
        raise IngestImportError(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def build_candidates(raw: bytes):
    """Pure observation projection; identical bytes produce identical output.

    No filesystem/media access, inferred identities, model calls or decisions.
    Exact original bytes are supplied by the intake, including all source texts.
    """
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise IngestImportError("invalid ingest JSON") from exc
    _require(isinstance(manifest, dict) and manifest.get("schema_version") == DIRECTOR_SCHEMA,
             "candidate intake currently supports only kcd-director-experimental-1")
    _require(isinstance(manifest.get("entries"), list) and manifest["entries"], "entries must be non-empty")
    _require(isinstance(manifest.get("file_inventory"), list), "file_inventory must be an array")
    inventory = {}
    for item in manifest["file_inventory"]:
        _require(isinstance(item, dict), "invalid inventory item")
        path, digest, size = item.get("path"), item.get("sha256"), item.get("size")
        _require(isinstance(path, str) and bool(path) and path not in inventory, "invalid/duplicate inventory path")
        _require(isinstance(digest, str) and SHA256_RE.fullmatch(digest), "invalid inventory hash")
        _require(isinstance(size, int) and not isinstance(size, bool) and size >= 0, "invalid inventory size")
        inventory[path] = item
    # Validate source IDs/roles before the legacy importer uses them as filenames.
    for entry in manifest["entries"]:
        _require(isinstance(entry, dict), "invalid entry")
        source_id = entry.get("source_id")
        _require(isinstance(source_id, str) and SAFE_COMPONENT.fullmatch(source_id), "unsafe source_id")
        files = entry.get("files")
        _require(isinstance(files, dict), "missing files object")
        for section in ("referenced", "discovered"):
            _require(isinstance(files.get(section, {}), dict), "invalid file section")
            for role in files.get(section, {}):
                _require(SAFE_COMPONENT.fullmatch(role), "unsafe observation role")
    observations = list(_iter_observations(manifest))
    for _, _, observation in observations:
        item = inventory.get(observation["path"])
        _require(item is not None and all(item.get(k) == observation[k] for k in ("sha256", "size")),
                 "file observation disagrees with inventory")
    manifest_ref = "sha256:" + hashlib.sha256(raw).hexdigest()
    candidates = []
    for index, entry in enumerate(manifest["entries"]):
        source_id = entry["source_id"]
        _require(isinstance(entry.get("interpretations"), dict) and
                 entry["interpretations"].get("content_identity_scope") == LAUNCH_SCOPE,
                 "missing/unsupported Director content scope")
        normalized, evidence = entry.get("normalized"), entry.get("evidence")
        _require(isinstance(normalized, dict) and isinstance(evidence, dict), "missing source observations")
        title, categories = normalized.get("title"), normalized.get("categories")
        _require(isinstance(title, str) and bool(title.strip()), "missing source title")
        _require(isinstance(categories, list) and all(isinstance(c, str) for c in categories), "invalid menu groups")
        issues = entry.get("issues")
        _require(isinstance(issues, list) and all(isinstance(i, str) for i in issues), "invalid source issues")
        refs = entry["files"].get("inventory_refs")
        _require(isinstance(refs, list) and all(isinstance(p, str) and p in inventory for p in refs)
                 and len(refs) == len(set(refs)), "invalid launch inventory references")
        observed_paths = {o["path"] for sid, _, o in observations if sid == source_id}
        _require(set(refs) == observed_paths, "launch references disagree with explicit observations")

        def observation(value, field):
            return {"value": value, "source_ref": {"manifest": manifest_ref, "entry": source_id,
                    "pointer": f"/entries/{index}/{field}"}}

        description_source = evidence.get("description_source")
        description = None
        if description_source is not None:
            _require(isinstance(description_source, dict) and isinstance(description_source.get("text"), dict),
                     "invalid selected description source")
            text = description_source["text"].get("cp1252_view")
            _require(isinstance(text, str), "selected description has no readable text")
            # Preserve original whitespace/line breaks; never copy normalized prose
            # or infer a language from the CD label.
            description = observation(text, "evidence/description_source/text/cp1252_view")
        missing = []
        for section in ("referenced", "discovered"):
            for role, file in entry["files"].get(section, {}).items():
                if file.get("exists") is False:
                    missing.append(observation(file.get("path"), f"files/{section}/{role}/path"))
        candidates.append({
            "key": {"manifest": manifest_ref, "entry": source_id},
            "state": "candidate", "decision": None,
            "observations": {"title": observation(title, "normalized/title"),
                             "menu_groups": observation(categories, "normalized/categories"),
                             "description": description},
            "preservation": {"scope": "launch_files_only", "package_id": None,
                             "files": [{"path": p, "sha256": inventory[p]["sha256"],
                                        "size": inventory[p]["size"]} for p in refs]},
            "source_issues": observation(issues, "issues"),
            "missing_references": missing,
            "inspection_reasons": (["source_issue"] if issues else []) +
                                  (["description_not_selected"] if description is None else []) +
                                  ["identity_not_established", "version_not_inspected", "distribution_not_inspected"],
            "claims": {"identity": None, "version": None, "content_kind": None,
                       "distribution_kind": None, "description_language": None},
        })
    return {"schema": SCHEMA, "rule_version": RULE_VERSION, "manifest": manifest_ref,
            "mode": "observations_only", "candidates": candidates,
            "summary": {"candidates": len(candidates),
                        "with_source_issues": sum(bool(c["source_issues"]["value"]) for c in candidates),
                        "with_selected_description": sum(c["observations"]["description"] is not None for c in candidates),
                        "automatic_decisions": 0, "human_decisions": 0}}


def render_report(document):
    def label(value):
        # Source strings are data, including when rendered as Markdown headings.
        return re.sub(r"([\\`*_{}\[\]()<>#+.!|])", r"\\\1", " ".join(value.split()))

    issue_labels = {"conflicting_launch_targets": "Menyknappene peker til forskjellige filer",
                    "missing_launch_file": "En referert startfil mangler",
                    "unresolved_direct_launch": "Direkte menyhandling er uavklart",
                    "unresolved_warning_continue_launch": "Fortsett-knappen er uavklart"}
    summary = document["summary"]
    lines = ["# Kandidatmottak", "", f"{summary['candidates']} uidentifiserte kandidater mottatt.",
             f"{summary['with_selected_description']} har valgt omtale fra CD-en; "
             f"{summary['with_source_issues']} har kildeavvik.", "",
             "Dette er observasjoner til videre maskinell undersøkelse, ikke en liste over "
             "manuelle godkjenninger. Ingen identiteter eller felt er godkjent.", "",
             "Bare startfilreferanser er registrert; de utgjør ikke komplette programpakker. "
             "Menygruppe er ikke lik innholdstype. Språk, versjon og distribusjon er ikke fastslått.", ""]
    for candidate in document["candidates"]:
        obs = candidate["observations"]
        lines += [f"## {candidate['key']['entry']}: {label(obs['title']['value'])}", "",
                  "Menygruppe fra innleser: " + ", ".join(label(v) for v in obs["menu_groups"]["value"]), "",
                  "Omtale valgt fra CD-en:", ""]
        description = obs["description"]
        # Indented blocks keep original source markup inert in the human report.
        lines += ["    " + line for line in (description["value"] if description else
                  "Ingen entydig omtale valgt av innleseren.").splitlines()]
        lines += ["", "Startfiler:", ""] + ["    " + f["path"] for f in candidate["preservation"]["files"]]
        lines += ["", "Kildeavvik: " + ("; ".join(label(issue_labels.get(i, i)) for i in
                  candidate["source_issues"]["value"]) or "Ingen registrert."), ""]
        if candidate["missing_references"]:
            lines += ["Manglende filreferanser:", ""]
            lines += ["    " + str(f["value"]) for f in candidate["missing_references"]] + [""]
    return "\n".join(lines)


def _tree_bytes(root):
    _require(root.is_dir() and not root.is_symlink(), "intake destination must be a real directory")
    result = {}
    for path in root.rglob("*"):
        _require(not path.is_symlink(), "intake contains a symlink")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
        else:
            _require(path.is_dir(), "intake contains a special file")
    return result


def prepare_intake(manifest_path, output):
    """Build and validate in isolation, then atomically publish a new intake.

    An exact retry is a no-op; changed/edited destinations are never overwritten.
    This API never opens ReviewWorkspace or writes to the original catalog.
    """
    raw = Path(manifest_path).read_bytes()
    document = build_candidates(raw)
    output = Path(output).absolute()
    _require(output.parent.is_dir(), "output parent must already exist")
    # All intake writers serialize the existence check and publication.
    lock_path = output.parent / ("." + output.name + ".intake.lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        staging = Path(tempfile.mkdtemp(prefix=".intake-", dir=output.parent))
        try:
            (staging / "manifest.json").write_bytes(raw)
            (staging / "catalog").mkdir()
            import_manifest(staging / "manifest.json", staging / "catalog")
            (staging / "candidates.json").write_text(_json(document), encoding="utf-8")
            (staging / "rapport.md").write_text(render_report(document), encoding="utf-8")
            if output.exists() or output.is_symlink():
                _require(_tree_bytes(output) == _tree_bytes(staging),
                         "refusing to replace an existing or edited intake; choose a new output")
            else:
                os.rename(staging, output)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description="Receive unapproved Director candidates in an isolated intake")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare_intake(args.manifest, args.output)
    except (CatalogError, OSError) as exc:
        parser.exit(2, f"candidate intake failed: {exc}\n")
    print(_json(result["summary"]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
