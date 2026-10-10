#!/usr/bin/env python3
"""Cramér's V for the selected chi-square comparisons reported in the thesis.

V = sqrt(chi2 / (n * (min(rows, columns) - 1)))

The chi-square values are the stored Pearson statistics in
outputs/data/statistical_tests.tsv (the same statistic the permutation tests
use). As a check, each one is recomputed from the canonical counts in
outputs/data/word_order_summary.tsv; the script stops if they differ.

Only these comparisons are included (thesis order):
  H1 omnibus, the six genre pairs of the pairwise table, SSJ-SST, human-GPT-5.
No other test gets a V, and no verbal size labels are attached.

Output: outputs/supplementary/cramers_v_selected.tsv
"""

import argparse
import csv
import math
from pathlib import Path

PATTERNS = ["SVO", "SOV", "VSO", "VOS", "OSV", "OVS"]

# (label, thesis location, test_family, test_id, groups)
SELECTED = [
    ("H1 omnibus: SUK three genre groups", "§4.1.1 text",
     "h1_omnibus", "suk_three_genres__permutation_chi_square",
     ["suk-literary", "suk-publicistic", "suk-professional"]),
    ("strokovno–publicistično", "tab:zanri-pari", "selected_validation",
     "suk-professional__suk-publicistic__permutation_chi_square", ["suk-professional", "suk-publicistic"]),
    ("strokovno–leposlovno", "tab:zanri-pari", "h2_prespecified",
     "suk-professional__suk-literary__permutation_chi_square", ["suk-professional", "suk-literary"]),
    ("strokovno–pogovorno", "tab:zanri-pari", "h2_prespecified",
     "suk-professional__sst__permutation_chi_square", ["suk-professional", "sst"]),
    ("publicistično–leposlovno", "tab:zanri-pari", "h2_prespecified",
     "suk-publicistic__suk-literary__permutation_chi_square", ["suk-publicistic", "suk-literary"]),
    ("publicistično–pogovorno", "tab:zanri-pari", "h2_prespecified",
     "suk-publicistic__sst__permutation_chi_square", ["suk-publicistic", "sst"]),
    ("leposlovno–pogovorno", "tab:zanri-pari", "selected_validation",
     "suk-literary__sst__permutation_chi_square", ["suk-literary", "sst"]),
    ("SSJ–SST", "§4.1.2 text", "selected_validation",
     "ssj__sst__permutation_chi_square", ["ssj", "sst"]),
    ("human essays–GPT-5 essays", "§4.1.3 text", "selected_validation",
     "human-essays__gpt5-essays__permutation_chi_square", ["human-essays", "gpt5-essays"]),
]


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def pearson_chi_square(table):
    """Pearson chi-square of a groups x patterns table; empty columns are dropped."""
    columns = [list(col) for col in zip(*table) if sum(col) > 0]
    n = sum(sum(col) for col in columns)
    row_totals = [sum(col[i] for col in columns) for i in range(len(table))]
    chi2 = 0.0
    for col in columns:
        col_total = sum(col)
        for i, observed in enumerate(col):
            expected = row_totals[i] * col_total / n
            chi2 += (observed - expected) ** 2 / expected
    return chi2, n, len(table), len(columns)


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=here.parent,
                        help="root of the sl-word-order-repro package")
    parser.add_argument("--out", type=Path,
                        default=here.parent / "outputs" / "supplementary" / "cramers_v_selected.tsv")
    args = parser.parse_args()

    tests = {(r["test_family"], r["test_id"]): r
             for r in read_tsv(args.repo / "outputs" / "data" / "statistical_tests.tsv")}
    summary = {r["corpus_id"]: r for r in read_tsv(args.repo / "outputs" / "data" / "word_order_summary.tsv")}

    rows = []
    for label, location, family, test_id, groups in SELECTED:
        source = tests[(family, test_id)]
        stored = float(source["statistic"])
        table = [[int(summary[g][f"{p}_n"]) for p in PATTERNS] for g in groups]
        recomputed, n, n_rows, n_cols = pearson_chi_square(table)
        if abs(recomputed - stored) > 1e-6 * max(1.0, stored):
            raise SystemExit(f"{label}: stored chi2 {stored} != recomputed {recomputed}")
        k = min(n_rows, n_cols) - 1
        rows.append({
            "comparison": label, "thesis_location": location, "groups": ",".join(groups),
            "n": n, "rows": n_rows, "columns": n_cols, "chi_square": f"{stored:.6f}",
            "cramers_v": f"{math.sqrt(stored / (n * k)):.4f}",
            "source_test_family": family, "source_test_id": test_id,
            "source_p_value": source["p_value"], "source_p_kind": source["statistic_name"],
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
