# Word order in Slovenian: reproducibility package

Reproduces the quantitative analyses and the seven figures of a master's thesis on
subject–verb–object word order in Slovenian (University of Ljubljana, Digital
Linguistics). The study asks how the relative order of subject, verb and object
varies across standard written, spoken, web, encyclopaedic, parliamentary,
historical-prose and human-versus-machine-generated Slovenian, and whether
registers differ in how fixed or variable that order is.

All examples come from one query over dependency-annotated corpora:

```text
upos=VERB >nsubj upos=NOUN >obj upos=NOUN
```

The predicate must be a `VERB` and both arguments common nouns (`NOUN`), with
relations exactly `nsubj` and `obj`; subtypes and `iobj` are excluded. Every
matching subject × object pair is classified as SVO, SOV, VSO, VOS, OSV or OVS.

## What you can reproduce

Three levels apply to different corpora:

- **Level 1 — source-to-result.** You obtain the official release, this package
  builds the analysis corpus and extracts the counts on your machine.
- **Level 2 — prepared-input-to-result.** The exact analysed file is available to
  you, but this package cannot rebuild it from a public source. Counts are
  recomputed from that file, which is identified by SHA-256.
- **Level 3 — downstream-from-verified-counts.** The analysis corpus is not
  available, so stored counts verified at analysis time are used instead.

> **A cached count is a recorded analysis result, not a rebuilt corpus.** At level 3
> nothing is recomputed from text, and the corpus preparation behind those numbers
> cannot be rechecked. Every such row is marked `verified_reference_*` in the output.

Statistics, all seven figures and the supplementary check are recomputed in full
regardless. The **verified-cache workflow** is what an outside reader can run today;
the **full workflow** requires all 18 analysis corpora and never falls back to the
cache.

## Repository structure

```mermaid
flowchart LR
  subgraph DOC[" "]
    direction TB
    CFG["<b>config/corpora.tsv</b><br/>inventory of all 18 corpus sets:<br/>version, paths, checksums,<br/>annotation layers"]
    INP["<b>inputs/README.md</b><br/>where to obtain every corpus,<br/>with links and licences"]
  end

  subgraph DATA[" "]
    direction TB
    PREP["<b>prepared/</b><br/>canonical CoNLL-U files<br/>the analysis actually reads<br/>+ checksums.sha256"]
    REF["<b>reference/</b><br/>verified counts for corpora<br/>that cannot be rebuilt here<br/><i>opt-in only</i>"]
  end

  SCR["<b>scripts/</b><br/>12 Python scripts:<br/>prepare → extract → analyse<br/>→ statistics → figures"]

  subgraph OUT[" "]
    direction TB
    ODATA["<b>outputs/data/</b><br/>4 canonical TSV tables"]
    OFIG["<b>outputs/figures/</b><br/>7 thesis figures, PDF"]
    OSUP["<b>outputs/supplementary/</b><br/>one separate supplementary check"]
  end

  CFG -->|"drives"| SCR
  INP -.->|"tells you how to fill"| PREP
  PREP -->|"read by"| SCR
  REF -.->|"only with --use-reference-cache"| SCR
  SCR -->|"writes"| ODATA
  ODATA -->|"read by make_figures.py"| OFIG
  SCR -.->|"supplementary check"| OSUP

  classDef doc fill:#eef3f7,stroke:#4a6b82,color:#1b2b36
  classDef data fill:#dbe9f2,stroke:#2f5f80,color:#12222c
  classDef cache fill:#f6efe2,stroke:#9a7b3f,color:#2c2418
  classDef code fill:#e4ede4,stroke:#4a7050,color:#16241a
  classDef out fill:#0072B2,stroke:#004b75,color:#ffffff
  class CFG,INP doc
  class PREP data
  class REF cache
  class SCR code
  class ODATA,OFIG out
  class OSUP cache
```

Details live next to the data they describe: [`inputs/README.md`](inputs/README.md)
for corpus sources, versions, licences and preparation;
[`prepared/README.md`](prepared/README.md) for checksums and what is pinned;
[`reference/README.md`](reference/README.md) for what the cached counts are and how
they were verified.

