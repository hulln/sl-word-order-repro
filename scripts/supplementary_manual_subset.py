#!/usr/bin/env python3
"""Supplementary check: the H2 genre comparisons on manually checked syntax.

The main genre analysis uses the whole genre-annotated SUK material, part of
which carries automatically added dependency syntax. This supplementary check
repeats the four H2 comparisons on the subset whose syntax is manually checked,
against the spoken treebank SST.

The three SUK subset distributions are read from ``reference/manual_subset_counts.tsv``:
they come from an analysis that cannot be rerun from this package, because it
needs the SUK composite. The SST distribution is taken from the canonical
``outputs/data/word_order_counts.tsv``, so this check always uses the same SST
release as the main analysis.

The statistical procedure is the canonical one, imported from
``compute_statistics``: a permutation test on Pearson's chi-square with 20,000
reassignments and a fixed seed, followed by Holm adjustment over the four tests.

This is supplementary evidence, not part of the main 18-corpus analysis.
"""

from __future__ import annotations

import csv

import numpy as np

from compute_statistics import PAIR_SEED, PERMUTATIONS, holm, permutation_pair
from pipeline_common import PATTERNS, ROOT, read_tsv, write_tsv

SUBSET = ROOT / "reference" / "manual_subset_counts.tsv"
WORD_COUNTS = ROOT / "outputs" / "data" / "word_order_counts.tsv"
OUTPUT = ROOT / "outputs" / "supplementary" / "manual_subset_h2.tsv"

SUBSET_COLUMNS = ("corpus_id", "corpus", "pattern", "count", "total", "proportion")
OUTPUT_COLUMNS = (
    "comparison", "corpus_a", "corpus_b", "n_a", "n_b",
    "statistic_name", "statistic", "df", "p_value", "p_adjusted",
    "permutations", "seed", "notes",
)

# Order matters: the shared random stream makes the result reproducible only in
# this order. The first two comparisons are the ones H2 predicts.
PAIRS = (
    ("suk-professional-manual", "sst"),
    ("suk-publicistic-manual", "sst"),
    ("suk-professional-manual", "suk-literary-manual"),
    ("suk-publicistic-manual", "suk-literary-manual"),
)


def counts_from(path, columns, wanted):
    rows = read_tsv(path, columns)
    grouped = {}
    for row in rows:
        grouped.setdefault(row["corpus_id"], {})[row["pattern"]] = int(row["count"])
    result = {}
    for corpus_id in wanted:
        if corpus_id not in grouped:
            raise RuntimeError(f"{path}: missing {corpus_id}")
        counts = grouped[corpus_id]
        if set(counts) != set(PATTERNS):
            raise RuntimeError(f"{path}: incomplete pattern set for {corpus_id}")
        result[corpus_id] = np.array([counts[p] for p in PATTERNS], dtype=np.int64)
    return result


def main() -> None:
    matrix = counts_from(SUBSET, SUBSET_COLUMNS, [c for pair in PAIRS for c in pair if c != "sst"])
    word_columns = (
        "corpus_id", "corpus", "pattern", "count", "total", "proportion", "extraction_status"
    )
    matrix.update(counts_from(WORD_COUNTS, word_columns, ["sst"]))

    rng = np.random.default_rng(PAIR_SEED)
    calculated = []
    for corpus_a, corpus_b in PAIRS:
        chi2, pearson_p, permutation_p, degrees, small = permutation_pair(
            matrix[corpus_a], matrix[corpus_b], rng
        )
        calculated.append((corpus_a, corpus_b, chi2, pearson_p, permutation_p, degrees, small))

    adjusted = holm([item[4] for item in calculated])
    rows = []
    for (a, b, chi2, pearson_p, permutation_p, degrees, small), holm_p in zip(calculated, adjusted):
        rows.append({
            "comparison": f"{a}__{b}",
            "corpus_a": a, "corpus_b": b,
            "n_a": int(matrix[a].sum()), "n_b": int(matrix[b].sum()),
            "statistic_name": "pearson_chi_square_with_permutation_p",
            "statistic": f"{chi2:.12g}", "df": degrees,
            "p_value": f"{permutation_p:.12g}", "p_adjusted": f"{holm_p:.12g}",
            "permutations": PERMUTATIONS, "seed": PAIR_SEED,
            "notes": (
                f"supplementary manually checked subset; Pearson asymptotic p={pearson_p:.12g}; "
                f"expected cells under 5={small}"
            ),
        })
    write_tsv(OUTPUT, OUTPUT_COLUMNS, rows)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(rows)} rows)")
    for row in rows:
        print(f"  {row['comparison']:48s} p={float(row['p_value']):.4f}  Holm={float(row['p_adjusted']):.4f}")


if __name__ == "__main__":
    main()
