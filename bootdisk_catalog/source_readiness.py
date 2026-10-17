"""Source catalog readiness is independent of installed software identification.

This deterministic projection creates no semantic identities or human approvals.
Missing versions and editions never create review work. File association problems
remain explicit even when the CD's title and prose can be catalogued.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from .catalog import CatalogError
from .file_association import explain_references
from .completed_investigations import completed_investigation

RULE = "source-catalog-readiness-4"
KNOWN_ISSUES = {
    "conflicting_launch_targets", "missing_launch_file",
    "missing_auxiliary_launch_file", "unresolved_warning_continue_launch",
    "shared_warning_control_not_runtime_tested",
}


def _decoded(observation):
    if not isinstance(observation, dict):
        return None
    try:
        text = base64.b64decode(observation["base64"], validate=True).decode("cp1252")
    except (KeyError, ValueError, UnicodeError, TypeError):
        return None
    return text if text == observation.get("cp1252_view") else None


def title_evidence(manifest, entry):
    """Bind the title to a source field, not to an invented program identity."""
    title = entry.get("normalized", {}).get("title")
    if not isinstance(title, str) or not title.strip() or any(ord(c) < 32 for c in title):
        return None
    evidence = entry.get("evidence", {})
    if manifest.get("schema_version") == "kcd-director-experimental-1":
        selection = evidence.get("selection", {})
        choices = [("evidence/title/text", evidence.get("title", {}).get("text"), False),
                   ("evidence/selection/title", selection.get("title"), False),
                   ("evidence/selection/text", selection.get("text"), True)]
        for pointer, value, first_line in choices:
            text = _decoded(value)
            selected = text.splitlines()[0] if first_line and text else text
            if selected is not None and " ".join(selected.split()) == title:
                return {"field": pointer, "value": title, "original": text}
        return None
    if manifest.get("schema_version") != "0.9":
        return None
    raw = entry.get("raw", {})
    if any(k.casefold() == 'titelno' and isinstance(v, str) and v.strip() for k, v in raw.items()):
        from .localized_source import localized_title
        return localized_title(manifest, entry)
    if "calendar_metadata" in evidence:
        from .calendar_source import validate_calendar
        if validate_calendar(manifest, entry):
            return {"field": "raw/Titel", "value": title, "original": raw["Titel"]}
    if "description_tools" in evidence:
        # source_context validates preserved bytes, hash, section and raw fields.
        field, section = "Navn", raw
    elif evidence.get("metadata_section") == "Generelt":
        field, section = "Speciel", manifest.get("source", {}).get("sections", {}).get("Generelt", {})
    else:
        field = "Titel"
        section = manifest.get("source", {}).get("sections", {}).get(entry["source_id"], {})
    if raw.get(field) == section.get(field) == title:
        return {"field": "raw/" + field, "value": title}
    return None


def assess_manifest(manifest_path):
    """Validate source context and derive independent catalog/file work queues."""
    # Lazy import avoids a cycle when presentation_projection calls this module.
    from .presentation import source_context
    path = Path(manifest_path)
    raw = path.read_bytes()
    manifest = json.loads(raw)
    ref = "sha256:" + hashlib.sha256(raw).hexdigest()
    contexts = source_context(path)
    if len({e["source_id"] for e in manifest["entries"]}) != len(manifest["entries"]):
        raise CatalogError("duplicate source entry")
    result = {}
    for position, entry in enumerate(manifest["entries"]):
        key = {"manifest": ref, "entry": entry["source_id"]}
        title = title_evidence(manifest, entry)
        issues = entry.get("issues", [])
        unknown = sorted(set(issues) - KNOWN_ISSUES)
        references = entry.get("files", {}).get("referenced", {})
        missing = [r.get("path") for r in references.values() if r.get("exists") is False]
        if "conflicting_launch_targets" in issues:
            association = "conflict"
        elif "unresolved_warning_continue_launch" in issues or unknown:
            association = "needs_inspection"
        elif missing or "missing_launch_file" in issues:
            association = "missing"
        elif "shared_warning_control_not_runtime_tested" in issues:
            association = "not_runtime_tested"
        elif references:
            association = "observed"
        else:
            association = "not_applicable_or_unrecorded"
        explanation = explain_references(entry)
        completion = completed_investigation(ref, entry["source_id"])
        if completion and not unknown:
            explanation = completion
        if explanation:
            association = "observed"
        # Technical exceptions go to machine inspection first. A human queue
        # must contain a concrete unanswered question, not every unknown field.
        tasks = []
        if not title:
            tasks.append("inspect_source_title")
        if association in ("conflict", "needs_inspection"):
            tasks.append("inspect_file_association")
        if unknown:
            tasks.append("inspect_unknown_source_issue")
        result[entry["source_id"]] = {
            "rule": RULE, "key": key,
            "status": "documented" if title and not unknown else "needs_inspection",
            "title": ({"value": title["value"], "source_ref": {
                **key, "pointer": f"/entries/{position}/" + title["field"]},
                "original": title.get("original", title["value"]),
                "normalization": "whitespace; workshop shelf uses first line"} if title else None),
            "description": contexts[entry["source_id"]].get("description"),
            "file_association": {"status": association, "issues": issues, "missing": missing,
                                 "explanation": explanation,
                                 "runtime_verified": False},
            "machine_tasks": tasks,
            "human_questions": [],
            "scope": "CD source entry only; no installed-product, version or edition claim",
        }
    if path.read_bytes() != raw:
        raise CatalogError("source manifest changed during assessment")
    return result


def main(argv=None):
    import argparse
    from collections import Counter
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    rows = list(assess_manifest(args.manifest).values())
    result = {"schema": "bootdisk-source-readiness-1", "rule": RULE, "entries": rows,
              "summary": {"entries": len(rows),
                          "source_status": dict(Counter(r["status"] for r in rows)),
                          "file_association": dict(Counter(r["file_association"]["status"] for r in rows)),
                          "machine_inspection_entries": sum(bool(r["machine_tasks"]) for r in rows),
                          "human_questions": sum(len(r["human_questions"]) for r in rows)}}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
