# Source inputs

`inputs/` is for downloaded or otherwise supplied material **before**
thesis-specific preparation. `scripts/prepare_corpora.py` turns these resources
into the canonical files under `prepared/`. Analysis scripts never read this
directory directly.

The paths below match `config/corpora.tsv`. Licences are stated only where the
upstream record or repository makes them explicit; otherwise consult the linked
record before redistributing data.

## Public resources

| Resource | Version and official source | Licence | Put under `inputs/` | Preparation and annotation provenance |
|---|---|---|---|---|
| UD Slovenian-SSJ | UD 2.18, [UD repository](https://github.com/UniversalDependencies/UD_Slovenian-SSJ/tree/r2.18) | CC BY-SA 4.0 | `UD_Slovenian-SSJ/` | Merge train, dev, and test. Syntax and NER are official gold. Produces `prepared/ssj.conllu`. |
| UD Slovenian-SST | UD 2.18, [UD repository](https://github.com/UniversalDependencies/UD_Slovenian-SST/tree/r2.18) | CC BY-SA 4.0 | `UD_Slovenian-SST/` | Merge train, dev, and test; add CLASSLA 2.2.1 NER in pretokenized mode while preserving every non-MISC field. Syntax remains official gold. Produces `prepared/sst.conllu`. |
| SUK | SUK 1.1, [CLARIN.SI 11356/1959](http://hdl.handle.net/11356/1959) | CC BY-SA 4.0 | `combined_suk.conllu` | A SUK-derived UD CoNLL-U composite prepared by the thesis supervisor and supplied to the author; see the note below for what it contains and why it is not a download. Split by `zvrst` metadata; repair only `HEAD=_` roots; exclude unmapped documents. |
| JANES-News | Janes-News 1.0 / JANES v0.4 base, [11356/1140](http://hdl.handle.net/11356/1140) | CC BY 4.0 | `janes.news.conllu` | Comments on online news articles (rtvslo.si, mladina.si, reporter.si, 2007-03 to 2015-01), not the articles themselves. The relationship between the analysed conversion and the public release could not be established: the metadata schema, sites and period match, and the token counts are close (14,477,309 against 14,838,074), but the document grouping differs and the release states that person entities were removed from its texts. Settling this would require a comparison against the distributed TEI/vertical, which this package does not perform. The analysis input is a UD CoNLL-U conversion prepared and annotated by the thesis supervisor and supplied to the author; CLARIN distributes this corpus as TEI/vertical, not as UD CoNLL-U. The conversion keeps the original JANES document and sentence identifiers and its `text_meta` metadata, and adds a full CLASSLA layer (`tokenize,mwt,pos,lemma,depparse,ner`). Copy it to `prepared/janes-news.conllu`. Syntax and NER are automatic. |
| JANES-Blog | Janes-Blog 1.0 / JANES v0.4 base, [11356/1138](http://hdl.handle.net/11356/1138) | CC BY 4.0 | `janes.blog.conllu` | Same supervisor-prepared route as JANES-News. Copy to `prepared/janes-blog.conllu`. Syntax is automatic. |
| JANES-Forum | Janes-Forum 1.0 / JANES v0.4 base, [11356/1139](http://hdl.handle.net/11356/1139) | CC BY 4.0 | `janes.forum.conllu` | Same supervisor-prepared route as JANES-News. Copy to `prepared/janes-forum.conllu`. Syntax is automatic. |
| JANES-Tweet | Janes-Tweet 1.0 / JANES v0.4 base, [11356/1142](http://hdl.handle.net/11356/1142) | CC BY-NC 4.0 | `janes_tweet.conllu` | Same supervisor-prepared route as JANES-News, but delivered twice. Use **only** the clean underscore variant `janes_tweet.conllu`. The earlier dot variant `janes.tweet.conllu` is encoding-mangled — roughly 69 % of its word forms are fragments — and must never be used; it was superseded once the upstream encoding problem was fixed. Twitter redistribution/access constraints apply. |
| JANES-Wiki | Janes-Wiki 1.0, [11356/1137](http://hdl.handle.net/11356/1137) | CC BY-SA 4.0 | `Janes-Wiki.vert.zip` | Wikipedia talk pages. Historical preparation was vertical → sentence text → CLASSLA 2.2.1 UD/NER, producing `prepared/janes-wiki.conllu`. The CLARIN record lists MD5 `69f4e9f7a9e3c1f3cc5562df1a3d51c9` for `Janes-Wiki.vert.zip` and 5,008,067 source tokens; the historical conversion reproduced that token count exactly, which is the acceptance check before parsing. The source vertical held 390,525 sentences, but CLASSLA re-segmented the detokenized text, so the prepared file's own sentence count is **not** established and the manifest pins none. The public package documents this route but does not yet contain a verified end-to-end converter/parser wrapper. |
| CLASSLA-Wikipedia | CLASSLA-Wikipedia 1.0, Slovenian part, [11356/1427](http://hdl.handle.net/11356/1427) | CC BY 4.0 | `classlawiki-sl.conllu.gz` | Download [`classlawiki-sl.conllu.gz`](https://www.clarin.si/repository/xmlui/bitstream/handle/11356/1427/classlawiki-sl.conllu.gz) (~620 MB) and decompress it to `prepared/classla-wikipedia.conllu`. The distribution is analysis-ready: HEAD/DEPREL are filled and `NER=` is present, so it is used **as supplied and never reannotated**. These are Wikipedia articles, unlike JANES-Wiki talk pages. |
| ParlaMint-SI | ParlaMint.ana 4.0, [11356/1860](http://hdl.handle.net/11356/1860) | CC BY 4.0 | `ParlaMint-SI.ana/` | Download the Slovenian `.ana` package and concatenate its per-year CoNLL-U files. This package concatenates in sorted path order; the historical run used a shell command that could resolve to either glob order or filesystem traversal order, so the **byte content of the concatenation is not reproducible**, only its counts. Concatenation order cannot change any word-order count, because it does not change which sentences are present. The distributed syntax is automatic. |
| KDSP | KDSP 1.0, [11356/1823](http://hdl.handle.net/11356/1823) | CC BY 4.0 | `KDSP.txt` | 262 texts of longer Slovenian narrative prose published 1836–1918. CLARIN distributes TEI/vertical, not UD, so the historical route downloaded the release and annotated its text with CLASSLA 2.2.1 using the full stack `tokenize,mwt,pos,lemma,depparse,ner`, documents chunked at 250,000 characters on paragraph boundaries. The annotator is not shipped here, so the step is documented rather than runnable, and the resulting file is not byte-pinned. |
| AI-GenT | AI-GenT 1.0, [11356/2210](http://hdl.handle.net/11356/2210) | CC BY-NC-SA 4.0 | the three distributed files already present as `aigent-*.conllu` | Use the Slovenian `4y-gs`, default-prompt cells for GPT-5, GaMS-27B, and gemma-2-27b. Distributed Trankit annotation (UD v2.15 model) is copied unchanged into `prepared/`. |

The three SUK rows in the manifest are **derived analysis corpora**, not three
downloads: `suk-literary`, `suk-publicistic`, and `suk-professional` all come
from the one verified `combined_suk.conllu` composite.

**`combined_suk.conllu` cannot be downloaded, and it is wider than the CoNLL-U
CLARIN ships.** It was prepared by the thesis supervisor and supplied to the
author. SUK 1.1's CoNLL-U distribution covers only the two
syntactically annotated parts — `ssj500k-syn.ud.conllu` (11,411 sentences) and
`elexiswsd.ud.conllu` (2,024) — whereas the composite holds 48,594 sentences
across 2,908 documents drawn from four SUK components: ssj500k 2.3,
SentiCoref 1.0, Ambiga and ELEXIS-WSD 1.0. It is therefore a UD conversion of
substantially more of SUK than the release distributes in that format, and the
components SUK publishes without manually checked syntax carry automatically
added parses, which is why some of their roots are written `HEAD=_` and have to
be repaired before extraction. It also carries a `dedup_status` field that the
official export does not have.

Downloading SUK 1.1 therefore does **not** reproduce the composite, and the
conversion code that built it has not been recovered. What was verified against
SUK 1.1 is the query-relevant layer on the parts the release does distribute:
FORM, UPOS, HEAD and DEPREL are identical, and the only differences are 262
FEATS values, which no analysis in this package reads. Genre splitting and
everything downstream of it are fully reproducible from the exact file, which is
checksum-pinned: `combined_suk.conllu`, SHA-256
`03f9222d6e9e86b4d5aab50fd11781127f3f6f3e1b017039a0d3d2d3889ebc5c`. The public
entry point remains the three files already shipped under `prepared/`.

## Human and GPT-5 thesis essay pair

Both sets are 691 essays keyed to the **same 691 Šolar document identifiers**,
one machine text per human text. The identifier sets are identical, with no
document on either side only. The human side has 19,358 sentences, the GPT-5
side 17,179.

**The 691 documents are the fourth-year secondary-school subset of Šolar.** This
is not inferred from the identifiers: the same subset is defined independently
by AI-GenT 1.0, whose Slovenian `4y-ss` cell contains exactly these 691
documents, and whose narrower `4y-gs` cell (fourth-year grammar school, 205
documents) is a strict subset of them. AI-GenT names Šolar 3.0
([11356/1589](http://hdl.handle.net/11356/1589)) as the human corpus it was
built on.

**The GPT-5 texts are an AI-GenT cell.** The analysed file is AI-GenT 1.0's
Slovenian `Solar/4y-ss/GPT-5/pap` annotated file — the persona-aware prompt
variant — with DEPS and MISC blanked: across all 374,196 tokens, columns 1–9 are
byte-identical, and the only MISC difference is the removal of `SpaceAfter=No`.
The generation is therefore documented by AI-GenT itself: model GPT-5, prompts
built from each Šolar essay's title, subtitle, referenced literary work and the
length of the corresponding human essay, with the persona-aware template
published in AI-GenT's `Prompt_templates.md`; AI-GenT also ships the raw
generated texts. It follows that the syntactic layer of the GPT-5 essays is
**Trankit with the custom Slovenian UD v2.15 model**, the annotator AI-GenT
used — not CLASSLA. The base file is obtainable by taking that cell from
[AI-GenT 1.0](http://hdl.handle.net/11356/2210) and blanking DEPS and MISC.

For the human essays the annotator is **not** established. Šolar 3.0 was not
available for comparison here, and the file carries the same DEPS/MISC blanking
as its GPT-5 counterpart, so it went through the same normalisation — but which
tool produced its trees is not evidence-backed and is not claimed.

### Named-entity layer

Neither analysed file carries any NER: their MISC columns contain no `NER=`
value. The named-entity layer is added by preparation, and that step is
reproducible:

```bash
python3 scripts/add_ner_annotation.py --input inputs/human-essays.conllu \
  --output prepared/human-essays.conllu --type standard
```

`prepare_corpora.py` runs exactly this for both essay rows and then asserts that
nothing outside MISC changed. Regenerating both derivatives with CLASSLA 2.2.1
in `standard` mode reproduces **all eight** cached essay NER distributions
exactly — both roles, both entity statuses, all six patterns, for both corpora.
The derivatives are not byte-pinned, because the historical ones were not kept;
what is demonstrated is that the analysis counts are recovered from the pinned
base files.

- Expected base inputs: `inputs/human-essays.conllu` and
  `inputs/gpt5-essays.conllu`, pinned by SHA-256:
  - human essays, 19,358 sentences:
    `6f6282c7b4d25e1089a412740fbcc7626c9f46e86e11ce282b10157319d33322`
  - GPT-5 essays, 17,179 sentences:
    `a9945c5d40f9e7f6a066da2d2c549c76a26ca6d20b4bd7ff01b49e80e2e247a0`
- Neither file is redistributed here. AI-GenT is public under CC BY-NC-SA 4.0;
  the redistribution status of the Šolar-derived human file is unresolved.
- Lightweight reproduction uses only the verified aggregate reference counts;
  it does not reconstruct or expose the essays.

## Fingerprints of the corpora that are not shipped

Eight corpora are reproduced here from verified aggregate counts rather than
from their prepared CoNLL-U, because the files are too large or not
redistributable. Four of them are byte copies of a supplied file, so their
prepared SHA-256 is exact and the manifest pins it:

| Prepared file | SHA-256 |
|---|---|
| `janes-news.conllu` | `af4fe2a16e583ff25661a361682903fef10c68e4304eebc9fbb2ea5c18d4ab19` |
| `janes-blog.conllu` | `7b8933e14a8e078dbf9322ed2945cdec609ff7107489ab2cfa00156c6cf9cf0c` |
| `janes-forum.conllu` | `3aecac32f75d5fa5c224c59abb66bf9bca3310d881657bd38ff0689b26b6dabd` |
| `janes-tweet.conllu` | `4a3f1c85f45094941670bf1d1fad7e50dc1fe117b3aa18d7a583ebdf0ca83bb1` |

For the other four, only a truncated SHA-256 was ever recorded, from a
server-side checksum file that is not distributed. These are identification
aids, not pins: the manifest leaves `prepared_sha256` empty for them and
`prepare_corpora.py` does not check them.

| Prepared file | SHA-256 (first 16) | Recorded |
|---|---|---|
| `janes-wiki.conllu` | `aa398403028feede` | server build, 2026-07-10 |
| `classla-wikipedia.conllu` | `d163fd9647110e67` | server copy, 2026-07-10 |
| `parlamint.conllu` | `be53ad8a8b28e1f7` | server copy, 2026-07-08 |
| `kdsp.conllu` | `d9e34d3d0520e19d` | server copy, 2026-07-08 |

Two of those four could not match a local rebuild even if the full digest were
known. `parlamint.conllu` depends on the concatenation order discussed above,
and `janes-wiki.conllu` came from a CLASSLA run this package cannot regenerate.
`classla-wikipedia.conllu` is a plain decompression of a public download, so a
correctly obtained file should match its fingerprint.

## What is already included

The three small, publicly distributable AI-GenT CoNLL-U source files are
included. Other source inputs must be obtained according to their licences and
placed at the exact manifest paths. Prepared SSJ/SST/SUK files are distributed
separately under `prepared/` because they are outputs of preparation, not source
downloads.
