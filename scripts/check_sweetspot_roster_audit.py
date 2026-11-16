#!/usr/bin/env python3
"""Check audit inventory completeness, not the truth of source interpretations."""

import argparse
import copy
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "a": {0, 21, 17, 3},
    "b": {1, 22, 2, 25},
    "c": {18, 26, 6, 20},
    "d": {19, 7, 16, 8},
    "e": {12, 23, 13, 24},
    "f": {9, 14, 5, 15},
    "g": {4, 10, 11},
}
STATUSES = {
    "existing_labels_reviewed",
    "excluded_with_evidence",
    "unresolved_source",
    "runtime_or_article_limited",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def key(row):
    require(type(row.get("character_id")) is int, "character_id must be an integer")
    require(type(row.get("action_id")) is int, "action_id must be an integer")
    return f"{row['character_id']}:{row['action_id']}"


def references(row, sources, group):
    refs = row["source_ids"]
    require(
        isinstance(refs, list) and all(ref in sources for ref in refs), f"group {group}: undefined source reference"
    )
    return refs


def validate(catalog, labels, reports):
    labeled_actions = {f"{r['character']}:{r['action']}" for r in labels}
    seen = set()
    unavailable = set()
    seen_groups = set()
    totals = Counter()
    characters = {}
    proposals = []
    source_count = 0
    source_failures = 0
    gaps = 0
    for report in reports:
        group = report.get("group")
        require(group in GROUPS and group not in seen_groups, f"unknown/duplicate group {group}")
        seen_groups.add(group)
        assigned = GROUPS[group]
        require(
            len(report["character_ids"]) == len(assigned) and set(report["character_ids"]) == assigned,
            f"group {group}: character ownership",
        )
        sources = {}
        for source in report["sources"]:
            identity = source["id"]
            require(
                isinstance(identity, str) and identity and identity not in sources,
                f"group {group}: duplicate/empty source",
            )
            require(source["url"].startswith("https://"), f"source {identity}: HTTPS URL required")
            require(type(source["retrieved"]) is bool, f"source {identity}: retrieval flag required")
            if source["retrieved"]:
                require(
                    re.fullmatch(r"[0-9a-f]{64}", source.get("sha256") or ""),
                    f"source {identity}: retrieved bytes need SHA-256",
                )
            else:
                source_failures += 1
            require(source.get("scope"), f"source {identity}: scope required")
            sources[identity] = source
        source_count += len(sources)

        for row in report["actions"]:
            identity = key(row)
            require(row["character_id"] in assigned, f"{identity}: wrong group")
            require(
                identity in catalog["actions"] and identity not in seen,
                f"{identity}: absent or duplicate catalog action",
            )
            seen.add(identity)
            status = row["status"]
            require(status in STATUSES, f"{identity}: unknown status")
            require(
                isinstance(row.get("reason"), str) and row["reason"].strip(),
                f"{identity}: action-specific rationale required",
            )
            refs = references(row, sources, group)
            if status in {"existing_labels_reviewed", "excluded_with_evidence"}:
                require(
                    refs and any(sources[ref]["retrieved"] for ref in refs),
                    f"{identity}: source-backed disposition needs retrieved evidence",
                )
            if status == "existing_labels_reviewed":
                require(identity in labeled_actions, f"{identity}: no existing labels")
            totals[status] += 1
            char = characters.setdefault(row["character_id"], Counter())
            char[status] += 1
            char["actions"] += 1
            char["labeled_actions"] += identity in labeled_actions
            phases = {
                (g["hitbox_id"], g["bone_id"], p["phase_id"]): p
                for g in catalog["actions"][identity]
                for p in g["phases"]
            }
            proposed = set()
            for proposal in row["proposals"]:
                signature = (proposal["hitbox_id"], proposal["bone_id"], proposal["phase_id"])
                require(
                    signature in phases and signature not in proposed,
                    f"{identity}: absent or duplicate proposal phase {signature}",
                )
                proposed.add(signature)
                require(
                    proposal["spot"] in {"sweet", "sour"} and proposal.get("label") and proposal.get("reason") and refs,
                    f"{identity}: proposal needs exact selection and rationale",
                )
                proposals.append({"action": identity, **proposal})
        for row in report["unavailable"]:
            identity = key(row)
            require(
                row["character_id"] in assigned
                and identity in catalog["unavailable"]
                and identity not in unavailable
                and row.get("reason"),
                f"{identity}: absent/duplicate/wrong-group unavailable action",
            )
            unavailable.add(identity)
        for gap in report["gaps"]:
            require(
                gap["character_id"] in assigned and gap.get("move") and gap.get("reason"), f"group {group}: invalid gap"
            )
            references(gap, sources, group)
            gaps += 1
    require(seen_groups == set(GROUPS), f"missing groups: {sorted(set(GROUPS) - seen_groups)}")
    require(seen == set(catalog["actions"]), f"unreviewed catalog actions: {sorted(set(catalog['actions']) - seen)}")
    require(
        unavailable == set(catalog["unavailable"]),
        f"unreviewed extraction failures: {sorted(set(catalog['unavailable']) - unavailable)}",
    )
    return {
        "catalog_actions": len(seen),
        "character_contexts": len(characters),
        "unavailable_actions": len(unavailable),
        "dispositions": dict(sorted(totals.items())),
        "characters": {str(c): dict(sorted(counts.items())) for c, counts in sorted(characters.items())},
        "sources": source_count,
        "failed_retrievals": source_failures,
        "recorded_gaps": gaps,
        "proposed_labels": proposals,
        "meaning": "Complete inventory accounting; not complete source, runtime or collision certification.",
    }


def negative_controls(catalog, labels, reports):
    controls = []
    missing = copy.deepcopy(reports)
    missing[0]["actions"].pop()
    controls.append(missing)
    duplicate = copy.deepcopy(reports)
    duplicate[0]["actions"].append(copy.deepcopy(duplicate[0]["actions"][0]))
    controls.append(duplicate)
    invalid_status = copy.deepcopy(reports)
    invalid_status[0]["actions"][0]["status"] = "complete"
    controls.append(invalid_status)
    invalid_source = copy.deepcopy(reports)
    invalid_source[0]["actions"][0]["source_ids"] = ["nonexistent-source"]
    controls.append(invalid_source)
    invalid_proposal = copy.deepcopy(reports)
    invalid_proposal[0]["actions"][0]["proposals"] = [
        {
            "hitbox_id": -1,
            "bone_id": -1,
            "phase_id": "absent",
            "spot": "sweet",
            "label": "invalid",
            "reason": "negative control",
        }
    ]
    controls.append(invalid_proposal)
    missing_unavailable = copy.deepcopy(reports)
    next(r for r in missing_unavailable if r["unavailable"])["unavailable"].pop()
    controls.append(missing_unavailable)
    for index, changed in enumerate(controls):
        try:
            validate(catalog, labels, changed)
        except ValueError:
            continue
        raise AssertionError(f"negative control {index} unexpectedly passed")
    return len(controls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=ROOT / "docs/sweetspot-roster-audit")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    catalog_path = ROOT / "melee/hitbox_catalog.json"
    labels_path = ROOT / "melee/hitbox_phase_labels.csv"
    catalog = json.loads(catalog_path.read_text())
    with labels_path.open(newline="") as source:
        labels = list(csv.DictReader(source))
    reports = [json.loads(p.read_text()) for p in sorted(args.reports.glob("group-*.json"))]
    summary = validate(catalog, labels, reports)
    summary["catalog_sha256"] = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    summary["labels_sha256"] = hashlib.sha256(labels_path.read_bytes()).hexdigest()
    if args.self_test:
        summary["negative_controls_passed"] = negative_controls(catalog, labels, reports)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError) as error:
        print(f"audit inventory rejected: {error}", file=sys.stderr)
        raise SystemExit(1) from error
