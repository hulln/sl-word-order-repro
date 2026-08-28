#!/usr/bin/env python3
"""Compute canonical summary tables and thesis statistics.

Reads ``word_order_counts.tsv`` and ``ner_word_order.tsv`` and writes
``word_order_summary.tsv`` and ``statistical_tests.tsv`` under ``outputs/data``.
The tests comprise Pearson chi-square comparisons, H1/H2 permutation tests and
NER Fisher exact tests, with Holm adjustment where applicable.
"""

from __future__ import annotations

import argparse
import math
from collections import defaultdict

import numpy as np
from scipy.stats import chi2_contingency, fisher_exact

from pipeline_common import PATTERNS, ROOT, load_manifest, read_tsv, write_tsv

WORD_COUNTS = ROOT / "outputs" / "data" / "word_order_counts.tsv"
NER_COUNTS = ROOT / "outputs" / "data" / "ner_word_order.tsv"
SUMMARY = ROOT / "outputs" / "data" / "word_order_summary.tsv"
TESTS = ROOT / "outputs" / "data" / "statistical_tests.tsv"
WORD_COLUMNS = (
    "corpus_id", "corpus", "pattern", "count", "total", "proportion", "extraction_status"
)
NER_COLUMNS = (
    "corpus_id", "corpus", "role", "entity_status", "pattern", "count", "total",
    "proportion", "ner_evidence", "extraction_status",
)
SUMMARY_COLUMNS = (
    "corpus_id", "corpus", "total",
    "SVO_n", "SVO_proportion", "SOV_n", "SOV_proportion",
    "VSO_n", "VSO_proportion", "VOS_n", "VOS_proportion",
    "OSV_n", "OSV_proportion", "OVS_n", "OVS_proportion",
    "dominant_order", "dominant_flag", "entropy_nat", "extraction_status",
)
TEST_COLUMNS = (
    "test_family", "test_id", "corpus_a", "corpus_b", "statistic_name",
    "statistic", "df", "p_value", "p_adjusted", "effect_name", "effect_value",
    "n_a", "n_b", "permutations", "seed", "notes",
)
PERMUTATIONS = 20_000
H1_SEED = 20260715
SELECTED_PAIRS = (
    # The first six rows and their independent streams reproduce the frozen
    # UD 2.18 genre-comparison artifact. Later rows cannot shift those streams.
    ("suk-professional", "suk-publicistic", 20260714),
    ("suk-professional", "suk-literary", 20260715),
    ("suk-professional", "sst", 20260716),
    ("suk-publicistic", "suk-literary", 20260717),
    ("suk-publicistic", "sst", 20260718),
    ("suk-literary", "sst", 20260719),
    ("ssj", "sst", 20260720),
    ("human-essays", "gpt5-essays", 20260721),
    ("gpt5-essays", "aigent-gpt5", 20260722),
    ("suk-literary", "kdsp", 20260723),
)
H2_PAIRS = {
    frozenset(("suk-professional", "sst")),
    frozenset(("suk-publicistic", "sst")),
    frozenset(("suk-professional", "suk-literary")),
    frozenset(("suk-publicistic", "suk-literary")),
}
CANONICAL_TOTALS = {
    "ssj": 1969,
    "sst": 168,
    "suk-literary": 162,
    "suk-publicistic": 2837,
    "suk-professional": 1105,
    "human-essays": 1671,
    "gpt5-essays": 3248,
}
CANONICAL_H2_PERMUTATION_P = {
    frozenset(("suk-professional", "suk-literary")): "0.546773",
    frozenset(("suk-publicistic", "suk-literary")): "0.724414",
    frozenset(("suk-professional", "sst")): "0.000950",
    frozenset(("suk-publicistic", "sst")): "0.001800",
}
CANONICAL_SUPPLEMENTARY_PERMUTATION_P = {
    frozenset(("gpt5-essays", "aigent-gpt5")): "0.0785960702",
    frozenset(("suk-literary", "kdsp")): "0.0072496375",
}


def load_word_matrix(manifest: list[dict[str, str]]) -> tuple[dict[str, np.ndarray], dict[str, dict[str, str]]]:
    rows = read_tsv(WORD_COUNTS, WORD_COLUMNS)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["corpus_id"]].append(row)
    expected = [row["corpus_id"] for row in manifest]
    if list(grouped) != expected:
        raise RuntimeError("word_order_counts.tsv corpus order differs from the manifest")
    matrix, metadata = {}, {}
    for manifest_row in manifest:
        corpus_id = manifest_row["corpus_id"]
        corpus_rows = grouped[corpus_id]
        if [row["pattern"] for row in corpus_rows] != list(PATTERNS):
            raise RuntimeError(f"{corpus_id}: invalid pattern order")
        counts = np.array([int(row["count"]) for row in corpus_rows], dtype=np.int64)
        total = int(corpus_rows[0]["total"])
        if counts.sum() != total:
            raise RuntimeError(f"{corpus_id}: counts do not sum to total")
        if corpus_id in CANONICAL_TOTALS and total != CANONICAL_TOTALS[corpus_id]:
            raise RuntimeError(
                f"{corpus_id}: expected canonical total {CANONICAL_TOTALS[corpus_id]}, found {total}"
            )
        matrix[corpus_id] = counts
        metadata[corpus_id] = corpus_rows[0]
    return matrix, metadata


