# Exact-text repetition sensitivity analysis

This supplementary check asks how much the descriptive cross-source S/V/O
comparison depends on repeated identical sentence texts. The primary analysis
continues to count every occurrence. The check covers four selected large or
high-repetition sources: JANES-Tweet, JANES-Wiki, CLASSLA-Wikipedia and
ParlaMint-SI. It introduces no new hypothesis, corpus, parser run, significance
test or deduplication variant. H1 and H2 are outside its scope.

## Definition and validation

Within each corpus separately, retain the first occurrence in the original file
order of each identical sentence identity and omit later occurrences from this
sensitivity count. Identity is the exact content following `# text = `, removing
only the physical line ending, with no trimming, case folding, whitespace or
Unicode normalisation. If that field is absent, identity is the FORM values of
integer-ID tokens joined by one space; multiword-token ranges and empty nodes
are ignored. Empty explicit text is a valid identity. The entire JANES-Tweet
input uses this FORM fallback (19,707,683 sentences); the other three inputs
have zero fallbacks. Sentences without qualifying S/V/O pairs are still included
in the identity index and sentence totals. The reader inherits the canonical
extractor's UTF-8 `errors="ignore"`; exactness refers to that decoded text, and
input bytes are pinned by SHA-256.

The unchanged nested `flush_sentence()` and `classify()` implementation from
`scripts/extract_word_order_direct.py` is reused, rather than maintaining another
matching implementation. It counts every matching NOUN `nsubj` × NOUN `obj`
pair attached directly to the same VERB. Sentence counts and pair counts have
different denominators. Shannon entropy uses natural logarithms. The
`js_distance_base2_pre_post` column is Jensen–Shannon **distance**, the square
root of the base-2 divergence.

The production script first hashes each input and performs ordinary extraction.
Its total and all six order counts must exactly equal the primary summary
before deduplication proceeds. File fingerprints are checked between passes.
An exact SQLite BLOB key preserves identity with a bounded 64 MiB cache and a
temporary disk index. For the ranking checks only these four distributions are
replaced; every other source retains the primary counts. These checks encode
selected descriptive statements, not every thesis claim or qualitative
interpretation. The logs record 44 checks: 42 preserved and two rankings reversed.

## Completed results

Values below are computed from `dedup_sensitivity.tsv`, rounded for display.
“Repeated” is the percentage of all sentence occurrences after their first
identical-text occurrence, not the percentage of S/V/O instances.

| Corpus | Repeated (%) | SVO before (%) | SVO after (%) | OVS before (%) | OVS after (%) | Entropy before | Entropy after |
|---|---:|---:|---:|---:|---:|---:|---:|
| JANES-Tweet | 27.249 | 77.457 | 77.252 | 8.856 | 8.915 | 0.862688 | 0.868615 |
| JANES-Wiki | 39.479 | 72.972 | 72.222 | 9.414 | 9.932 | 0.992483 | 1.005591 |
| CLASSLA-Wikipedia | 19.136 | 76.026 | 75.999 | 14.207 | 14.211 | 0.843517 | 0.844337 |
| ParlaMint-SI | 19.170 | 67.907 | 71.922 | 16.440 | 12.073 | 1.054847 | 0.994274 |

Absolute SVO changes are 0.205, 0.751, 0.027 and 4.015 percentage points,
respectively. The first three sources change slightly; ParlaMint-SI changes more
strongly. Two original rankings are not preserved:

- ParlaMint-SI has the highest OVS share in the original nine-source register
  comparison. After replacing the four distributions, it no longer does.
- ParlaMint-SI has the lowest SVO share among the seven automatically analysed
  register sources in the original comparison. In the sensitivity comparison,
  JANES-Forum has the lowest share instead.

All other encoded directional, ranking and JSD checks are preserved, including
SVO dominance in all 18 sources. This establishes stability only for the encoded
checks under this one procedure; it does not establish stability of all possible
comparisons. Primary result tables and figures are retained as frequency-based
results, and no H1/H2 input, test or interpretation is changed.

## ParlaMint-SI: effect of repeated sentences

The explanatory audit independently extracts every occurrence, including later
copies, and reconciles exactly with the completed deduplication run:

- 3,876,183 sentences; 3,133,122 unique texts retained; 743,061 later identical
  texts omitted; 68,984 repeated text types, including texts with no S/V/O pairs.
- 497,572 S/V/O instances before; 453,811 after; 43,761 omitted.
- OVS: 81,801 → 54,788, a reduction of 27,013 (33.023% of the original OVS).
- SVO: 337,886 → 326,388, a reduction of 11,498 (3.403% of the original SVO).
- No repeated text type had differing S/V/O count vectors. This does not prove
  that every annotation field is identical or correct.
