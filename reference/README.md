# Verified stored counts

For some corpora the exact analysed file is not distributed here. This directory
stores aggregate results, not reconstructed corpora. “Verified” means the six
word-order counts were obtained independently with STARK and the direct
CoNLL-U extractor and agreed exactly.

- `word_order_counts.tsv` supplies 10 corpora × 6 patterns when
  `--use-reference-cache` is requested.
- `ner_word_order_counts.tsv` supplies the NER splits for JANES-News and the
  human/GPT-5 essay pair when their prepared files are absent.
- `manual_subset_counts.tsv` supplies the SUK side of the separate supplementary
  H2 check.

If a prepared corpus is present, it is analysed instead of using stored counts.
Output rows identify stored results with `verified_reference_*` statuses.

For the essay pair, GPT-5 source and generation are documented by AI-GenT 1.0.
The human syntactic annotator remains undocumented. The derived annotated Human
subset is not distributed in this repository and must be obtained or prepared
from the source data.