def entropy_natural(counts: np.ndarray) -> float:
    proportions = counts / counts.sum()
    return -sum(float(value) * math.log(float(value)) for value in proportions if value > 0)


def build_summary(
    manifest: list[dict[str, str]], matrix: dict[str, np.ndarray], metadata: dict[str, dict[str, str]]
) -> list[dict[str, object]]:
    rows = []
    for manifest_row in manifest:
        corpus_id = manifest_row["corpus_id"]
        counts = matrix[corpus_id]
        total = int(counts.sum())
        proportions = counts / total
        ranking = np.argsort(-proportions, kind="stable")
        dominant = int(ranking[0])
        second = int(ranking[1])
        row: dict[str, object] = {
            "corpus_id": corpus_id,
            "corpus": manifest_row["display_name"],
            "total": total,
        }
        for index, pattern in enumerate(PATTERNS):
            row[f"{pattern}_n"] = int(counts[index])
            row[f"{pattern}_proportion"] = f"{proportions[index]:.6f}"
        row["dominant_order"] = PATTERNS[dominant]
        row["dominant_flag"] = (
            "dominant"
            if proportions[second] == 0 or proportions[dominant] > 2 * proportions[second]
            else "no_dominant_order"
        )
        row["entropy_nat"] = f"{entropy_natural(counts):.6f}"
        row["extraction_status"] = metadata[corpus_id]["extraction_status"]
        rows.append(row)
    return rows


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    pa, pb = a / a.sum(), b / b.sum()
    return float(np.dot(pa, pb) / (np.linalg.norm(pa) * np.linalg.norm(pb)))


def js_distance(a: np.ndarray, b: np.ndarray) -> float:
    pa, pb = a / a.sum(), b / b.sum()
    midpoint = (pa + pb) / 2

    def divergence(p: np.ndarray) -> float:
        return sum(float(value) * math.log2(float(value / middle)) for value, middle in zip(p, midpoint) if value > 0)

    return math.sqrt((divergence(pa) + divergence(pb)) / 2)


def base_test_row(**values: object) -> dict[str, object]:
    row = {column: "" for column in TEST_COLUMNS}
    row.update(values)
    return row


def pairwise_tests(manifest: list[dict[str, str]], matrix: dict[str, np.ndarray]) -> list[dict[str, object]]:
    ids = [row["corpus_id"] for row in manifest]
    rows = []
    for index, corpus_a in enumerate(ids):
        for corpus_b in ids[index + 1 :]:
            a, b = matrix[corpus_a], matrix[corpus_b]
            table = np.vstack((a, b))
            keep = table.sum(axis=0) > 0
            chi2, p_value, degrees, _ = chi2_contingency(table[:, keep], correction=False)
            common = {
                "corpus_a": corpus_a,
                "corpus_b": corpus_b,
                "n_a": int(a.sum()),
                "n_b": int(b.sum()),
            }
            rows.append(base_test_row(
                test_family="all_pairwise", test_id=f"{corpus_a}__{corpus_b}__chi_square",
                statistic_name="pearson_chi_square", statistic=f"{chi2:.12g}", df=degrees,
                p_value=f"{p_value:.12g}", notes="2 x 6 distribution", **common,
            ))
            rows.append(base_test_row(
                test_family="all_pairwise", test_id=f"{corpus_a}__{corpus_b}__jsd",
                statistic_name="descriptive_distance", effect_name="jensen_shannon_distance_base2",
                effect_value=f"{js_distance(a, b):.6f}", notes="square-root Jensen-Shannon distance", **common,
            ))
            rows.append(base_test_row(
                test_family="all_pairwise", test_id=f"{corpus_a}__{corpus_b}__cosine",
                statistic_name="descriptive_similarity", effect_name="cosine_similarity",
                effect_value=f"{cosine_similarity(a, b):.6f}",
                notes="cosine similarity of six-order proportion vectors", **common,
            ))
    return rows