## Data flow

```mermaid
flowchart TB
  subgraph S["① SOURCE — you obtain these; see inputs/README.md"]
    direction LR
    S_UD["UD Slovenian-SSJ 2.18<br/>UD Slovenian-SST 2.18"]
    S_SUK["SUK-derived CoNLL-U composite<br/>prepared by the thesis supervisor"]
    S_JAN["Janes-News · Blog · Forum · Tweet<br/>CLASSLA-annotated, supplied"]
    S_JW["Janes-Wiki 1.0<br/>CLARIN vertical"]
    S_CW["CLASSLA-Wikipedia 1.0 sl<br/>analysis-ready CoNLL-U"]
    S_PM["ParlaMint-SI .ana 4.0"]
    S_KD["KDSP 1.0<br/>262 prose texts, 1836–1918"]
    S_HU["Šolar 3.0 — 4y-ss<br/>691 human essays"]
    S_GP["AI-GenT 1.0 — 4y-ss / GPT-5 / pap<br/>691 generated essays"]
    S_AG["AI-GenT 1.0 — 4y-gs / default<br/>GPT-5 · GaMS-27B · gemma-2-27b"]
  end

  subgraph P["② PREPARATION"]
    direction LR
    P_UDM["merge train+dev+test"]
    P_NER["add CLASSLA 2.2.1 NER<br/>trees untouched"]
    P_SPL["split by genre metadata<br/>repair HEAD=_ roots"]
    P_CP["copy as supplied"]
    P_V2T["vertical → text → CLASSLA"]
    P_GZ["decompress only<br/>never re-annotated"]
    P_CAT["concatenate per-year files"]
    P_CLA["CLASSLA full stack"]
  end

  subgraph PR["③ PREPARED — the canonical analysis inputs"]
    direction LR
    R_SSJ["ssj"]
    R_SST["sst"]
    R_SUK["suk-literary<br/>suk-publicistic<br/>suk-professional"]
    R_AIG["aigent-gpt5<br/>aigent-gams27b<br/>aigent-gemma2-27b"]
    R_BIG["janes-news · janes-blog<br/>janes-forum · janes-tweet<br/>janes-wiki · classla-wikipedia<br/>parlamint · kdsp"]
    R_ESS["human-essays<br/>gpt5-essays"]
  end

  subgraph C["④ VERIFIED REFERENCE CACHE — not a fresh run"]
    CACHE["reference/word_order_counts.tsv — 10 corpora<br/>reference/ner_word_order_counts.tsv — 3 corpora<br/><br/>opt-in via --use-reference-cache<br/>every row stamped verified_reference_*"]
  end

  subgraph A["⑤ ANALYSIS"]
    direction TB
    HUB(["each prepared corpus present locally"])
    A_ST["STARK extraction"]
    A_DI["independent direct<br/>CoNLL-U extraction"]
    A_EQ{"identical on all<br/>six patterns?"}
    A_MRG["add CLASSLA 2.2.1 NER<br/>deterministic derived step"]
    A_NER["analyze_ner.py<br/>NOUN or PROPN arguments"]
  end

  subgraph D["⑥ CANONICAL DATA — outputs/data/"]
    direction LR
    D_WC["word_order_counts.tsv"]
    D_NE["ner_word_order.tsv"]
    D_SU["word_order_summary.tsv"]
    D_ST["statistical_tests.tsv"]
  end

  F["⑦ FIGURES — make_figures.py<br/>seven thesis PDFs"]
  STOP["run fails"]

  S_UD --> P_UDM --> R_SSJ
  P_UDM --> P_NER --> R_SST
  S_SUK --> P_SPL --> R_SUK
  S_AG --> P_CP --> R_AIG
  S_JAN --> P_CP --> R_BIG
  S_JW --> P_V2T --> R_BIG
  S_CW --> P_GZ --> R_BIG
  S_PM --> P_CAT --> R_BIG
  S_KD --> P_CLA --> R_BIG
  S_HU --> R_ESS
  S_GP --> R_ESS

  R_SSJ --> HUB
  R_SST --> HUB
  R_SUK --> HUB
  R_AIG --> HUB
  R_BIG --> HUB
  R_ESS --> HUB

  R_BIG -. "if not available locally" .-> CACHE
  R_ESS -. "if not available locally" .-> CACHE

  HUB --> A_ST --> A_EQ
  HUB --> A_DI --> A_EQ
  A_EQ -->|"yes → stark_direct_exact"| D_WC
  A_EQ -->|"no"| STOP
  CACHE -->|"verified_reference_stark_direct_exact"| D_WC

  R_SSJ --> A_NER
  R_SST --> A_NER
  R_SUK --> A_NER
  R_ESS --> A_MRG --> A_NER
  A_NER --> D_NE
  CACHE -->|"verified_reference_counts"| D_NE

  D_WC --> D_SU
  D_WC --> D_ST
  D_NE --> D_ST
  D_SU --> F
  D_ST --> F
  D_NE --> F

  SUPIN["reference/manual_subset_counts.tsv<br/>SUK subset with manually checked syntax"] --> SUP
  D_WC -->|"canonical SST row"| SUP
  SUP["supplementary_manual_subset.py<br/>same permutation + Holm procedure"] --> SUPOUT["outputs/supplementary/<br/>manual_subset_h2.tsv"]

  classDef src fill:#eef3f7,stroke:#4a6b82,color:#1b2b36
  classDef prep fill:#e4ede4,stroke:#4a7050,color:#16241a
  classDef prepared fill:#cfe2ef,stroke:#2f5f80,color:#12222c
  classDef cache fill:#f6efe2,stroke:#9a7b3f,color:#2c2418
  classDef ana fill:#e8e2f0,stroke:#5d4b80,color:#221b2e
  classDef out fill:#0072B2,stroke:#004b75,color:#ffffff
  classDef fail fill:#f3dede,stroke:#8b3a3a,color:#3a1414
  class S_UD,S_SUK,S_JAN,S_JW,S_CW,S_PM,S_KD,S_HU,S_GP,S_AG src
  class P_UDM,P_NER,P_SPL,P_CP,P_V2T,P_GZ,P_CAT,P_CLA prep
  class R_SSJ,R_SST,R_SUK,R_AIG,R_BIG,R_ESS prepared
  class CACHE cache
  class HUB,A_ST,A_DI,A_EQ,A_MRG,A_NER ana
  class D_WC,D_NE,D_SU,D_ST,F out
  class STOP fail
  class SUPIN,SUP,SUPOUT supp
  classDef supp fill:#f6efe2,stroke:#9a7b3f,color:#2c2418,stroke-dasharray:4 3
  style S fill:#fbfcfd,stroke:#c3d0da
  style P fill:#fbfcfd,stroke:#c3d0da
  style PR fill:#fbfcfd,stroke:#c3d0da
  style C fill:#fdfaf4,stroke:#d8c69f
  style A fill:#fbfcfd,stroke:#c3d0da
  style D fill:#fbfcfd,stroke:#c3d0da
```

