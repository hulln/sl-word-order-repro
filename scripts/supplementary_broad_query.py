#!/usr/bin/env python3
"""Reproduce the broad-argument SSJ/SST sensitivity query on UD 2.18.

The query is ``upos=VERB >nsubj _ >obj _``. Every subject x object pair is one
instance; the output is therefore not a count of distinct STARK form/tree rows.
The same pass also asserts the canonical NOUN-only totals and SVO counts.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from pipeline_common import PATTERNS, ROOT, load_manifest, package_path, sha256, write_tsv

OUTPUT = ROOT / "outputs" / "supplementary" / "broad_argument_query.tsv"
CORPORA = ("ssj", "sst")
COLUMNS = (
    "corpus_id", "corpus", "query", "total",
    "SVO_n", "SVO_proportion", "SOV_n", "SOV_proportion",
    "VSO_n", "VSO_proportion", "VOS_n", "VOS_proportion",
    "OSV_n", "OSV_proportion", "OVS_n", "OVS_proportion",
    "entropy_nat", "top_order", "second_order", "top_second_ratio",
    "dominant_order", "dominant_flag",
)
EXPECTED_BROAD = {
    "ssj": {"SVO": 2131, "SOV": 427, "VSO": 108, "VOS": 83, "OSV": 333, "OVS": 826},
    "sst": {"SVO": 327, "SOV": 174, "VSO": 39, "VOS": 20, "OSV": 130, "OVS": 145},
}
EXPECTED_NOUN_CONTROLS = {
    "ssj": {"total": 1969, "SVO": 1406},
    "sst": {"total": 168, "SVO": 108},
}
EXPECTED_DOMINANCE = {"ssj": "SVO", "sst": "NO DOMINANT ORDER"}


def classify(subject_id: int, verb_id: int, object_id: int) -> str:
    return "".join(label for _, label in sorted(
        ((subject_id, "S"), (verb_id, "V"), (object_id, "O"))
    ))


def extract(path: Path) -> tuple[Counter[str], Counter[str]]:
    broad: Counter[str] = Counter()
    noun_only: Counter[str] = Counter()
    upos: dict[int, str] = {}
    head: dict[int, int] = {}
    deprel: dict[int, str] = {}

    def flush() -> None:
        if not upos:
            return
        for verb_id, verb_upos in upos.items():
            if verb_upos != "VERB":
                continue
            subjects = [
                token_id for token_id in upos
                if head.get(token_id) == verb_id and deprel[token_id] == "nsubj"
            ]
            objects = [
                token_id for token_id in upos
                if head.get(token_id) == verb_id and deprel[token_id] == "obj"
            ]
            for subject_id in subjects:
                for object_id in objects:
                    pattern = classify(subject_id, verb_id, object_id)
                    broad[pattern] += 1
                    if upos[subject_id] == "NOUN" and upos[object_id] == "NOUN":
                        noun_only[pattern] += 1

    with path.open(encoding="utf-8-sig", errors="strict") as handle:
        for line in handle:
            if not line.strip():
                flush()
                upos, head, deprel = {}, {}, {}
                continue
            if line.startswith("#"):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) != 10 or not columns[0].isdigit():
                continue
            token_id = int(columns[0])
            upos[token_id] = columns[3]
            head[token_id] = int(columns[6]) if columns[6].isdigit() else 0
            deprel[token_id] = columns[7]
    flush()
    return broad, noun_only


def entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    return -sum(
        (counts[pattern] / total) * math.log(counts[pattern] / total)
        for pattern in PATTERNS if counts[pattern]
    )


def build_row(corpus_id: str, display_name: str, counts: Counter[str]) -> dict[str, object]:
    total = sum(counts.values())
    ranking = sorted(PATTERNS, key=lambda pattern: (-counts[pattern], PATTERNS.index(pattern)))
    top, second = ranking[:2]
    ratio = counts[top] / counts[second] if counts[second] else math.inf
    dominant = top if ratio > 2 else "NO DOMINANT ORDER"
    row: dict[str, object] = {
        "corpus_id": corpus_id,
        "corpus": display_name,
        "query": "upos=VERB >nsubj _ >obj _",
        "total": total,
        "entropy_nat": f"{entropy(counts):.6f}",
        "top_order": top,
        "second_order": second,
        "top_second_ratio": f"{ratio:.6f}",
        "dominant_order": dominant,
        "dominant_flag": "dominant" if dominant == top else "no_dominant_order",
    }
    for pattern in PATTERNS:
        row[f"{pattern}_n"] = counts[pattern]
        row[f"{pattern}_proportion"] = f"{counts[pattern] / total:.6f}"
    return row


def main() -> None:
    manifest = {row["corpus_id"]: row for row in load_manifest()}
    rows = []
    for corpus_id in CORPORA:
        metadata = manifest[corpus_id]
        path = package_path(metadata["prepared_input"])
        actual_hash = sha256(path)
        if actual_hash != metadata["prepared_sha256"]:
            raise RuntimeError(
                f"{corpus_id}: prepared hash {actual_hash} does not match canonical "
                f"{metadata['prepared_sha256']}"
            )
        broad, noun_only = extract(path)
        if dict(broad) != EXPECTED_BROAD[corpus_id]:
            raise RuntimeError(
                f"{corpus_id}: broad counts differ: expected {EXPECTED_BROAD[corpus_id]}, "
                f"found {dict(broad)}"
            )
        noun_control = EXPECTED_NOUN_CONTROLS[corpus_id]
        if sum(noun_only.values()) != noun_control["total"] or noun_only["SVO"] != noun_control["SVO"]:
            raise RuntimeError(
                f"{corpus_id}: NOUN-only control differs: expected {noun_control}, "
                f"found total={sum(noun_only.values())}, SVO={noun_only['SVO']}"
            )
        row = build_row(corpus_id, metadata["display_name"], broad)
        if row["dominant_order"] != EXPECTED_DOMINANCE[corpus_id]:
            raise RuntimeError(
                f"{corpus_id}: expected dominance {EXPECTED_DOMINANCE[corpus_id]}, "
                f"found {row['dominant_order']}"
            )
        rows.append(row)
        print(
            f"{corpus_id}: broad n={row['total']}, SVO={row['SVO_n']} "
            f"({100 * int(row['SVO_n']) / int(row['total']):.4f}%); "
            f"NOUN control n={sum(noun_only.values())}, SVO={noun_only['SVO']}"
        )
    write_tsv(OUTPUT, COLUMNS, rows)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
