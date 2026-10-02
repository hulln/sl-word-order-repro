# Supplementary analyses

These outputs are robustness checks on the main analysis. Exact statistics and
p-values are recorded in the TSV files rather than repeated here.

| Output | What it represents |
|---|---|
| `manual_subset_h2.tsv` | The four prespecified H2 comparisons on the manually checked SUK syntax subset, with SST as the conversational source. |
| `h1_document_cluster.tsv` | H1 with whole SUK documents as the permutation unit. |
| `h2_cluster_robustness.tsv` | The four H2 comparisons with SUK documents and SST speech events as the primary clustering units; SST speaker clustering is included as a sensitivity check. |
| `paired_essay_robustness.tsv` | The Human/GPT-5 comparison using within-pair label swaps across matched essays. Sign and Wilcoxon rows are diagnostics. |
| `broad_argument_query.tsv` | Sensitivity query `upos=VERB >nsubj _ >obj _` on canonical UD 2.18 SSJ and SST. These are subject × object **instance counts**, not distinct STARK tree-type counts. The file includes all six orders, proportions, entropy and the strict WALS `>2×` dominance decision. |

All permutation tests use 20,000 permutations and preserve all six word-order
categories. The manual-subset comparisons use independent seeds 20260814–20260817.
The cluster-aware and matched-pair checks use the fixed base seed 20260828; the
H2 file also records the exact derived RNG seed for each comparison. Holm
adjustment is applied over the same four prespecified H2 comparisons.

The scripts are `scripts/supplementary_manual_subset.py`,
`scripts/supplementary_robustness.py` and
`scripts/supplementary_broad_query.py`. The first two scripts' anonymous
numerical inputs are in `reference/` and are documented in
`reference/README.md`; the broad-query script reads the canonical prepared SSJ
and SST CoNLL-U files directly and checks their pinned hashes.

## Exact-text repetition sensitivity

[Procedure, results, hashes and rerun commands](repetition_sensitivity.md)
document the completed four-corpus check. H1 and H2 are outside its scope.

| File | Evidence |
|---|---|
| `dedup_sensitivity.tsv` | All four before/after six-order distributions, sentence and instance counts, natural-log entropy and base-2 JSD distance. |
| `dedup_sensitivity.log` | Preserved structured production log, including 44 descriptive checks (42 preserved; two ParlaMint rankings reversed). |
| `dedup_run.stdout.log` | Unedited dedup stdout/stderr capture. |
| `parlamint_duplicate_audit.txt` | Explanatory audit; exact reconciliation and production code/input hashes. |
| `parlamint_duplicate_examples.tsv.gz` | Lossless complete TSV of 68,984 repeated text types, including zero-instance types. |
| `parlamint_audit_run.stdout.log` | Unedited focused audit stdout/stderr capture. |
| `parlamint_duplicate_manual_check.md` | Researcher's targeted manual spot check, documented separately from automated evidence. |
| `repetition_sensitivity.sha256` | Hashes of distributed production scripts, evidence and manual note; check from repository root. |

Identical parliamentary texts can recur across different segments and sessions.
The sensitivity count does not label these as corpus errors or replace the
primary results. Server paths in the preserved logs record the actual run;
portable commands pass explicit CLI paths. No corpus files are included.
