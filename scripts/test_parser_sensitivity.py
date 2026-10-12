#!/usr/bin/env python3
"""Verify the published parser-sensitivity aggregates (thesis Section 4.2.4).

Run from the repository root: python3 scripts/test_parser_sensitivity.py
Standard library only. The script performs two supported levels of checking:

1. Internal verification: totals, denominators, retention identities,
   percentages, entropies, Jensen-Shannon distances and the agreement
   matrices are recomputed from the published aggregate tables and compared
   with ``outputs/supplementary/parser_sensitivity_summary.json``.
2. Cross-checks: the reference side of both query variants is compared with
   the canonical public tables (``outputs/data/word_order_counts.tsv``,
   ``outputs/data/ner_word_order.tsv``) and the pinned SSJ inventory entry in
   ``config/corpora.tsv``. If ``prepared/ssj.conllu`` is present, its SHA-256
   is checked; with ``--auto PATH`` the SHA-256 of a locally available copy
   of the saved CLASSLA-Stanza 2.2.1 parse is checked as well.

A third level, re-running the original instance-level comparison, needs the
saved automatic parse, which is not distributed; this script does NOT
reproduce that comparison, it only verifies the published aggregates.

Numerical conventions: entropy is the natural-log Shannon entropy of the
six-pattern distribution; the Jensen-Shannon distance is
sqrt((KL(p||m) + KL(q||m)) / 2) with base-2 logarithms and m = (p+q)/2.
Full-precision values are compared with absolute tolerance 1e-9; values the
tables print with four or eight decimals are compared with half-unit
rounding tolerances (5e-5 and 1e-8).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUP = ROOT / "outputs/supplementary"
PATTERNS = ["SVO", "SOV", "VSO", "VOS", "OSV", "OVS"]

# Recorded thesis values (Section 4.2.4); the run must stop if any differs.
RECORDED = {
    "NOUN": {"gold_n": 1969, "auto_n": 1882, "aligned_n": 1788,
             "same_pattern": 1780, "changed_pattern": 8, "not_retained": 189},
    "NOUN|PROPN": {"gold_n": 2542, "auto_n": 2445, "aligned_n": 2310,
                   "same_pattern": 2300, "changed_pattern": 10, "not_retained": 242},
}
REASON_POPULATIONS = {"gold_only": 177, "auto_only": 89}
NO_MISSING = "missing_sentence_token_or_unexplained_residual"

failures: list[str] = []
checks = 0


def check(condition: bool, label: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(label)
        print(f"FAIL: {label}")


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def entropy_nat(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    return -sum((n / total) * math.log(n / total) for n in counts.values() if n)


def js_distance_base2(a: dict[str, int], b: dict[str, int]) -> float:
    pa = [a[p] / sum(a.values()) for p in PATTERNS]
    pb = [b[p] / sum(b.values()) for p in PATTERNS]
    mid = [(x + y) / 2 for x, y in zip(pa, pb)]
    def kl(p, q):
        return sum(x * math.log2(x / y) for x, y in zip(p, q) if x)
    return math.sqrt((kl(pa, mid) + kl(pb, mid)) / 2)


def verify_variant(name: str, summary: dict, distribution: Path, matrix: Path) -> dict[str, dict[str, int]]:
    """Level 1: internal verification of one query variant. Returns the counts."""
    rows = read_tsv(distribution)
    check([r["pattern"] for r in rows] == PATTERNS,
          f"{name}: distribution lists the six patterns in canonical order")
    gold = {r["pattern"]: int(r["gold_n"]) for r in rows}
    auto = {r["pattern"]: int(r["auto_n"]) for r in rows}
    s = summary

    check(sum(gold.values()) == s["gold_n"], f"{name}: gold counts sum to gold_n")
    check(sum(auto.values()) == s["auto_n"], f"{name}: auto counts sum to auto_n")
    for r in rows:
        for side, counts in (("gold", gold), ("auto", auto)):
            printed = float(r[f"{side}_pct"])
            exact = 100 * counts[r["pattern"]] / sum(counts.values())
            check(close(printed, exact, 5e-5), f"{name}: {side}_pct of {r['pattern']}")
        check(close(float(r["diff_pp"]), float(r["auto_pct"]) - float(r["gold_pct"]), 5e-5),
              f"{name}: diff_pp of {r['pattern']}")

    cells = {(r["GOLD"], r["AUTO"]): int(r["n"]) for r in read_tsv(matrix)}
    check(all(g in PATTERNS and a in PATTERNS for g, a in cells),
          f"{name}: matrix uses only the six patterns")
    check(sum(cells.values()) == s["aligned_n"], f"{name}: matrix sums to aligned_n")
    check(sum(n for (g, a), n in cells.items() if g == a) == s["same_pattern"],
          f"{name}: matrix diagonal equals same_pattern")
    off_diagonal = {k: n for k, n in cells.items() if k[0] != k[1]}
    check(off_diagonal == {("OVS", "SVO"): RECORDED[name]["changed_pattern"]},
          f"{name}: all pattern changes are OVS->SVO "
          f"({RECORDED[name]['changed_pattern']} instances)")
    for pattern in PATTERNS:
        check(sum(n for (g, _), n in cells.items() if g == pattern) <= gold[pattern],
              f"{name}: aligned gold marginal of {pattern} within gold count")
        check(sum(n for (_, a), n in cells.items() if a == pattern) <= auto[pattern],
              f"{name}: aligned auto marginal of {pattern} within auto count")

    for key, value in RECORDED[name].items():
        if key != "not_retained":
            check(s[key] == value, f"{name}: recorded {key} = {value}")
    check(s["aligned_n"] == s["same_pattern"] + s["changed_pattern"],
          f"{name}: aligned_n = same_pattern + changed_pattern")
    check(s["gold_n"] == s["aligned_n"] + s["gold_only"] + s["unclear_gold_instances"],
          f"{name}: gold_n = aligned + gold_only + unclear gold")
    check(s["auto_n"] == s["aligned_n"] + s["auto_only"] + s["unclear_auto_instances"],
          f"{name}: auto_n = aligned + auto_only + unclear auto")
    check(s["manual_review_n"] == s["gold_only"] + s["auto_only"]
          + s["changed_pattern"] + s["unclear_alignment"],
          f"{name}: manual_review_n composition")
    check(s["gold_n"] - s["same_pattern"] == RECORDED[name]["not_retained"],
          f"{name}: not-retained reference instances = {RECORDED[name]['not_retained']}")
    check(close(s["gold_recall_pct"], 100 * s["aligned_n"] / s["gold_n"]),
          f"{name}: gold_recall_pct")
    check(close(s["same_among_aligned_pct"], 100 * s["same_pattern"] / s["aligned_n"]),
          f"{name}: same_among_aligned_pct")
    check(close(s["changed_or_lost_gold_pct"],
                100 * (s["gold_n"] - s["same_pattern"]) / s["gold_n"]),
          f"{name}: changed_or_lost_gold_pct")
    check(close(s["gold_entropy_ln"], entropy_nat(gold)), f"{name}: gold entropy (ln)")
    check(close(s["auto_entropy_ln"], entropy_nat(auto)), f"{name}: auto entropy (ln)")
    check(close(s["jensen_shannon_distance_base2"], js_distance_base2(gold, auto)),
          f"{name}: Jensen-Shannon distance (base 2)")
    check(s["random_seed"] == 20260809, f"{name}: recorded random seed")
    return {"gold": gold, "auto": auto}


def verify_reasons(summary_noun: dict) -> None:
    """Level 1: the discrepancy-reason table of the canonical NOUN query."""
    rows = read_tsv(SUP / "parser_sensitivity_discrepancy_reasons.tsv")
    check({r["direction"] for r in rows} == set(REASON_POPULATIONS),
          "reasons: directions are gold_only and auto_only")
    for direction, population in REASON_POPULATIONS.items():
        subset = [r for r in rows if r["direction"] == direction]
        check(summary_noun[direction] == population,
              f"reasons: summary {direction} = {population}")
        check(all(int(r["population_n"]) == population for r in subset),
              f"reasons: population_n of {direction}")
        check(all(0 <= int(r["count"]) <= population for r in subset),
              f"reasons: counts of {direction} within population")
        for r in subset:
            check(close(float(r["pct_of_population"]),
                        100 * int(r["count"]) / population, 1e-8),
                  f"reasons: pct of {direction}/{r['reason_code']}")
        missing = [r for r in subset if r["reason_code"] == NO_MISSING]
        check(len(missing) == 1 and int(missing[0]["count"]) == 0,
              f"reasons: no missing-sentence/unexplained residual in {direction}")


def cross_checks(public: dict, counts: dict[str, dict[str, dict[str, int]]]) -> None:
    """Level 2: agreement with the canonical public SSJ tables and inventory."""
    word_order = [r for r in read_tsv(ROOT / "outputs/data/word_order_counts.tsv")
                  if r["corpus_id"] == "ssj"]
    main = {r["pattern"]: int(r["count"]) for r in word_order}
    check(main == counts["NOUN"]["gold"],
          "cross: NOUN gold counts equal outputs/data/word_order_counts.tsv (ssj)")
    check(all(int(r["total"]) == 1969 for r in word_order),
          "cross: word_order_counts.tsv ssj total is 1969")

    ner = [r for r in read_tsv(ROOT / "outputs/data/ner_word_order.tsv")
           if r["corpus_id"] == "ssj" and r["role"] == "subject"]
    check({r["entity_status"] for r in ner} == {"entity", "common"},
          "cross: ner_word_order.tsv ssj subject splits into entity and common")
    ner_sums = {p: sum(int(r["count"]) for r in ner if r["pattern"] == p)
                for p in PATTERNS}
    check(ner_sums == counts["NOUN|PROPN"]["gold"],
          "cross: NOUN|PROPN gold counts equal the ssj subject sums "
          "of outputs/data/ner_word_order.tsv")

    inventory = [r for r in read_tsv(ROOT / "config/corpora.tsv")
                 if r["corpus_id"] == "ssj"]
    check(len(inventory) == 1, "cross: one ssj row in config/corpora.tsv")
    row = inventory[0]
    check(row["prepared_sha256"] == public["reference"]["sha256"],
          "cross: reference SHA-256 equals the pinned ssj hash in config/corpora.tsv")
    check(int(row["expected_sentences"]) == public["reference"]["sentence_count"] == 13435,
          "cross: 13,435 sentences in both the inventory and the summary")
    check(row["version"] == "UD 2.18" and "2.18" in public["reference"]["release"],
          "cross: both sides identify the UD 2.18 release")


def optional_hash_checks(public: dict, auto_path: Path | None) -> None:
    """Level 2 (optional): hashes of locally available input files."""
    reference = ROOT / public["reference"]["path"]
    if reference.exists():
        check(sha256(reference) == public["reference"]["sha256"],
              "hash: prepared/ssj.conllu matches the pinned reference SHA-256")
    else:
        print("note: prepared/ssj.conllu not present; reference hash check skipped "
              "(rebuild it from the public UD 2.18 release to enable it)")
    if auto_path is None:
        print("note: no --auto path given; the saved CLASSLA-Stanza 2.2.1 parse is "
              "not distributed here and the original comparison is NOT re-run")
        return
    digest = sha256(auto_path)
    expected = {public["automatic_parse"]["source_sha256"]: "source parse",
                public["automatic_parse"]["harmonised_copy_sha256"]: "harmonised-ID copy"}
    check(digest in expected,
          f"hash: --auto file matches a recorded automatic-parse SHA-256 ({auto_path})")
    if digest in expected:
        print(f"ok: --auto file identified as the {expected[digest]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--auto", type=Path, default=None,
                        help="optional local copy of the saved CLASSLA parse, "
                             "verified by SHA-256 only")
    args = parser.parse_args()

    public = json.loads((SUP / "parser_sensitivity_summary.json").read_text(encoding="utf-8"))
    summaries = public["summaries"]
    check(summaries["NOUN"]["gold_sha256"] == summaries["NOUN|PROPN"]["gold_sha256"]
          == public["reference"]["sha256"],
          "summary: one reference SHA-256 across both variants")
    check(summaries["NOUN"]["auto_sha256"] == summaries["NOUN|PROPN"]["auto_sha256"]
          == public["automatic_parse"]["harmonised_copy_sha256"],
          "summary: one automatic-parse SHA-256 across both variants")
    check(public["automatic_parse"]["classla_rerun"] is False,
          "summary: records that CLASSLA was not rerun")
    harmonisation = public["sentence_id_harmonisation"]
    check(harmonisation["identical_ids"] + harmonisation["renamed_ids"]
          == public["reference"]["sentence_count"],
          "summary: sentence-ID harmonisation covers all 13,435 sentences")
    check(harmonisation["renamed_ids"] == 2024, "summary: 2,024 renamed sentence IDs")

    print("[1] Internal verification of the published aggregates")
    counts = {
        "NOUN": verify_variant("NOUN", summaries["NOUN"],
                               SUP / "parser_sensitivity_distribution.tsv",
                               SUP / "parser_sensitivity_gold_auto_matrix.tsv"),
        "NOUN|PROPN": verify_variant("NOUN|PROPN", summaries["NOUN|PROPN"],
                                     SUP / "parser_sensitivity_distribution_noun_propn.tsv",
                                     SUP / "parser_sensitivity_gold_auto_matrix_noun_propn.tsv"),
    }
    verify_reasons(summaries["NOUN"])

    print("[2] Cross-checks against canonical public tables and pinned hashes")
    cross_checks(public, counts)
    optional_hash_checks(public, args.auto)

    print("[3] Re-running the original comparison is not supported from public "
          "files (the saved automatic parse is not distributed) and was not attempted")

    if failures:
        print(f"{len(failures)} of {checks} checks FAILED")
        return 1
    print(f"All {checks} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