## The corpora

18 analysis sets from 12 public resources plus one non-public essay pair. Sources,
versions, licences and preparation steps are in
[`inputs/README.md`](inputs/README.md).

| Corpus | Source / version | How you get it | Level |
|---|---|---|---|
| SSJ | UD Slovenian-SSJ r2.18 | rebuilt by this package | 1 |
| SST | UD Slovenian-SST r2.18 | rebuilt; NER step needs the annotation extras | 1 |
| SUK literary / publicistic / professional | SUK 1.1, via a composite prepared by the thesis supervisor | not distributed here pending a redistribution decision; runs from the composite | 2 |
| JANES News / Blog / Forum / Tweet | Janes-* 1.0, JANES v0.4 base; UD conversion prepared by the thesis supervisor | verified counts | 3 |
| JANES-Wiki | Janes-Wiki 1.0, Wikipedia talk pages | verified counts | 3 |
| CLASSLA-Wikipedia | CLASSLA-Wikipedia 1.0, Slovenian | public download, else verified counts | 1 / 3 |
| ParlaMint-SI | ParlaMint.ana 4.0 | public download, else verified counts | 1 / 3 |
| KDSP | KDSP 1.0 | verified counts | 3 |
| Human essays | Šolar 3.0, the 691 fourth-year secondary essays | verified counts | 3 |
| GPT-5 essays | AI-GenT 1.0, `sl/Solar/4y-ss/GPT-5/pap` | from AI-GenT, else verified counts | 2 / 3 |
| AI-GenT gpt-5 / GaMS-27B / gemma-2-27b | AI-GenT 1.0, `sl/Solar/4y-gs`, default prompt | public download | 1 |

