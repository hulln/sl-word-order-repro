# Word order in Slovenian: reproducibility package

This repository accompanies a master's thesis on subject–verb–object word order
in Slovenian. It compares the six possible S/V/O orders across written, spoken,
web, parliamentary, historical and human-versus-machine-generated texts, runs
the thesis statistics and recreates the seven figures.

Some corpora can be rebuilt from public sources. For others, the exact analysed
file cannot be redistributed or reconstructed here, so the repository includes
previously verified aggregate counts instead.

## Main word-order query

The main analysis uses this dependency query:

```text
upos=VERB >nsubj upos=NOUN >obj upos=NOUN
```

It selects a `VERB` with `nsubj` and `obj` dependents, both headed by `NOUN`.
STARK runs with `label_subtypes=no`, so relation subtypes are collapsed to their
base labels for STARK matching, whereas the independent direct extractor
requires exact `nsubj` and `obj`. No `nsubj`/`obj` subtypes occur in the analysed
Slovenian prepared sources, so this distinction does not affect the reported
counts. `iobj` remains outside the query. All matching subject × object pairs are
counted and classified as SVO, SOV, VSO, VOS, OSV or OVS.

The separate named-entity analysis uses the same relations but allows `NOUN` or
`PROPN` argument heads.

## What a fresh clone contains

No CoNLL-U corpus files are tracked in Git. A fresh clone contains the numerical
results, statistics and figures, plus verified stored counts for corpora that may
be unavailable. It does not contain prepared corpora.

## Repository structure

```mermaid
---
config:
  layout: elk
  theme: base
  fontFamily: Arial
  themeVariables:
    fontFamily: Arial
    fontSize: 17px
    primaryTextColor: "#24343d"
    lineColor: "#829098"
    background: "#ffffff"
    edgeLabelBackground: "#ffffff"
  flowchart:
    htmlLabels: true
    curve: linear
    nodeSpacing: 42
    rankSpacing: 48
    padding: 16
  elk:
    mergeEdges: true
    nodePlacementStrategy: LINEAR_SEGMENTS
    nodePlacementAlignment: BALANCED
---
flowchart TB
    GUIDE("<b>inputs/README.md</b><br/>sources · licences<br/>download instructions")
    CFG("<b>config/corpora.tsv</b><br/>18-set inventory<br/>paths · preparation · optional validation pins")

    PREP("<b>prepared/</b><br/>canonical CoNLL-U<br/>checksums.sha256")
    REF("<b>reference/</b><br/>verified aggregate and<br/>supplementary numerical inputs")

    PIPE("<b>scripts/</b><br/>prepare → extract → analyse<br/>statistics → figures")

    DATA("<b>outputs/data/</b><br/>4 canonical TSV tables")
    FIG("<b>outputs/figures/</b><br/>7 thesis figures · PDF")
    SUP("<b>outputs/supplementary/</b><br/>supplementary checks")

    GUIDE --> PREP
    PREP --> PIPE
    CFG --> PIPE
    REF -.-> PIPE
    PIPE --> DATA
    DATA --> FIG
    PIPE -.-> SUP

    classDef source fill:#edf3f6,stroke:#8ca5b3,stroke-width:1.4px,color:#24343d,font-size:17px
    classDef prepared fill:#d9e8ef,stroke:#52788d,stroke-width:2px,color:#1f3440,font-size:17px
    classDef cache fill:#f4efe5,stroke:#a58e69,stroke-width:1.6px,stroke-dasharray:6 4,color:#473d2e,font-size:16px
    classDef analysis fill:#eeeaf3,stroke:#817394,stroke-width:1.6px,color:#302a38,font-size:17px
    classDef result fill:#dceaf0,stroke:#52788d,stroke-width:1.7px,color:#1f3440,font-size:17px
    classDef final fill:#c9dde7,stroke:#466e82,stroke-width:2px,color:#18313d,font-size:17px
    classDef secondary fill:#f3f1ec,stroke:#a39c8e,stroke-width:1.3px,stroke-dasharray:5 4,color:#4a4740,font-size:15px

    class GUIDE,CFG source
    class PREP prepared
    class REF cache
    class PIPE analysis
    class DATA result
    class FIG final
    class SUP secondary

    linkStyle default stroke:#829098,stroke-width:1.35px
```