- The top 5/10/20 text types contribute 12.54%/15.98%/19.83% of removed OVS,
  so the reduction extends across many repeated text types.

The audit TSV records the first count vector, actual later-occurrence
contributions, nominal `(occurrences − 1) × first` contributions and vector
frequencies. It is complete, not just a selection of examples; use a CSV-aware
TSV reader because text can contain quoted tabs and quotes.

The separate [manual spot-check record](parlamint_duplicate_manual_check.md)
records the researcher's targeted inspection after the automated audit. The
strongest OVS contributor, “Predlog zakona je v obravnavo zboru predložila vlada
Republike Slovenije.”, has 513 occurrences and two annotated NOUN objects
before the verb, with the NOUN subject after it. Its 512 later copies therefore
contribute 1,024 OVS pairs. One object, *zboru*, is morphologically dative but
labelled `obj`; extraction consistently follows the supplied dependency labels.
The check documents recurrence under distinct identifiers across segments,
dates and sessions. Inspection of high-contributing examples shows many recurring
parliamentary formulations about legislation and allocating speaking turns.
This is a qualitative observation, not a formally measured variable or a
systematic classification of all repeated types.

Identical text recurring in parliamentary material is not by itself evidence of
erroneous corpus records. The sensitivity version is not a “cleaned” or
intrinsically more correct corpus. The supported methodological qualification
is that the frequency of recurring identical formulations can affect aggregate
cross-source S/V/O distributions, especially OVS in this ParlaMint-SI input.

## Provenance and files

Production took place on 2026-10-01 (UTC timestamps in the logs). Both scripts
here are **byte-identical to the production-run scripts**; no later path-only
cleanup or computational change was needed. Their historical server defaults
remain visible; the rerun commands below supply portable explicit paths.

| Component | Production SHA-256 |
|---|---|
| `scripts/dedup_sensitivity.py` | `93a773aa703c340ef0e92b841180b987d87a3a1a3958d7be03def035fe2afd1e` |
| `scripts/inspect_parlamint_duplicates.py` | `4adcba838904e5d42eb6c1b4fde309868bd90ff19365587ad8d66a6bbe273d41` |
| `scripts/extract_word_order_direct.py` | `2276cbbc7317e7d1c11848be2c8c9c4e790df0585653c19e68a059c320a982a3` |
| `config/corpora.tsv` | `ecec27bcbe51e0b0fde355c165269a2e8347c9819daa50f5fff19285c984c4e0` |
| `outputs/data/word_order_summary.tsv` | `6d9fb032ea1469dea4e694beb9b33fe241463674b7cde1fa28d232d3566d7381` |
| `dedup_sensitivity.tsv` | `7e412bd4e93fd14be4097fb896f91858f0e8634b51170da2d1b6fdc27a3f93c9` |

`dedup_sensitivity.log`, `dedup_run.stdout.log` and
`parlamint_audit_run.stdout.log` are retained without editing. The dedup stdout
log equals `nohup: ignoring input\n` followed by the structured dedup log. Raw
logs, the audit report and the results TSV contain historical machine usernames
and absolute server paths; these are provenance, not portable command examples.
They were read and scanned for credential assignments, private-key blocks,
common token prefixes and credential-bearing URLs; no secrets were detected.
No raw log was rewritten or regenerated.

The audit report retains the production script and input hashes, including the
completed dedup TSV hash. `repetition_sensitivity.sha256` verifies the distributed
scripts, preserved outputs and manual note; it is run from the repository root.
The manual note was documented later from the researcher's supplied inspection
and is not part of the automatically generated production evidence.

The complete examples TSV is losslessly distributed as
`parlamint_duplicate_examples.tsv.gz` to avoid storing 22,532,723 uncompressed
bytes in Git. Gzip uses `mtime=0`; no Git LFS is required. Compressed size:
1,870,445 bytes. The uncompressed content SHA-256 is
`7dc9ae1f8372237086a1cfb4d381ea7118bd4e16dbb954004ba3fe3d8e7a60dc`;
compressed SHA-256 is
`23b6a183e429aa3b4d6d0b54cfa54cbe1197c6d8603ab371323c78448de4434b`.

```bash
sha256sum -c outputs/supplementary/repetition_sensitivity.sha256
gzip -cd outputs/supplementary/parlamint_duplicate_examples.tsv.gz | sha256sum
```

## Reproducing the analysis

Python 3.10 or newer and its standard library are sufficient; STARK, a parser
and annotation packages are not needed for this check. Obtain the exact
prepared corpora using the source/access information in `inputs/README.md` and
`prepared/README.md`; stored counts alone cannot reproduce the sentence-level
check. Do not reconstruct unavailable JANES preparations from aggregate counts.

The unchanged dedup CLI expects the historical filenames below in one external
corpus directory, although the public prepared filenames differ:

