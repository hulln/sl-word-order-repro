#!/usr/bin/env python3
"""Analyze named-entity head status and S/V/O order in prepared corpora."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from pipeline_common import (
    PATTERNS,
    ROOT,
    analyses,
    load_manifest,
    package_path,
    read_tsv,
    validate_distribution,
    write_tsv,
)

REFERENCE = ROOT / "reference" / "ner_word_order_counts.tsv"
OUTPUT = ROOT / "outputs" / "data" / "ner_word_order.tsv"
REFERENCE_COLUMNS = (
    "corpus_id",
    "role",
    "entity_status",
    "pattern",
    "count",
    "total",
    "proportion",
)
OUTPUT_COLUMNS = (
    "corpus_id",
    "corpus",
    "role",
    "entity_status",
    "pattern",
    "count",
    "total",
    "proportion",
    "ner_evidence",
    "extraction_status",
)
ROLES = ("subject", "object")
STATUSES = ("entity", "common")


def classify(subject_id: int, verb_id: int, object_id: int) -> str:
    return "".join(
        label
        for _, label in sorted(
            ((subject_id, "S"), (verb_id, "V"), (object_id, "O"))
        )
    )


def entity_status(misc: str) -> str:
    for item in misc.split("|"):
        if item.upper().startswith("NER="):
            tag = item.split("=", 1)[1].upper()
            return "entity" if tag.startswith(("B-", "I-")) else "common"
    return "common"


def extract(path: Path) -> dict[tuple[str, str], Counter[str]]:
    counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    upos: dict[int, str] = {}
    head: dict[int, int] = {}
    relation: dict[int, str] = {}
    status: dict[int, str] = {}

    def flush() -> None:
        if not upos:
            return
        for verb_id, verb_upos in upos.items():
            if verb_upos != "VERB":
                continue
            subjects = [
                token_id
                for token_id in upos
                if head.get(token_id) == verb_id
                and relation[token_id] == "nsubj"
                and upos[token_id] in {"NOUN", "PROPN"}
            ]
            objects = [
                token_id
                for token_id in upos
                if head.get(token_id) == verb_id
                and relation[token_id] == "obj"
                and upos[token_id] in {"NOUN", "PROPN"}
            ]
            for subject_id in subjects:
                for object_id in objects:
                    pattern = classify(subject_id, verb_id, object_id)
                    counts[("subject", status[subject_id])][pattern] += 1
                    counts[("object", status[object_id])][pattern] += 1

    with path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                flush()
                upos, head, relation, status = {}, {}, {}, {}
                continue
            if line.startswith("#"):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) != 10 or not columns[0].isdigit():
                continue
            token_id = int(columns[0])
            upos[token_id] = columns[3]
            head[token_id] = int(columns[6]) if columns[6].isdigit() else 0
            relation[token_id] = columns[7]
            status[token_id] = entity_status(columns[9])
        flush()
    return counts


def load_reference() -> dict[str, dict[tuple[str, str], dict[str, tuple[int, int]]]]:
    rows = read_tsv(REFERENCE, REFERENCE_COLUMNS)
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["role"] not in ROLES or row["entity_status"] not in STATUSES:
            raise RuntimeError(f"{REFERENCE}: invalid role/status row")
        grouped[(row["corpus_id"], row["role"], row["entity_status"])].append(row)
    result: dict[str, dict[tuple[str, str], dict[str, tuple[int, int]]]] = defaultdict(dict)
    for (corpus_id, role, status), group_rows in grouped.items():
        result[corpus_id][(role, status)] = validate_distribution(
            group_rows, f"{corpus_id}/{role}/{status}", REFERENCE
        )
    return dict(result)


def counts_to_distributions(
    counts: dict[tuple[str, str], Counter[str]], corpus_id: str
) -> dict[tuple[str, str], dict[str, tuple[int, int]]]:
    result = {}
    for role in ROLES:
        for status in STATUSES:
            counter = counts[(role, status)]
            total = sum(counter.values())
            if total <= 0:
                raise RuntimeError(f"{corpus_id}: no NER observations for {role}/{status}")
            result[(role, status)] = {
                pattern: (counter[pattern], total) for pattern in PATTERNS
            }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--use-reference-cache",
        action="store_true",
        help="explicitly use verified NER counts for unavailable prepared corpora",
    )
    args = parser.parse_args()
    manifest = load_manifest()
    ner_rows = [row for row in manifest if "ner" in analyses(row)]
    reference = load_reference() if args.use_reference_cache else {}
    names = {row["corpus_id"]: row["display_name"] for row in ner_rows}
    if not set(reference).issubset(names):
        raise RuntimeError(f"{REFERENCE}: contains corpus IDs outside the manifest NER set")

    output_rows: list[dict[str, object]] = []
    for row in ner_rows:
        corpus_id = row["corpus_id"]
        prepared = package_path(row["prepared_input"])
        if prepared.is_file():
            distributions = counts_to_distributions(extract(prepared), corpus_id)
            extraction_status = "direct_from_prepared"
            print(f"{corpus_id}: NER analysis from prepared corpus")
        elif args.use_reference_cache and corpus_id in reference:
            distributions = reference[corpus_id]
            extraction_status = "verified_reference_counts"
            print(f"{corpus_id}: explicit verified NER reference cache")
        else:
            raise SystemExit(
                f"Missing prepared NER corpus for {corpus_id}: {prepared}; "
                "use --use-reference-cache only if the documented cache is acceptable"
            )
        if set(distributions) != {(role, status) for role in ROLES for status in STATUSES}:
            raise RuntimeError(f"{corpus_id}: incomplete NER role/status groups")
        for role in ROLES:
            for status in STATUSES:
                distribution = distributions[(role, status)]
                total = distribution[PATTERNS[0]][1]
                for pattern in PATTERNS:
                    count, pattern_total = distribution[pattern]
                    if pattern_total != total:
                        raise RuntimeError(f"{corpus_id}: inconsistent NER total")
                    output_rows.append(
                        {
                            "corpus_id": corpus_id,
                            "corpus": row["display_name"],
                            "role": role,
                            "entity_status": status,
                            "pattern": pattern,
                            "count": count,
                            "total": total,
                            "proportion": f"{count / total:.6f}",
                            "ner_evidence": row["ner_family"],
                            "extraction_status": extraction_status,
                        }
                    )

    expected_rows = len(ner_rows) * len(ROLES) * len(STATUSES) * len(PATTERNS)
    if len(output_rows) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} NER rows, found {len(output_rows)}")
    write_tsv(OUTPUT, OUTPUT_COLUMNS, output_rows)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(output_rows)} rows)")


if __name__ == "__main__":
    main()
