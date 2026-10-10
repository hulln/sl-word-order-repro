#!/usr/bin/env python3
"""Cluster-bootstrap 95 % intervals for SVO share and entropy in the four H2 groups.

Groups and resampling units:
  suk-professional, suk-publicistic, suk-literary   -> SUK document
  sst                                               -> SST speech event

Inputs (read only, from the sl-word-order-repro package):
  reference/suk_document_counts.tsv   six-pattern counts per SUK document
  reference/sst_event_counts.tsv      six-pattern counts per SST speech event
  outputs/data/word_order_summary.tsv canonical counts (used only as a check)

Procedure: before resampling, the summed cluster counts must reproduce the
canonical counts exactly, otherwise the script stops. For each group, in the
fixed order below, each replicate draws as many clusters as the group has,
with replacement, sums their counts and computes the SVO share and the
Shannon entropy (natural log). The interval is the 2.5th and 97.5th
percentile of the replicates. One random generator with a fixed seed is used
for all groups, so the output is identical on every run.

The point estimates are those of the full sample, not bootstrap means.
Overlapping intervals are not a significance test.

Output: outputs/supplementary/h2_cluster_bootstrap.tsv
"""

import argparse
import csv
from pathlib import Path

import numpy as np

PATTERNS = ["SVO", "SOV", "VSO", "VOS", "OSV", "OVS"]
SEED = 20261001
REPLICATES = 20000
# Fixed group order; also the order of the H2 table in the thesis.
GROUPS = [
    ("suk-professional", "document"),
    ("suk-publicistic", "document"),
    ("suk-literary", "document"),
    ("sst", "speech event"),
]


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def entropy(counts):
    total = counts.sum()
    shares = counts[counts > 0] / total
    return float(-(shares * np.log(shares)).sum())


def load_clusters(repo):
    """Return {group: array of shape (clusters, 6)}."""
    clusters = {group: [] for group, _ in GROUPS}
    for row in read_tsv(repo / "reference" / "suk_document_counts.tsv"):
        clusters[row["genre"]].append([int(row[p]) for p in PATTERNS])
    for row in read_tsv(repo / "reference" / "sst_event_counts.tsv"):
        clusters["sst"].append([int(row[p]) for p in PATTERNS])
    return {group: np.array(rows, dtype=np.int64) for group, rows in clusters.items()}


def check_against_canonical(repo, clusters):
    summary = {row["corpus_id"]: row for row in read_tsv(repo / "outputs" / "data" / "word_order_summary.tsv")}
    for group, _ in GROUPS:
        summed = clusters[group].sum(axis=0).tolist()
        canonical = [int(summary[group][f"{p}_n"]) for p in PATTERNS]
        if summed != canonical:
            raise SystemExit(f"{group}: cluster counts {summed} != canonical {canonical}")
        if (clusters[group].sum(axis=1) == 0).any():
            raise SystemExit(f"{group}: contains an empty cluster")
        if abs(entropy(clusters[group].sum(axis=0)) - float(summary[group]["entropy_nat"])) > 5e-7:
            raise SystemExit(f"{group}: entropy differs from the canonical value")

    # Cluster counts must match the frozen cluster-level permutation checks.
    h1 = read_tsv(repo / "outputs" / "supplementary" / "h1_document_cluster.tsv")[0]
    expected = {"suk-literary": int(h1["clusters_literary"]),
                "suk-publicistic": int(h1["clusters_publicistic"]),
                "suk-professional": int(h1["clusters_professional"])}
    h2 = read_tsv(repo / "outputs" / "supplementary" / "h2_cluster_robustness.tsv")
    event_counts = {int(row["clusters_b"]) for row in h2 if row["group_b"] == "sst"}
    for group, n in expected.items():
        if len(clusters[group]) != n:
            raise SystemExit(f"{group}: {len(clusters[group])} documents, expected {n}")
    if len(clusters["sst"]) not in event_counts:
        raise SystemExit(f"sst: {len(clusters['sst'])} events not among {sorted(event_counts)}")


def bootstrap(counts, rng):
    m = len(counts)
    svo = np.empty(REPLICATES)
    ent = np.empty(REPLICATES)
    for b in range(REPLICATES):
        pick = rng.integers(0, m, size=m)
        total = counts[pick].sum(axis=0)
        svo[b] = total[0] / total.sum()
        ent[b] = entropy(total)
    return np.percentile(svo, [2.5, 97.5]), np.percentile(ent, [2.5, 97.5])


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=here.parent,
                        help="root of the sl-word-order-repro package")
    parser.add_argument("--out", type=Path,
                        default=here.parent / "outputs" / "supplementary" / "h2_cluster_bootstrap.tsv")
    args = parser.parse_args()

    clusters = load_clusters(args.repo)
    check_against_canonical(args.repo, clusters)

    rng = np.random.default_rng(SEED)
    rows = []
    for group, unit in GROUPS:
        counts = clusters[group]
        total = counts.sum(axis=0)
        (svo_lo, svo_hi), (ent_lo, ent_hi) = bootstrap(counts, rng)
        rows.append({
            "group": group, "n": int(total.sum()), "n_clusters": len(counts), "cluster_unit": unit,
            "svo": f"{total[0] / total.sum():.6f}", "svo_lo": f"{svo_lo:.6f}", "svo_hi": f"{svo_hi:.6f}",
            "entropy": f"{entropy(total):.6f}", "entropy_lo": f"{ent_lo:.6f}",
            "entropy_hi": f"{ent_hi:.6f}", "replicates": REPLICATES, "seed": SEED,
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