Details live next to the data they describe: [`inputs/README.md`](inputs/README.md)
for corpus sources, versions, licences and preparation;
[`prepared/README.md`](prepared/README.md) for checksums and what is pinned;
[`reference/README.md`](reference/README.md) for what the stored counts are and how
they were verified; and
[`outputs/supplementary/README.md`](outputs/supplementary/README.md) for the
supplementary analyses.

## Data flow

```mermaid
---
config:
  layout: elk
  theme: base
  fontFamily: Arial
  themeVariables:
    fontFamily: Arial
    fontSize: 17px
    primaryTextColor: "#24343d"
    lineColor: "#829098"
    background: "#ffffff"
    edgeLabelBackground: "#ffffff"
  flowchart:
    htmlLabels: true
    curve: linear
    nodeSpacing: 30
    rankSpacing: 42
    padding: 16
  elk:
    mergeEdges: true
    nodePlacementStrategy: LINEAR_SEGMENTS
    nodePlacementAlignment: BALANCED
---
flowchart TB
    UD("<b>UD</b><br/>SSJ 2.18 · SST 2.18<br/>merge splits · SST + NER")
    SUP("<b>SUK + supplied JANES</b><br/>SUK → Literary · Publicistic · Professional<br/>JANES News · Blog · Forum · Tweet")
    PUB("<b>Other public corpora</b><br/>JANES-Wiki · CLASSLA-Wikipedia<br/>ParlaMint-SI 4.0 · KDSP")
    ESS("<b>Matched essays</b><br/>Human 4y-ss · GPT-5 4y-ss/pap<br/>deterministic NER enrichment")
    AIG("<b>AI-GenT supplementary comparison</b><br/>GPT-5 · GaMS · Gemma<br/>4y-gs / default")

    subgraph STATES[" "]
      direction LR
      PREP("<b>PREPARED INPUT</b><br/>exact corpora · fresh analysis")
      CACHE("<b>VERIFIED REFERENCE COUNTS</b><br/>recorded result · not a rebuilt corpus")
    end

    WORD("<b>WORD-ORDER ANALYSIS</b><br/>STARK + direct CoNLL-U<br/>exact agreement required<br/><i>mismatch → stop</i>")
    NERIN("<b>NER-capable inputs</b>")
    NER("<b>NER ANALYSIS</b>")

    RESULT("<b>CANONICAL RESULTS</b><br/>word-order counts + summary · NER results")
    STATS("<b>STATISTICS</b><br/>canonical statistical tests")
    FIG("<b>7 THESIS FIGURES</b>")

    CHECKS("<b>SUPPLEMENTARY CHECKS</b>")

    UD --> PREP
    SUP --> PREP
    PUB --> PREP
    ESS --> PREP
    AIG --> PREP

    PREP --> WORD
    PREP --> NERIN --> NER
    WORD --> RESULT
    NER --> RESULT
    CACHE -.-> RESULT

    RESULT --> STATS --> FIG
    RESULT -.-> CHECKS
    CACHE -.-> CHECKS

    classDef source fill:#edf3f6,stroke:#8ca5b3,stroke-width:1.4px,color:#24343d,font-size:17px
    classDef prepared fill:#d9e8ef,stroke:#52788d,stroke-width:2px,color:#1f3440,font-size:18px
    classDef cache fill:#f4efe5,stroke:#a58e69,stroke-width:1.6px,stroke-dasharray:6 4,color:#473d2e,font-size:16px
    classDef analysis fill:#eeeaf3,stroke:#817394,stroke-width:1.5px,color:#302a38,font-size:17px
    classDef result fill:#dceaf0,stroke:#52788d,stroke-width:1.7px,color:#1f3440,font-size:17px
    classDef final fill:#c9dde7,stroke:#466e82,stroke-width:2px,color:#18313d,font-size:18px
    classDef secondary fill:#f3f1ec,stroke:#a39c8e,stroke-width:1.3px,stroke-dasharray:5 4,color:#4a4740,font-size:15px

    class UD,SUP,PUB,ESS,AIG source
    class PREP prepared
    class CACHE cache
    class WORD,NERIN,NER analysis
    class RESULT,STATS result
    class FIG final
    class CHECKS secondary

    style STATES fill:transparent,stroke:transparent
    linkStyle default stroke:#829098,stroke-width:1.35px
```

## Corpus routes

The 18 analysis sets do not all enter the workflow in the same way:

