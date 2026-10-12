# Parser sensitivity on SSJ (thesis Section 4.2.4)

This check measures how the automatic syntactic annotation affects the
word-order extraction. The same 13,435 SSJ sentences are compared in two
annotations: the manually checked reference from the public UD 2.18 release
(`prepared/ssj.conllu`) and a saved automatic parse produced with
CLASSLA-Stanza 2.2.1. The automatic parse kept the reference sentence
boundaries and tokenisation and re-assigned morphology and syntax without
seeing the reference labels, so the check isolates the effect of automatic
tagging and parsing, not of segmentation.

**CLASSLA-Stanza was not rerun for the UD 2.18 update.** The automatic parse
is the one saved from the historical run; only the reference side was moved
to UD 2.18. Because 2,024 of the 13,435 sentence IDs were renamed in UD 2.18
(rule `elexiswsd<n>.<old identifier>`), the comparison first harmonised the
sentence IDs of a copy of the automatic parse by sentence order, verifying
that token IDs and token forms are identical in every sentence; 11,411 IDs
were already identical.

## Procedure

Both annotations go through the same extraction as the main analysis: a
`VERB` with an `nsubj` and an `obj` dependant, every subject × object pair of
the same verb being one instance. The canonical query requires `NOUN`
argument heads; the supplementary variant allows `NOUN` or `PROPN`.

Instances are grouped by `(sent_id, verb_id)` and matched one-to-one. Exact
`(sent_id, verb_id, subject_id, object_id)` matches are removed first and count
as *same pattern*. Among the remaining instances, a pair with the same two
argument tokens but swapped subject/object roles counts as *changed pattern*
only if the swapped match is unique in both directions. Both instances are
then removed. This preserves the identity of the tokens while allowing their
roles, and hence their word-order pattern, to change.

For the remaining instances, any shared argument token creates an overlap
candidate, irrespective of its role. A pair unique in both directions is
removed but marked *unclear*, since partial overlap is insufficient for
reliable alignment. If overlaps remain without such a unique pair, all
remaining candidates for that sentence and verb are kept together in one
*unclear* record. When no overlaps remain, unmatched reference instances are
*gold-only* and unmatched automatic instances are *auto-only*.

Only *same pattern* and *changed pattern* pairs enter the aligned denominator.
*Unclear* records are excluded; their candidate instances are counted
separately on each side. Strict retention uses all reference instances as its
denominator and counts only *same pattern* instances as retained.

## Published files

| File | Contents |
|---|---|
| `parser_sensitivity_distribution.tsv` | Six-pattern counts and percentages of the reference and automatic extraction, canonical `NOUN` query. |
| `parser_sensitivity_distribution_noun_propn.tsv` | The same for the `NOUN\|PROPN` variant. |
| `parser_sensitivity_gold_auto_matrix.tsv` | Reference × automatic pattern matrix over the aligned instances, `NOUN` query. |
| `parser_sensitivity_gold_auto_matrix_noun_propn.tsv` | The same for the `NOUN\|PROPN` variant. |
| `parser_sensitivity_discrepancy_reasons.tsv` | Multi-label reason counts for the one-sided (gold-only and auto-only) instances of the `NOUN` query. |
| `parser_sensitivity_summary.json` | Both variants' aggregate summaries, input checksums and run metadata. |

All published files are aggregates; they contain no sentences, tokens,
sentence identifiers or corpus text.

## Results

Canonical `NOUN` query: the reference annotation yields 1,969 instances, the
automatic one 1,882. Of the 1,788 reliably aligned instances, 1,780 (99.55 %)
keep the same word-order pattern; all eight changes are OVS → SVO, where the
automatic parse swapped the `nsubj` and `obj` relations. Of the 1,969
reference instances, 189 (9.60 %) are not retained with the same arguments
and pattern: 8 changed pattern, 177 were not captured by the automatic query
and 4 had no unambiguous alignment. This 9.60 % is a strict retention
criterion, not a direct parser error rate. In the full distributions the SVO
share rises from 71.41 % to 73.27 %, entropy (natural log) falls from 0.972
to 0.932, and the Jensen–Shannon distance is 0.025. The reason summary shows
that the one-sided instances stem from differing dependency relations,
attachment or UPOS, not from missing sentences or tokens.

`NOUN|PROPN` variant: 2,542 reference and 2,445 automatic instances; 2,310
aligned, of which 2,300 (99.57 %) keep the same pattern (10 × OVS → SVO);
9.52 % of reference instances are not retained; the Jensen–Shannon distance
is 0.019. Allowing proper-noun heads therefore barely changes the picture.

## Verification versus recomputation

`scripts/test_parser_sensitivity.py` (standard library only) distinguishes
three levels:

1. **Internal verification of the published aggregates** — totals,
   denominators, retention identities, percentages, entropies, the
   Jensen–Shannon distance and the agreement matrices are recomputed from the
   published tables and compared against `parser_sensitivity_summary.json`.
   Fully supported by this repository.
2. **Cross-checking against independently published counts** — the reference
   side of both variants is compared with the canonical public tables
   (`outputs/data/word_order_counts.tsv` and `outputs/data/ner_word_order.tsv`)
   and with the pinned SSJ entry in `config/corpora.tsv`. Fully supported by
   this repository; the reference file itself can be rebuilt from the public
   UD 2.18 release and checked against its pinned SHA-256.
3. **Re-running the original comparison** — requires the saved CLASSLA-Stanza
   2.2.1 parse, which is **not distributed** in this repository and, because
   the exact historical model resources cannot be reconstructed with
   certainty, cannot be regenerated bit-identically from public sources. The
   script optionally verifies the SHA-256 of a locally available copy
   (`--auto PATH`), but the comparison itself is not reproducible from public
   files, and the verification script does not reproduce it.

The published aggregates are therefore *verifiable* and *cross-checkable*,
but the instance-level comparison behind them is not independently
*recomputable* from this package.

## Provenance and checksums

| Item | Value |
|---|---|
| Reference | `prepared/ssj.conllu`, UD Slovenian-SSJ 2.18, train+dev+test merged, 13,435 sentences |
| Reference SHA-256 | `a11385ea9184c2dfaac9b16416c303935197e553512810afe3e94114005532d1` |
| Automatic parse | CLASSLA-Stanza 2.2.1, saved historical parse (not distributed) |
| Automatic parse SHA-256 | `40106516db9e5de0c4b64b5ec7fa9daf02f28d0bed091baab91697d6398ca498` |
| Harmonised-ID copy SHA-256 | `d1d453d6dd6548a6afee77f529f54f1f4c92a49f482d1c698c7d33b8ca1d7b34` |
| Run date / random seed | 2026-10-12 / 20260809 |

The TSV files are byte-identical copies of the verified analysis outputs; the
summary JSON restates the run manifest with the absolute local reference path
replaced by `prepared/ssj.conllu`, private analysis paths and script hashes
omitted, and Slovenian descriptive strings restated in English (see its
`provenance` field). Sentence-level outputs of the analysis (alignment
listings, instance tables, manual-review material) are not published.

**Attribution.** The reference annotations come from the *UD Slovenian-SSJ*
treebank, release 2.18 (Universal Dependencies,
<https://github.com/UniversalDependencies/UD_Slovenian-SSJ/tree/r2.18>,
CC BY-SA 4.0; Kaja Dobrovoljc and Nikola Ljubešić, 2022: *Extending the SSJ
Universal Dependencies Treebank for Slovenian: Was It Worth It?*, LAW-XVI @
LREC 2022). The published tables contain aggregate counts only and reproduce
no corpus text.
