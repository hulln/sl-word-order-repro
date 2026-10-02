# ParlaMint-SI: targeted manual spot check after the automated audit

Recorded 2026-10-02 from the researcher's supplied account of the completed
manual inspection. This is **manual spot-check evidence**, not program-generated
evidence and not a new corpus run in this documentation session. The automated
counts come from `parlamint_duplicate_audit.txt` and
`parlamint_duplicate_examples.tsv` (distributed as `.tsv.gz` in the public repo).

The check asked whether the highest contributor to removed OVS represented
identical texts recurring in different parliamentary locations and why each
occurrence contributed two canonical S/V/O instances.

Exact inspected sentence:

> Predlog zakona je v obravnavo zboru predložila vlada Republike Slovenije.

The researcher inspected the canonical `parlamint-si.conllu`, SHA-256
`be53ad8a8b28e1f7996ba79de045b1c3516324cd8adbe902ea2500e7d02bd81e`.
The following is an **abbreviated transcription of the supplied annotation**,
not a complete CoNLL-U block; omitted fields and dependencies are not invented.

| ID | FORM | UPOS | HEAD | DEPREL |
|---:|---|---|---:|---|
| 1 | Predlog | NOUN | 7 | obj |
| 2 | zakona | NOUN | — | — |
| 3 | je | AUX | 7 | aux |
| 4 | v | ADP | — | — |
| 5 | obravnavo | NOUN | 7 | obl |
| 6 | zboru | NOUN | 7 | obj |
| 7 | predložila | VERB | 0 | root |
| 8 | vlada | NOUN | 7 | nsubj |
| 9 | Republike | NOUN | — | — |
| 10 | Slovenije | PROPN | — | — |

Both NOUN objects precede the VERB, and the NOUN subject follows it:
`Predlog – predložila – vlada` and `zboru – predložila – vlada` are both OVS.
The canonical rule counts every matching subject × object pair. Thus the audit's
513 occurrences yield two OVS instances each; retaining the first leaves
`(513 − 1) × 2 = 1,024` OVS instances from later identical-text occurrences.
The form *zboru* is morphologically dative but annotated `obj`. This illustrates
an annotation qualification: extraction follows the dependency labels, and
sentence deduplication did not create that decision or validate its linguistic
correctness.

The same text was observed under distinct sentence/paragraph identifiers and
in the following distinct segments, dates and sessions (as supplied by the
researcher; these are segment identifiers, not invented sentence IDs):

```text
ParlaMint-SI_2000-12-20-SDZ3-Izredna-03.ana.seg29
ParlaMint-SI_2000-12-20-SDZ3-Izredna-03.ana.seg519
ParlaMint-SI_2000-12-20-SDZ3-Izredna-03.ana.seg532
ParlaMint-SI_2000-12-20-SDZ3-Izredna-03.ana.seg568
ParlaMint-SI_2000-12-20-SDZ3-Izredna-03.ana.seg580
ParlaMint-SI_2000-12-21-SDZ3-Izredna-03.ana.seg168
ParlaMint-SI_2001-01-31-SDZ3-Redna-02.ana.seg8
ParlaMint-SI_2001-01-31-SDZ3-Redna-02.ana.seg377
```

This supports recurrence of identical parliamentary text in different places,
rather than simply treating these as erroneous technical duplicate records.
Inspection of the highest-contributing examples in the automated report shows
many recurring formulations about presenting/considering legislation and giving
speakers the floor. This is a qualitative observation, not a measurement of
formulaicity, and does not classify every repeated sentence as procedural.
The check was targeted, not a systematic classification of all 68,984 repeated
text types. Different metadata locations alone do not certify every aspect of
corpus construction or annotation.

## Commands for reproducing the inspection

These are supplied here as reproducible inspection commands, **not a claim that
these exact commands were used historically**. No unsupplied command output is
presented. Set the path to the same hash-verified canonical file; the hash is
recorded above. The local documentation session did not rerun this corpus check.

```bash
parlamint_corpus=/path/to/parlamint-si.conllu
sha256sum "$parlamint_corpus"
# Line numbers for every exact target # text line:
grep -nFx '# text = Predlog zakona je v obravnavo zboru predložila vlada Republike Slovenije.' "$parlamint_corpus"
# First matching block, including its available metadata and token annotation:
awk -v target='# text = Predlog zakona je v obravnavo zboru predložila vlada Republike Slovenije.' '
  { block = block $0 "\n" }
  $0 == target { found = 1 }
  /^$/ { if (found) { printf "%s", block; exit }; block = "" }
  END { if (found && block != "" && $0 != "") printf "%s", block }
' "$parlamint_corpus"
# Metadata of all matching blocks (streaming; no corpus file modification):
awk -v target='# text = Predlog zakona je v obravnavo zboru predložila vlada Republike Slovenije.' '
  /^#/ { metadata = metadata $0 "\n" }
  $0 == target { found = 1 }
  /^$/ { if (found) printf "%s\n", metadata; metadata = ""; found = 0 }
  END { if (found) printf "%s\n", metadata }
' "$parlamint_corpus"
```

The automatic audit independently extracted every repeated occurrence and found
no differing S/V/O count vectors in any repeated text type. Equality of count
vectors is narrower than equality or correctness of all annotations.