No corpus files are tracked in this repository.

## Quickstart

```bash
git clone https://github.com/hulln/sl-word-order-repro.git
cd sl-word-order-repro
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Extraction uses [STARK](https://github.com/clarinsi/STARK) (Krsnik & Dobrovoljc,
TLT 2025, <https://aclanthology.org/2025.tlt-1.5/>), which is not bundled; the
thesis used upstream commit `fd0202d` (`v3.1.0-3-gfd0202d`). This package runs
STARK with its own interpreter, so STARK's dependencies go into the same
environment, and then the workflow runs:

```bash
.venv/bin/pip install -r /path/to/STARK/requirements.txt
python3 scripts/run_all.py --stark /path/to/STARK/stark.py --use-reference-cache
```

Drop `--use-reference-cache` for the full workflow. `compute_statistics.py` and
`make_figures.py` need neither corpora nor STARK — they run from `outputs/data/`,
which holds the six-pattern counts, the summary with entropy, the named-entity
table and the statistical tests (χ², Jensen–Shannon, cosine, fixed-seed
permutation, Fisher, Holm). Only the stages that add a CLASSLA named-entity layer
need `requirements-annotation.txt`, which pulls in PyTorch.

## Supplementary check

`outputs/supplementary/` holds one check that sits outside the main 18-corpus
analysis: the H2 genre comparisons repeated on the SUK subset whose syntax is
manually checked, against the canonical SST. Run it with
`python3 scripts/supplementary_manual_subset.py`.

## Limitations

- **The full workflow is not currently achievable from public sources.** The four
  JANES sets, JANES-Wiki, KDSP and the human essays cannot be reconstructed in the
  form analysed; they are level 3.
- **The SUK composite** covers more of SUK than the release distributes as CoNLL-U
  and cannot be rebuilt from it. Its query-relevant layer (FORM, UPOS, HEAD,
  DEPREL) was verified identical to SUK 1.1. The prepared files are not
  distributed here pending a redistribution decision.
- **ParlaMint** concatenation order was not recorded, so the concatenated file is
  not byte-reproducible; order cannot change any count.
- **JANES-Wiki**: CLASSLA re-segmented the text, so the prepared file's sentence
  count is not established and the manifest pins none.
- **The essays**: the GPT-5 side is annotated with Trankit (AI-GenT's annotator);
  the human side's annotator is undocumented and only CLASSLA was ruled out. The
  two sets are comparable by matched design — 691 paired documents — not by a
  demonstrated identical annotation procedure. Neither base file carries NER; it is
  added deterministically by `scripts/add_ner_annotation.py`.
- **Named-entity results for automatically labelled sources are exploratory**: the
  criterion is the label on the argument's head token, not givenness or topicality.
  For Janes-News, the relationship between the analysed conversion and the public
  anonymised release could not be established.
- **`all_pairwise`** is computed over every pair mechanically and so includes pairs
  the thesis never compares — SSJ overlaps SUK by design. The prespecified tests
  are `h1_omnibus` and `h2_prespecified`.

## Licence and citation

Code and documentation: **MIT** ([`LICENSE`](LICENSE)).

MIT covers this repository only and grants no rights over any corpus. No corpus
files are distributed here; each keeps the licence of its original release —
listed in [`inputs/README.md`](inputs/README.md) — and several are non-commercial
or share-alike. To cite the package, see [`CITATION.cff`](CITATION.cff).
