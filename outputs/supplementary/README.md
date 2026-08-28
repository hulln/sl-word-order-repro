# Supplementary analyses

These outputs are robustness checks on the main analysis. Exact statistics and
p-values are recorded in the TSV files rather than repeated here.

| Output | What it represents |
|---|---|
| `manual_subset_h2.tsv` | The four prespecified H2 comparisons on the manually checked SUK syntax subset, with SST as the conversational source. |
| `h1_document_cluster.tsv` | H1 with whole SUK documents as the permutation unit. |
| `h2_cluster_robustness.tsv` | The four H2 comparisons with SUK documents and SST speech events as the primary clustering units; SST speaker clustering is included as a sensitivity check. |
| `paired_essay_robustness.tsv` | The Human/GPT-5 comparison using within-pair label swaps across matched essays. Sign and Wilcoxon rows are diagnostics. |

All permutation tests use 20,000 permutations and preserve all six word-order
categories. The manual-subset comparisons use independent seeds 20260814–20260817.
The cluster-aware and matched-pair checks use the fixed base seed 20260828; the
H2 file also records the exact derived RNG seed for each comparison. Holm
adjustment is applied over the same four prespecified H2 comparisons.

The scripts are `scripts/supplementary_manual_subset.py` and
`scripts/supplementary_robustness.py`. Their anonymous numerical inputs are in
`reference/` and are documented in `reference/README.md`.
