# Reference numerical inputs

This directory contains verified aggregate fallback counts for unavailable
analysed corpora and anonymized document, event, speaker and pair count vectors
for supplementary robustness analyses. It does not contain reconstructed
corpora. For the aggregate tables, “verified” means the six word-order counts
were obtained independently with STARK and the direct CoNLL-U extractor and
agreed exactly.

- `word_order_counts.tsv` supplies 10 corpora × 6 patterns when
  `--use-reference-cache` is requested.
- `ner_word_order_counts.tsv` supplies the NER splits for JANES-News and the
  human/GPT-5 essay pair when their prepared files are absent.
- `manual_subset_counts.tsv` supplies the SUK side of the separate supplementary
  H2 check.
- `suk_document_counts.tsv` contains anonymous six-pattern vectors for the 1,149
  SUK documents that contribute at least one extracted instance.
- `sst_event_counts.tsv` and `sst_speaker_counts.tsv` contain the same canonical
  168 SST instances grouped into 83 speech events and 91 speakers, respectively.
- `matched_essay_pair_counts.tsv` contains two six-pattern rows for each of all
  691 matched essay pairs, including zero-count sides.

The last four tables are the minimal inputs for
`scripts/supplementary_robustness.py`. They contain integer counts and grouping
labels only: no sentences, tokens, corpus text, original document names, event
IDs, speaker IDs, or essay IDs. Source groups were sorted exactly as in the
frozen analysis and then assigned sequential anonymous IDs. The essay table
preserves the frozen pair-list order. This deterministic replacement removes
identifiers without changing any count vector or Monte Carlo stream.

## Robustness-input provenance

The public tables were derived from the final extracted-instance summaries in
the frozen analysis. The following SHA-256 values identify those authoritative
source artifacts; they are provenance records and are not needed to run this
repository:

| Public input | Frozen source artifact(s) | Source SHA-256 |
|---|---|---|
| `suk_document_counts.tsv` | `h2_cluster_counts.tsv` | `adf218923a6128ec892f216b5d10273e4149d540de1be360aa9c049a585e6b2b` |
| `sst_event_counts.tsv` | `h2_cluster_counts.tsv` | `adf218923a6128ec892f216b5d10273e4149d540de1be360aa9c049a585e6b2b` |
| `sst_speaker_counts.tsv` | `svo_instances_sst.tsv`; `sst_sentence_speaker.tsv` | `1922fb357ed8e9620c131d6d5b9e95ae2696c6c8479b1671d0eb65ccecb19fa0`; `a5d657c9d96c7bda8d177979df3040ba34c959b84d3ce1127ce7bf7eafa47c2d` |
| `matched_essay_pair_counts.tsv` | `paired_essay_document_counts.tsv` | `7c9163568817e89eec0b726bb269158376239c188bb0330aba93f66a8c9d4aab` |

The reproduction script hard-asserts every canonical six-pattern aggregate,
the cluster/pair counts, and the frozen results before writing its outputs.

If a prepared corpus is present, it is analysed instead of using stored counts.
Output rows identify stored results with `verified_reference_*` statuses.

For the essay pair, GPT-5 source and generation are documented by AI-GenT 1.0.
The human syntactic annotator remains undocumented. The derived annotated Human
subset is not distributed in this repository and must be obtained or prepared
from the source data.
