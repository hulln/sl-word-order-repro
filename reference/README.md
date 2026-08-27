# Verified reference caches

Reference files support an explicitly requested lightweight reproduction. They
are analytical evidence, not raw/source corpora and not substitutes disguised
as full extraction.

`word_order_counts.tsv` contains 10 corpora × 6 patterns. Every row comes from
counts for which the thesis STARK query and the independent direct CoNLL-U
implementation agreed exactly. It covers the large JANES, Wikipedia,
ParlaMint-SI and KDSP inputs plus the non-redistributed Human/GPT-5 essay pair.

`ner_word_order_counts.tsv` contains the historical six-pattern NER splits for
JANES-News and the Human/GPT-5 essays, whose prepared CoNLL-U is unavailable in
this package. Entity status is based on the argument head token: case-normalized
`NER=B-*` or `NER=I-*` is `entity`; `O` or absent is `common`.

The word-order cache is consumed only with `--use-reference-cache`. The output
records `verified_reference_stark_direct_exact`. The NER cache is likewise
opt-in and records `verified_reference_counts`. Corpora present in `prepared/`
are always reanalysed instead of being replaced by cached rows.

Source/generation provenance for the thesis essay pair remains unresolved; the
cache preserves only verified aggregate counts and does not imply that the raw
essays are publicly available.
