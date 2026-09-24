"""Reproducible, read-only routing of pristine Director intake observations.

This module never imports ReviewWorkspace or a semantic writer. Suggestions are
not decisions. Machine work must finish before a human exception can be asserted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from .catalog import CatalogError
from .import_ingest import IngestImportError
from .intake import build_candidates, _json, _require, _tree_bytes

SCHEMA = "bootdisk-automation-queue-1"
RULES_VERSION = "director-first-pass-1"
STATUSES = ("candidate", "retain_unknown", "inspect", "conflict", "preserve")
STAGES = ("proposals", "inspecting", "needs_review", "protected")


def _evidence(label, observation):
    return {"label": label, "value": observation["value"], "source_ref": observation["source_ref"]}


def first_pass(manifest_raw: bytes, candidates_raw: bytes):
    """Validate both immutable inputs, then derive a deterministic queue.

    Candidate documents must match their source projection exactly. In particular,
    edited claims, human decisions and stale source references cannot enter this
    route. Unknown fields are retained, but inspection is separately queued.
    """
    expected = build_candidates(manifest_raw)
    try:
        supplied = json.loads(candidates_raw)
    except (ValueError, UnicodeError) as exc:
        raise IngestImportError("invalid candidates JSON") from exc
    _require(supplied == expected, "candidate snapshot differs from its manifest; refusing edited or decided input")
    rows = []
    for c in expected["candidates"]:
        obs = c["observations"]
        title = _evidence("Navn i CD-menyen", obs["title"])
        groups = _evidence("Kategori i CD-menyen", obs["menu_groups"])
        issue = _evidence("Registrerte kildeavvik", c["source_issues"])
        issues = c["source_issues"]["value"]
        missing = [_evidence("Manglende startfil", ref) for ref in c["missing_references"]]
        blocked = bool(issues or missing)
        fields, tasks = [], []

        def field(name, status, rule, reason, proposed=None, evidence=()):
            fields.append({"field": name, "status": status, "proposed": proposed,
                           "rule": rule, "reason": reason, "evidence": list(evidence)})

        def task(code, name, reason, evidence=()):
            tasks.append({"code": code, "field": name, "reason": reason, "evidence": list(evidence)})

        field("identity", "conflict" if blocked else "inspect", "identity-needs-package-context-1",
              "Kildeavvik må undersøkes før programidentitet fastslås." if blocked else
              "Menynavn og identiske installasjonsfiler fastslår ikke programidentitet.",
              evidence=[title, issue, *missing] if blocked else [title])
        if issues:
            task("resolve_source_issues", "identity", "Undersøk kildeavvik maskinelt før en person blir bedt om å vurdere dem.", [issue])
        if missing:
            task("resolve_missing_files", "identity", "Kontroller manglende startfiler før programtilknytning foreslås.", missing)
        task("inspect_product_context", "identity", "Undersøk programspesifikk README og installasjonsmetadata uten å kjøre programmet.", [title])
        field("version", "retain_unknown", "version-not-established-1",
              "Versjon er ikke fastslått. Tall i navn og en felles installatør er ikke tilstrekkelig belegg.", evidence=[title])
        task("inspect_product_version", "version", "Let etter versjon med dokumentert tilknytning til programmet, ikke bare installatøren.", [title])
        # The Director parser's games group identifies the menu section. Broad
        # programs/school groups cannot safely become application/course claims.
        if obs["menu_groups"]["value"] == ["games"] and not blocked:
            field("content_kind", "candidate", "director-games-section-1",
                  "Den entydige spillseksjonen støtter et forslag om innholdstype Spill; det er ikke en godkjenning.",
                  "game", [groups])
        else:
            field("content_kind", "inspect", "category-needs-context-1",
                  "Kategorien er bred, blandet eller har kildeavvik; innholdstypen må undersøkes.", evidence=[groups])
            task("inspect_content_kind", "content_kind", "Undersøk hva oppføringen inneholder før en innholdstype foreslås.", [groups])
        field("distribution_kind", "retain_unknown", "edition-not-established-1",
              "Utgaven er ikke fastslått. Freeware betyr ikke fullversjon, og en omtale av en demo kan gjelde et annet program.")
        task("inspect_edition", "distribution_kind", "Let etter eksplisitt demo/prøve/full-utgave i riktig programkontekst.")
        description = obs["description"]
        if description is not None and description["value"].strip() and not blocked:
            field("description", "candidate", "original-description-1", "Bevar den valgte CD-omtalen ordrett, inkludert linjeskift.",
                  description["value"], [_evidence("Omtale på CD-en", description)])
        else:
            evidence = ([_evidence("Omtale på CD-en", description)] if description is not None else [])
            if issues:
                evidence.append(issue)
            evidence.extend(missing)
            field("description", "conflict" if blocked else "retain_unknown", "description-needs-source-check-1",
                  "Kildeavvik må avklares før omtalen foreslås." if blocked else "Ingen entydig, ikke-tom originalomtale er valgt.", evidence=evidence)
            task("inspect_description", "description", "Undersøk originalkilden uten å skrive en erstatningsomtale.", evidence)
        rows.append({"key": c["key"], "title": obs["title"]["value"],
                     "stage": "inspecting" if tasks else "proposals", "requires_human": False,
                     "fields": fields, "tasks": tasks})
    counts = Counter(f["status"] for r in rows for f in r["fields"])
    stages = Counter(r["stage"] for r in rows)
    return {"schema": SCHEMA, "rules_version": RULES_VERSION, "mode": "read_only",
            "input": {"manifest": expected["manifest"], "candidates_sha256": hashlib.sha256(candidates_raw).hexdigest()},
            "entries": rows, "summary": {"entries": len(rows),
                "field_status_counts": {s: counts[s] for s in STATUSES},
                "stage_counts": {s: stages[s] for s in STAGES},
                "machine_tasks": sum(len(r["tasks"]) for r in rows),
                "human_exceptions": 0, "automatic_decisions": 0, "human_decisions": 0}}


def render_report(document):
    summary = document["summary"]
    lines = ["# Automatisk førstegjennomgang", "",
             f"{summary['entries']} oppføringer; {summary['field_status_counts']['candidate']} feltforslag; "
             f"{summary['machine_tasks']} maskinoppgaver.", "",
             "Ingen godkjenninger er skrevet. Menneskelig arbeidsmengde er ennå ikke fastslått: "
             "maskinoppgavene er planlagt, ikke utført. Null menneskeoppgaver betyr ikke at kurateringen er ferdig.", ""]
    for row in document["entries"]:
        # Indented source text cannot become Markdown links, HTML or instructions.
        lines += ["## Kildepost", "", "    " + row["key"]["entry"]]
        lines += ["    " + line for line in row["title"].splitlines()]
        for f in row["fields"]:
            lines += ["", f"- {f['field']}: {f['status']} — {f['reason']}"]
            if f["proposed"] is not None:
                lines += ["", *["    " + line for line in str(f["proposed"]).splitlines()]]
        lines += [""]
    return "\n".join(lines) + "\n"


def prepare_first_pass(intake, output):
    intake, output = Path(intake).absolute(), Path(output).absolute()
    _require(not output.resolve().is_relative_to(intake.resolve()), "output must be outside the intake")
    snapshot = _tree_bytes(intake)
    _require("manifest.json" in snapshot and "candidates.json" in snapshot, "intake needs manifest.json and candidates.json")
    result = first_pass(snapshot["manifest.json"], snapshot["candidates.json"])
    _require(output.parent.is_dir(), "output parent must already exist")
    lock_path = output.parent / ("." + output.name + ".first-pass.lock")
    # Refuse symlinks, including at the lock boundary. No source or workspace path
    # is a write target; existing results are compared, never overwritten.
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        staging = Path(tempfile.mkdtemp(prefix=".first-pass-", dir=output.parent))
        try:
            (staging / "queue.json").write_text(_json(result), encoding="utf-8")
            (staging / "rapport.md").write_text(render_report(result), encoding="utf-8")
            if output.exists() or output.is_symlink():
                _require(_tree_bytes(output) == _tree_bytes(staging), "refusing to replace existing or edited output; choose a new directory")
            else:
                os.rename(staging, output)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate read-only field suggestions and machine work from a pristine Director intake")
    parser.add_argument("intake", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare_first_pass(args.intake, args.output)
    except (CatalogError, OSError) as exc:
        parser.exit(2, f"first pass failed: {exc}\n")
    print(_json(result["summary"]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