| Corpus | Expected name in `--corpus-dir` | Public prepared name | SHA-256 |
|---|---|---|---|
| JANES-Tweet | `janes_tweet.conllu` | `prepared/janes-tweet.conllu` | `4a3f1c85f45094941670bf1d1fad7e50dc1fe117b3aa18d7a583ebdf0ca83bb1` |
| JANES-Wiki | `janes.wiki.conllu` | `prepared/janes-wiki.conllu` | `aa398403028feede657d8fb21cb5b4e92e64b10738e650d7345d9d9a838b0e42` |
| CLASSLA-Wikipedia | `classlawiki-sl.conllu` | `prepared/classla-wikipedia.conllu` | `d163fd9647110e6721131f5d204516f2b3f8ca102c61611807da87349b17ec8d` |
| ParlaMint-SI | `parlamint-si.conllu` | `prepared/parlamint.conllu` | `be53ad8a8b28e1f7996ba79de045b1c3516324cd8adbe902ea2500e7d02bd81e` |

Create an external directory of symlinks if starting with the public prepared
layout (this changes paths, not the input bytes). From the repository root:

```bash
repetition_repo="$PWD"
repetition_corpora="$PWD/../repetition-corpora"
mkdir -p "$repetition_corpora"
ln -s "$repetition_repo/prepared/janes-tweet.conllu" "$repetition_corpora/janes_tweet.conllu"
ln -s "$repetition_repo/prepared/janes-wiki.conllu" "$repetition_corpora/janes.wiki.conllu"
ln -s "$repetition_repo/prepared/classla-wikipedia.conllu" "$repetition_corpora/classlawiki-sl.conllu"
ln -s "$repetition_repo/prepared/parlamint.conllu" "$repetition_corpora/parlamint-si.conllu"
```

Alternatively set `repetition_corpora` to an existing external directory with
these four names and hashes. The manifest's historical JANES-Tweet boundary
count is 19,707,684; the check counts blocks with integer-ID tokens and reports
19,707,683, consistent with the completed run and current thesis. The manifest
is preserved as a production reference, not silently edited.

Choose a fresh external run directory on local disk, with room for tens of GB
of scratch storage. Both scripts intentionally reject output/scratch directories
inside the canonical repository or corpus directory. Keep rerun artifacts
separate from the preserved production logs; timestamps and absolute paths will
differ, so a rerun TSV need not be byte-identical even when numeric results agree.

```bash
repetition_run="$PWD/../repetition-run"
mkdir -p "$repetition_run/dedup" "$repetition_run/parlamint-audit" "$repetition_run/scratch"
python3 scripts/dedup_sensitivity.py \
  --repo "$repetition_repo" --corpus-dir "$repetition_corpora" \
  --out-dir "$repetition_run/dedup" --scratch-dir "$repetition_run/scratch" \
  > "$repetition_run/dedup/dedup_run.stdout.log" 2>&1
python3 scripts/inspect_parlamint_duplicates.py \
  --repo "$repetition_repo" --input "$repetition_corpora/parlamint-si.conllu" \
  --dedup-results "$repetition_run/dedup/dedup_sensitivity.tsv" \
  --out-dir "$repetition_run/parlamint-audit" --scratch-dir "$repetition_run/scratch" \
  > "$repetition_run/parlamint-audit/parlamint_audit_run.stdout.log" 2>&1
```

Run both commands sequentially, and inspect their exit status and logs before
continuing. The dedup script returns nonzero for failed input validation; the
expected `NOT STABLE` descriptive verdict is not a run failure. The focused
audit checks fixed six-order and sentence checkpoints and refuses to overwrite
its existing reports. It exports a plain TSV; gzip packaging is a later
lossless archival step. Scratch databases are temporary and are not included.
No corpus CoNLL-U files are distributed with these additions. The examples TSV
contains repeated-text audit excerpts from ParlaMint-SI, not the source corpus;
corpus-derived text retains the corpus licence described in `inputs/README.md`.

## Verification without source corpora

```bash
python3 -m py_compile scripts/dedup_sensitivity.py scripts/inspect_parlamint_duplicates.py scripts/test_repetition_sensitivity.py
python3 scripts/dedup_sensitivity.py --help
python3 scripts/inspect_parlamint_duplicates.py --help
python3 scripts/test_repetition_sensitivity.py
sha256sum -c outputs/supplementary/repetition_sensitivity.sha256
```

The fixture tests were added after the completed run and are not production
analysis code. They exercise exact identity, FORM fallback, first-occurrence
retention, Cartesian pairing and audit accounting with differing annotations.
They also validate the recorded numerical output and the 44 descriptive checks.
They do not run new full-corpus analyses or classify repeated texts linguistically.