| Corpus | Available route |
|---|---|
| SSJ; SST | Rebuild from the public UD 2.18 releases. SST also needs the annotation dependencies. |
| SUK literary / publicistic / professional | Reanalyse from the exact supervisor-prepared composite or derived files. The public SUK CoNLL-U is not the same corpus. |
| JANES News / Blog / Forum / Tweet | Reanalyse if the exact supervisor-prepared files are available; otherwise use verified stored counts. |
| JANES-Wiki; KDSP | The historical preparation is not runnable here; use verified stored counts unless the exact prepared files are available. |
| CLASSLA-Wikipedia; ParlaMint-SI | Rebuild from the public releases, or use verified stored counts. |
| Human essays | Reanalyse from the prepared matched subset if available; otherwise use verified stored counts. |
| GPT-5 essays | Normalize the AI-GenT essay cell to the pinned base file, then add NER; preparation performs only the NER step. Otherwise use verified stored counts. |
| AI-GenT supplementary GPT-5 / GaMS-27B / gemma-2-27b | Copy the public analysis-ready `4y-gs`, default-prompt files. |

Sources, exact paths, licences and caveats are in
[`inputs/README.md`](inputs/README.md).

## Statistical outputs

Main statistics are in `outputs/data/statistical_tests.tsv`. The manually
reviewed and robustness analyses are kept separately under
`outputs/supplementary/` and are described in its local README. Run
`scripts/supplementary_manual_subset.py` and
`scripts/supplementary_robustness.py` to reproduce them.

## Run from a fresh clone

```bash
git clone https://github.com/hulln/sl-word-order-repro.git
cd sl-word-order-repro
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 scripts/compute_statistics.py
python3 scripts/supplementary_manual_subset.py
python3 scripts/supplementary_robustness.py
python3 scripts/make_figures.py
```

These commands recompute the summary, main statistical tests, all supplementary
checks, and seven figures from the included numerical tables. They need neither
corpora nor STARK. The robustness script takes roughly one minute on a typical
laptop because it performs the frozen 20,000-permutation checks.

## Rerun extraction

First obtain the corpus files described in [`inputs/README.md`](inputs/README.md).
Extraction also needs [STARK](https://github.com/clarinsi/STARK); the thesis used
commit `fd0202d` (`v3.1.0-3-gfd0202d`). Install its requirements in the same
environment, then run:

```bash
.venv/bin/pip install -r /path/to/STARK/requirements.txt
python3 scripts/run_all.py --stark /path/to/STARK/stark.py --use-reference-cache
```

This is not a fresh-clone command. The reference option covers ten corpora only;
SSJ, SST, the three SUK subsets and the three AI-GenT `4y-gs` files must already
exist under `prepared/`. Without `--use-reference-cache`, all 18 prepared files
are required. Only preparation steps that add CLASSLA NER need
`requirements-annotation.txt`.

## Limitations

- The full extraction cannot be completed from public sources alone: the exact
  SUK composite, four JANES conversions, JANES-Wiki preparation, KDSP preparation
  and human essay file are not distributed here.
- The SUK composite is wider than the public CoNLL-U release. Where comparison
  was possible, its query-relevant fields matched SUK 1.1.
- ParlaMint is rebuilt by concatenating the distributed CoNLL-U files in
  lexicographically sorted full-path order.
- The 691 human and GPT-5 essays are matched by document. GPT-5 syntax comes from
  AI-GenT; the human syntactic annotator remains undocumented in the available
  provenance evidence.
- The supplementary AI-GenT `4y-gs` comparison uses different generated texts
  and prompts. Its 205 GPT-5 source documents overlap the matched 691, so it is
  not an independent replication.
- Automatically labelled NER results are exploratory and classify only the
  argument head token.
- `all_pairwise` includes mechanical comparisons outside the thesis hypotheses.
  The prespecified tests are `h1_omnibus` and `h2_prespecified`.

## Licence and citation

Code and repository content: **GNU GPL version 3 or later**
([`LICENSE`](LICENSE); SPDX: `GPL-3.0-or-later`).

The GPL covers this repository only and grants no rights over any corpus. No
corpus files are distributed here; each keeps the licence of its original
release — listed in [`inputs/README.md`](inputs/README.md) — and several are
non-commercial or share-alike. To cite the package, see
[`CITATION.cff`](CITATION.cff).