def permutation_pair(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float, int, int]:
    table = np.vstack((a, b))
    keep = table.sum(axis=0) > 0
    table = table[:, keep]
    chi2, pearson_p, degrees, expected = chi2_contingency(table, correction=False)
    n_a = int(table[0].sum())
    pool = np.repeat(np.arange(table.shape[1]), table.sum(axis=0))
    extreme = 0
    for _ in range(PERMUTATIONS):
        rng.shuffle(pool)
        random_a = np.bincount(pool[:n_a], minlength=table.shape[1])
        random_b = np.bincount(pool[n_a:], minlength=table.shape[1])
        random_table = np.vstack((random_a, random_b))
        random_keep = random_table.sum(axis=0) > 0
        random_chi2, _, _, _ = chi2_contingency(random_table[:, random_keep], correction=False)
        extreme += random_chi2 >= chi2
    return chi2, pearson_p, (extreme + 1) / (PERMUTATIONS + 1), degrees, int((expected < 5).sum())


def holm(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    adjusted = [0.0] * len(values)
    previous = 0.0
    for rank, index in enumerate(order):
        previous = max(previous, min(1.0, (len(values) - rank) * values[index]))
        adjusted[index] = previous
    return adjusted


def selected_permutation_tests(matrix: dict[str, np.ndarray]) -> list[dict[str, object]]:
    calculations = []
    for corpus_a, corpus_b, seed in SELECTED_PAIRS:
        chi2, pearson_p, permutation_p, degrees, cells_under_five = permutation_pair(
            matrix[corpus_a], matrix[corpus_b], np.random.default_rng(seed)
        )
        expected = CANONICAL_H2_PERMUTATION_P.get(frozenset((corpus_a, corpus_b)))
        if expected is not None and f"{permutation_p:.6f}" != expected:
            raise RuntimeError(
                f"{corpus_a}/{corpus_b}: expected frozen permutation p={expected}, "
                f"found {permutation_p:.6f}"
            )
        supplementary_expected = CANONICAL_SUPPLEMENTARY_PERMUTATION_P.get(
            frozenset((corpus_a, corpus_b))
        )
        if supplementary_expected is not None and f"{permutation_p:.10f}" != supplementary_expected:
            raise RuntimeError(
                f"{corpus_a}/{corpus_b}: expected supplementary permutation "
                f"p={supplementary_expected}, found {permutation_p:.10f}"
            )
        calculations.append(
            (corpus_a, corpus_b, seed, chi2, pearson_p, permutation_p, degrees, cells_under_five)
        )
    h2_indices = [
        index
        for index, (a, b, _seed, *_rest) in enumerate(calculations)
        if frozenset((a, b)) in H2_PAIRS
    ]
    adjusted = holm([calculations[index][5] for index in h2_indices])
    adjusted_by_index = dict(zip(h2_indices, adjusted))
    rows = []
    for index, (a, b, seed, chi2, pearson_p, permutation_p, degrees, cells_under_five) in enumerate(calculations):
        family = "h2_prespecified" if index in adjusted_by_index else "selected_validation"
        rows.append(base_test_row(
            test_family=family,
            test_id=f"{a}__{b}__permutation_chi_square",
            corpus_a=a,
            corpus_b=b,
            statistic_name="pearson_chi_square_with_permutation_p",
            statistic=f"{chi2:.12g}",
            df=degrees,
            p_value=f"{permutation_p:.12g}",
            p_adjusted=f"{adjusted_by_index[index]:.12g}" if index in adjusted_by_index else "",
            n_a=int(matrix[a].sum()),
            n_b=int(matrix[b].sum()),
            permutations=PERMUTATIONS,
            seed=seed,
            notes=f"Pearson asymptotic p={pearson_p:.12g}; expected cells under 5={cells_under_five}",
        ))
    return rows


def h1_test(matrix: dict[str, np.ndarray]) -> dict[str, object]:
    ids = ("suk-literary", "suk-publicistic", "suk-professional")
    table = np.vstack([matrix[corpus_id] for corpus_id in ids])
    chi2, pearson_p, degrees, expected = chi2_contingency(table, correction=False)
    sizes = table.sum(axis=1)
    pool = np.repeat(np.arange(table.shape[1]), table.sum(axis=0))
    rng = np.random.default_rng(H1_SEED)
    extreme = 0
    for _ in range(PERMUTATIONS):
        rng.shuffle(pool)
        cut_one = int(sizes[0])
        cut_two = int(sizes[0] + sizes[1])
        random_table = np.vstack(
            (
                np.bincount(pool[:cut_one], minlength=table.shape[1]),
                np.bincount(pool[cut_one:cut_two], minlength=table.shape[1]),
                np.bincount(pool[cut_two:], minlength=table.shape[1]),
            )
        )
        random_chi2 = float(((random_table - expected) ** 2 / expected).sum())
        extreme += random_chi2 >= chi2
    permutation_p = (extreme + 1) / (PERMUTATIONS + 1)
    if f"{permutation_p:.6f}" != "0.183991":
        raise RuntimeError(
            f"H1: expected frozen permutation p=0.183991, found {permutation_p:.6f}"
        )
    return base_test_row(
        test_family="h1_omnibus",
        test_id="suk_three_genres__permutation_chi_square",
        corpus_a="suk-literary,suk-publicistic,suk-professional",
        statistic_name="pearson_3x6_with_permutation_p",
        statistic=f"{chi2:.12g}",
        df=degrees,
        p_value=f"{permutation_p:.12g}",
        n_a=int(table.sum()),
        permutations=PERMUTATIONS,
        seed=H1_SEED,
        notes=f"Pearson asymptotic p={pearson_p:.12g}; minimum expected={expected.min():.6g}; cells under 5={int((expected < 5).sum())}",
    )


def ner_tests() -> list[dict[str, object]]:
    rows = read_tsv(NER_COUNTS, NER_COLUMNS)
    grouped: dict[tuple[str, str, str], dict[str, int]] = defaultdict(dict)
    evidence = {}
    for row in rows:
        key = (row["corpus_id"], row["role"], row["entity_status"])
        grouped[key][row["pattern"]] = int(row["count"])
        evidence[row["corpus_id"]] = row["ner_evidence"]
    raw = []
    for corpus_id in dict.fromkeys(row["corpus_id"] for row in rows):
        for role in ("subject", "object"):
            entity = grouped[(corpus_id, role, "entity")]
            common = grouped[(corpus_id, role, "common")]
            if set(entity) != set(PATTERNS) or set(common) != set(PATTERNS):
                raise RuntimeError(f"{corpus_id}/{role}: incomplete NER pattern counts")
            if role == "object":
                entity_outcome = entity["OVS"] + entity["OSV"]
                common_outcome = common["OVS"] + common["OSV"]
                outcome = "OVS+OSV"
            else:
                entity_outcome = entity["SVO"]
                common_outcome = common["SVO"]
                outcome = "SVO"
            entity_total, common_total = sum(entity.values()), sum(common.values())
            odds, p_value = fisher_exact(
                ((entity_outcome, entity_total - entity_outcome),
                 (common_outcome, common_total - common_outcome)),
                alternative="two-sided",
            )
            raw.append({
                "corpus_id": corpus_id, "role": role, "outcome": outcome,
                "entity_outcome": entity_outcome, "common_outcome": common_outcome,
                "entity_total": entity_total, "common_total": common_total,
                "odds": odds, "p": p_value, "family": evidence[corpus_id],
            })
    adjusted = {}
    for family in ("manual_ner", "automatic_ner"):
        indices = [index for index, row in enumerate(raw) if row["family"] == family]
        if len(indices) != 8:
            raise RuntimeError(f"{family}: expected eight Fisher tests, found {len(indices)}")
        for index, value in zip(indices, holm([raw[index]["p"] for index in indices])):
            adjusted[index] = value
    output = []
    for index, row in enumerate(raw):
        output.append(base_test_row(
            test_family=f"ner_fisher_{row['family']}",
            test_id=f"{row['corpus_id']}__{row['role']}__fisher",
            corpus_a=f"{row['corpus_id']}:entity",
            corpus_b=f"{row['corpus_id']}:common",
            statistic_name="fisher_exact_two_sided",
            statistic=f"{row['odds']:.12g}",
            p_value=f"{row['p']:.12g}",
            p_adjusted=f"{adjusted[index]:.12g}",
            effect_name="odds_ratio",
            effect_value=f"{row['odds']:.12g}",
            n_a=row["entity_total"],
            n_b=row["common_total"],
            notes=(
                f"outcome={row['outcome']}; entity outcome={row['entity_outcome']}; "
                f"common outcome={row['common_outcome']}; Holm family={row['family']}"
            ),
        ))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    manifest = load_manifest()
    matrix, metadata = load_word_matrix(manifest)
    summary_rows = build_summary(manifest, matrix, metadata)
    test_rows = pairwise_tests(manifest, matrix)
    test_rows.append(h1_test(matrix))
    test_rows.extend(selected_permutation_tests(matrix))
    test_rows.extend(ner_tests())
    write_tsv(SUMMARY, SUMMARY_COLUMNS, summary_rows)
    write_tsv(TESTS, TEST_COLUMNS, test_rows)
    print(f"Wrote {SUMMARY.relative_to(ROOT)} ({len(summary_rows)} rows)")
    print(f"Wrote {TESTS.relative_to(ROOT)} ({len(test_rows)} rows)")


if __name__ == "__main__":
    main()
