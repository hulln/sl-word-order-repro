#!/usr/bin/env python3
"""Reproduce cluster-aware and matched-pair robustness checks.

Reads anonymized six-pattern count vectors under ``reference/``. H1 permutes
whole SUK documents; H2 clusters SUK by document and SST by speech event, with
an SST speaker sensitivity analysis. The Human/GPT-5 check permutes labels
within matched document pairs.

Writes ``h1_document_cluster.tsv``, ``h2_cluster_robustness.tsv`` and
``paired_essay_robustness.tsv`` under ``outputs/supplementary/``.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.stats import binomtest, chi2_contingency, wilcoxon

from compute_statistics import PERMUTATIONS, holm
from pipeline_common import PATTERNS, ROOT, read_tsv, write_tsv

SEED = 20260828
ALPHA = 0.05

SUK_INPUT = ROOT / "reference" / "suk_document_counts.tsv"
SST_EVENT_INPUT = ROOT / "reference" / "sst_event_counts.tsv"
SST_SPEAKER_INPUT = ROOT / "reference" / "sst_speaker_counts.tsv"
ESSAY_INPUT = ROOT / "reference" / "matched_essay_pair_counts.tsv"

H1_OUTPUT = ROOT / "outputs" / "supplementary" / "h1_document_cluster.tsv"
H2_OUTPUT = ROOT / "outputs" / "supplementary" / "h2_cluster_robustness.tsv"
ESSAY_OUTPUT = ROOT / "outputs" / "supplementary" / "paired_essay_robustness.tsv"

SUK_COLUMNS = ("anonymous_cluster_id", "genre", *PATTERNS)
CLUSTER_COLUMNS = ("anonymous_cluster_id", *PATTERNS)
ESSAY_COLUMNS = ("anonymous_pair_id", "condition", *PATTERNS)

GENRES = ("suk-literary", "suk-publicistic", "suk-professional")
CANONICAL_COUNTS = {
    "suk-literary": (112, 8, 6, 4, 4, 28),
    "suk-publicistic": (2035, 193, 102, 51, 46, 410),
    "suk-professional": (831, 50, 46, 17, 20, 141),
    "sst": (108, 18, 16, 4, 4, 18),
    "human": (1237, 109, 132, 11, 37, 145),
    "gpt5": (2902, 125, 45, 5, 25, 146),
}
CANONICAL_CLUSTER_COUNTS = {
    "suk-literary": 54,
    "suk-publicistic": 845,
    "suk-professional": 250,
    "sst-event": 83,
    "sst-speaker": 91,
}

H1_COLUMNS = (
    "test", "scope", "instances", "clusters", "clusters_literary",
    "clusters_publicistic", "clusters_professional", "statistic_name",
    "statistic", "df", "asymptotic_p", "min_expected", "cells_under_5",
    "permutations", "seed", "permutation_p", "conclusion",
)
H2_COLUMNS = (
    "analysis", "comparison", "group_a", "group_b", "cluster_unit_a",
    "cluster_unit_b", "n_a", "n_b", "clusters_a", "clusters_b",
    "statistic_name", "statistic", "df", "asymptotic_p", "min_expected",
    "cells_under_5", "permutations", "seed_base", "rng_seed",
    "permutation_p", "p_adjusted", "significant", "notes",
)
ESSAY_OUTPUT_COLUMNS = (
    "test", "unit", "n_used", "statistic_name", "statistic", "df",
    "p_value", "permutations", "seed", "effect_name", "effect_value", "notes",
)

H2_COMPARISONS = (
    ("academic-literary", "suk-professional", "suk-literary"),
    ("journalistic-literary", "suk-publicistic", "suk-literary"),
    ("academic-conversational", "suk-professional", "sst"),
    ("journalistic-conversational", "suk-publicistic", "sst"),
)


def count_vector(row: dict[str, str], source) -> np.ndarray:
    try:
        vector = np.array([int(row[pattern]) for pattern in PATTERNS], dtype=np.int64)
    except ValueError as error:
        raise RuntimeError(f"{source}: non-integer pattern count") from error
    if (vector < 0).any():
        raise RuntimeError(f"{source}: negative pattern count")
    return vector


def require_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected}, found {actual}")


def require_frozen(value: float, expected: str, label: str) -> None:
    actual = f"{value:.6f}"
    if actual != expected:
        raise RuntimeError(f"{label}: expected frozen value {expected}, found {actual}")


def load_suk() -> dict[str, np.ndarray]:
    grouped: dict[str, list[np.ndarray]] = defaultdict(list)
    seen_ids = set()
    for row in read_tsv(SUK_INPUT, SUK_COLUMNS):
        cluster_id = row["anonymous_cluster_id"]
        genre = row["genre"]
        if cluster_id in seen_ids:
            raise RuntimeError(f"{SUK_INPUT}: duplicate cluster ID {cluster_id}")
        if genre not in GENRES:
            raise RuntimeError(f"{SUK_INPUT}: unexpected genre {genre}")
        seen_ids.add(cluster_id)
        grouped[genre].append(count_vector(row, SUK_INPUT))

    matrices = {genre: np.vstack(grouped[genre]) for genre in GENRES}
    for genre, matrix in matrices.items():
        require_equal(len(matrix), CANONICAL_CLUSTER_COUNTS[genre], f"{genre} clusters")
        require_equal(tuple(matrix.sum(axis=0)), CANONICAL_COUNTS[genre], f"{genre} counts")
    require_equal(sum(map(len, matrices.values())), 1149, "SUK document count")
    return matrices


def load_sst(path, unit: str) -> np.ndarray:
    rows = read_tsv(path, CLUSTER_COLUMNS)
    ids = [row["anonymous_cluster_id"] for row in rows]
    require_equal(len(ids), len(set(ids)), f"{unit} unique cluster IDs")
    matrix = np.vstack([count_vector(row, path) for row in rows])
    require_equal(len(matrix), CANONICAL_CLUSTER_COUNTS[unit], f"{unit} clusters")
    require_equal(tuple(matrix.sum(axis=0)), CANONICAL_COUNTS["sst"], f"{unit} counts")
    return matrix


def pearson_chi2(table: np.ndarray) -> float:
    table = table[:, table.sum(axis=0) > 0]
    expected = table.sum(axis=1, keepdims=True) * table.sum(axis=0, keepdims=True) / table.sum()
    return float(((table - expected) ** 2 / expected).sum())


def cluster_permutation_p(
    matrix_a: np.ndarray, matrix_b: np.ndarray, observed: float, rng: np.random.Generator
) -> float:
    pooled = np.vstack((matrix_a, matrix_b))
    cut = len(matrix_a)
    extreme = 0
    for _ in range(PERMUTATIONS):
        shuffled = pooled[rng.permutation(len(pooled))]
        table = np.vstack((shuffled[:cut].sum(axis=0), shuffled[cut:].sum(axis=0)))
        extreme += pearson_chi2(table) >= observed
    return (extreme + 1) / (PERMUTATIONS + 1)


def h1_document_test(suk: dict[str, np.ndarray]) -> None:
    matrix = np.vstack([suk[genre] for genre in GENRES])
    sizes = [len(suk[genre]) for genre in GENRES]
    cut_one, cut_two = sizes[0], sizes[0] + sizes[1]
    table = np.vstack([suk[genre].sum(axis=0) for genre in GENRES])
    chi2, asymptotic_p, degrees, expected = chi2_contingency(table, correction=False)
    if not np.isclose(chi2, pearson_chi2(table)):
        raise RuntimeError("H1: chi-square implementations disagree")

    rng = np.random.default_rng(SEED)
    extreme = 0
    for _ in range(PERMUTATIONS):
        shuffled = matrix[rng.permutation(len(matrix))]
        permuted = np.vstack((
            shuffled[:cut_one].sum(axis=0),
            shuffled[cut_one:cut_two].sum(axis=0),
            shuffled[cut_two:].sum(axis=0),
        ))
        extreme += pearson_chi2(permuted) >= chi2
    permutation_p = (extreme + 1) / (PERMUTATIONS + 1)
    require_frozen(chi2, "13.765731", "H1 chi-square")
    require_frozen(permutation_p, "0.250037", "H1 document permutation p")

    write_tsv(H1_OUTPUT, H1_COLUMNS, [{
        "test": "Pearson 3 x 6 document-label permutation",
        "scope": "SUK written genres",
        "instances": int(table.sum()),
        "clusters": len(matrix),
        "clusters_literary": sizes[0],
        "clusters_publicistic": sizes[1],
        "clusters_professional": sizes[2],
        "statistic_name": "pearson_chi_square",
        "statistic": f"{chi2:.6f}",
        "df": degrees,
        "asymptotic_p": f"{asymptotic_p:.6f}",
        "min_expected": f"{expected.min():.2f}",
        "cells_under_5": int((expected < 5).sum()),
        "permutations": PERMUTATIONS,
        "seed": SEED,
        "permutation_p": f"{permutation_p:.6f}",
        "conclusion": "H1 remains unsupported",
    }])


def h2_family(
    suk: dict[str, np.ndarray], sst: np.ndarray, sst_unit: str
) -> list[dict[str, object]]:
    matrices = dict(suk)
    matrices["sst"] = sst
    rows = []
    for index, (comparison, group_a, group_b) in enumerate(H2_COMPARISONS):
        matrix_a, matrix_b = matrices[group_a], matrices[group_b]
        table = np.vstack((matrix_a.sum(axis=0), matrix_b.sum(axis=0)))
        chi2, asymptotic_p, degrees, expected = chi2_contingency(table, correction=False)
        if not np.isclose(chi2, pearson_chi2(table)):
            raise RuntimeError(f"{comparison}: chi-square implementations disagree")
        rng_seed = SEED + 100 + index
        permutation_p = cluster_permutation_p(
            matrix_a, matrix_b, chi2, np.random.default_rng(rng_seed)
        )
        rows.append({
            "comparison": comparison,
            "group_a": group_a,
            "group_b": group_b,
            "cluster_unit_a": "SUK document",
            "cluster_unit_b": "SUK document" if group_b != "sst" else sst_unit,
            "n_a": int(table[0].sum()),
            "n_b": int(table[1].sum()),
            "clusters_a": len(matrix_a),
            "clusters_b": len(matrix_b),
            "statistic_name": "pearson_chi_square",
            "statistic": f"{chi2:.6f}",
            "df": degrees,
            "asymptotic_p": f"{asymptotic_p:.6f}",
            "min_expected": f"{expected.min():.2f}",
            "cells_under_5": int((expected < 5).sum()),
            "permutations": PERMUTATIONS,
            "seed_base": SEED,
            "rng_seed": rng_seed,
            "permutation_p_float": permutation_p,
        })
    adjusted = holm([float(row["permutation_p_float"]) for row in rows])
    for row, adjusted_p in zip(rows, adjusted):
        row["p_adjusted_float"] = adjusted_p
    return rows


def h2_cluster_tests(suk: dict[str, np.ndarray], event: np.ndarray, speaker: np.ndarray) -> None:
    primary = h2_family(suk, event, "SST speech event")
    sensitivity_family = h2_family(suk, speaker, "SST speaker")

    expected_primary = (
        ("0.655867", "1.000000"),
        ("0.738913", "1.000000"),
        ("0.002950", "0.008850"),
        ("0.001400", "0.005600"),
    )
    for row, (raw, adjusted) in zip(primary, expected_primary):
        require_frozen(float(row["permutation_p_float"]), raw, f"{row['comparison']} cluster p")
        require_frozen(float(row["p_adjusted_float"]), adjusted, f"{row['comparison']} Holm p")

    expected_sensitivity = {
        "academic-conversational": ("0.002350", "0.007050"),
        "journalistic-conversational": ("0.001500", "0.006000"),
    }
    output = []
    for analysis, rows in (("primary", primary), ("speaker_sensitivity", sensitivity_family)):
        for row in rows:
            if analysis == "speaker_sensitivity" and row["group_b"] != "sst":
                continue
            if analysis == "speaker_sensitivity":
                raw, adjusted = expected_sensitivity[str(row["comparison"])]
                require_frozen(float(row["permutation_p_float"]), raw, f"{row['comparison']} speaker p")
                require_frozen(float(row["p_adjusted_float"]), adjusted, f"{row['comparison']} speaker Holm p")
            raw_p = float(row.pop("permutation_p_float"))
            adjusted_p = float(row.pop("p_adjusted_float"))
            output.append({
                "analysis": analysis,
                **row,
                "permutation_p": f"{raw_p:.6f}",
                "p_adjusted": f"{adjusted_p:.6f}",
                "significant": "yes" if adjusted_p < ALPHA else "no",
                "notes": "Holm adjustment over the same four prespecified H2 comparisons",
            })
    write_tsv(H2_OUTPUT, H2_COLUMNS, output)


def load_essays() -> tuple[list[str], np.ndarray, np.ndarray]:
    pairs: dict[str, dict[str, np.ndarray]] = {}
    order = []
    for row in read_tsv(ESSAY_INPUT, ESSAY_COLUMNS):
        pair_id, condition = row["anonymous_pair_id"], row["condition"]
        if pair_id not in pairs:
            pairs[pair_id] = {}
            order.append(pair_id)
        if condition not in ("human", "gpt5") or condition in pairs[pair_id]:
            raise RuntimeError(f"{ESSAY_INPUT}: invalid or duplicate condition for {pair_id}")
        pairs[pair_id][condition] = count_vector(row, ESSAY_INPUT)
    require_equal(len(order), 691, "essay pair count")
    if any(set(pairs[pair_id]) != {"human", "gpt5"} for pair_id in order):
        raise RuntimeError(f"{ESSAY_INPUT}: every pair must have human and GPT-5 rows")
    human = np.vstack([pairs[pair_id]["human"] for pair_id in order])
    gpt5 = np.vstack([pairs[pair_id]["gpt5"] for pair_id in order])
    require_equal(tuple(human.sum(axis=0)), CANONICAL_COUNTS["human"], "human essay counts")
    require_equal(tuple(gpt5.sum(axis=0)), CANONICAL_COUNTS["gpt5"], "GPT-5 essay counts")
    return order, human, gpt5


def paired_essay_test() -> None:
    pairs, human, gpt5 = load_essays()
    table = np.vstack((human.sum(axis=0), gpt5.sum(axis=0)))
    chi2, asymptotic_p, degrees, _ = chi2_contingency(table, correction=False)
    difference = gpt5 - human
    rng = np.random.default_rng(SEED)
    extreme = 0
    for _ in range(PERMUTATIONS):
        swap = rng.random(len(pairs)) < 0.5
        moved = difference[swap].sum(axis=0)
        permuted = np.vstack((human.sum(axis=0) + moved, gpt5.sum(axis=0) - moved))
        extreme += pearson_chi2(permuted) >= chi2
    permutation_p = (extreme + 1) / (PERMUTATIONS + 1)

    human_n, gpt5_n = human.sum(axis=1), gpt5.sum(axis=1)
    informative = int(((human_n + gpt5_n) > 0).sum())
    complete = (human_n > 0) & (gpt5_n > 0)
    differences = gpt5[complete, 0] / gpt5_n[complete] - human[complete, 0] / human_n[complete]
    gpt5_higher = int((differences > 0).sum())
    human_higher = int((differences < 0).sum())
    ties = int((differences == 0).sum())
    sign = binomtest(gpt5_higher, gpt5_higher + human_higher, 0.5, alternative="two-sided")
    signed_rank = wilcoxon(differences, alternative="two-sided")

    require_equal(informative, 656, "informative essay pairs")
    require_equal(int(complete.sum()), 538, "essay pairs with instances on both sides")
    require_equal((gpt5_higher, human_higher, ties), (249, 112, 177), "paired SVO directions")
    require_frozen(chi2, "236.996527", "paired essay chi-square")
    require_frozen(permutation_p, "0.000050", "paired essay permutation p")
    require_frozen(float(differences.mean()), "0.147580", "mean paired SVO-share difference")

    rows = [
        {
            "test": "paired_label_swap_permutation", "unit": "document pair", "n_used": len(pairs),
            "statistic_name": "pearson_chi_square", "statistic": f"{chi2:.6f}", "df": degrees,
            "p_value": f"{permutation_p:.6f}", "permutations": PERMUTATIONS, "seed": SEED,
            "effect_name": "mean_paired_svo_share_difference_gpt5_minus_human",
            "effect_value": f"{differences.mean():+.4f}",
            "notes": (
                f"Primary robustness result; all six patterns; {informative} pairs contribute at least "
                f"one instance; p is at the 1/{PERMUTATIONS + 1} resolution floor (p < 0.0001)"
            ),
        },
        {
            "test": "sign_test_svo_share", "unit": "document pair", "n_used": int(complete.sum()),
            "statistic_name": "pairs_with_higher_gpt5_share", "statistic": gpt5_higher, "df": "",
            "p_value": f"{sign.pvalue:.3e}", "permutations": "", "seed": "",
            "effect_name": "", "effect_value": "",
            "notes": f"Diagnostic; GPT-5 higher={gpt5_higher}, human higher={human_higher}, tied={ties}",
        },
        {
            "test": "wilcoxon_signed_rank_svo_share", "unit": "document pair",
            "n_used": int(complete.sum()), "statistic_name": "W",
            "statistic": f"{signed_rank.statistic:.1f}", "df": "",
            "p_value": f"{signed_rank.pvalue:.3e}", "permutations": "", "seed": "",
            "effect_name": "", "effect_value": "",
            "notes": f"Diagnostic; zeros dropped; {gpt5_higher + human_higher} untied pairs",
        },
        {
            "test": "pooled_chi_square_main_analysis", "unit": "instance", "n_used": int(table.sum()),
            "statistic_name": "pearson_chi_square", "statistic": f"{chi2:.6f}", "df": degrees,
            "p_value": f"{asymptotic_p:.3e}", "permutations": "", "seed": "",
            "effect_name": "", "effect_value": "",
            "notes": "Reference row for the unchanged unpaired main analysis",
        },
    ]
    write_tsv(ESSAY_OUTPUT, ESSAY_OUTPUT_COLUMNS, rows)


def main() -> None:
    suk = load_suk()
    event = load_sst(SST_EVENT_INPUT, "sst-event")
    speaker = load_sst(SST_SPEAKER_INPUT, "sst-speaker")
    h1_document_test(suk)
    h2_cluster_tests(suk, event, speaker)
    paired_essay_test()
    print(f"Wrote {H1_OUTPUT.relative_to(ROOT)}")
    print(f"Wrote {H2_OUTPUT.relative_to(ROOT)}")
    print(f"Wrote {ESSAY_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
