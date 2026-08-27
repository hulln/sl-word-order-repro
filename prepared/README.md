# Canonical prepared corpora

This directory contains the exact CoNLL-U files that analysis scripts read.
They are generated or validated by `scripts/prepare_corpora.py`; scripts under
the analysis/statistics stages never read raw `inputs/`.

Currently shipped and fully analyzable:

- UD 2.18 SSJ, merged train+dev+test;
- UD 2.18 SST, merged train+dev+test with CLASSLA 2.2.1 NER added without
  changing tokenization or syntax;
- three SUK 1.1-derived genre analysis corpora;
- three distributed AI-GenT 1.0 Slovenian `4y-gs` default-prompt corpora.

`checksums.sha256` is regenerated from all prepared files currently present.
The manifest pins both a SHA-256 and a sentence count for each of the eight
shipped corpora. It also pins a SHA-256 for the four JANES corpora and a
sentence count for the two essay files, none of which are shipped but all of
which are exactly identified. Only four rows — JANES-Wiki, CLASSLA-Wikipedia,
ParlaMint-SI and KDSP — are pinned by neither; see `inputs/README.md` for the
truncated fingerprints recorded for those.

Missing large/restricted corpora are never silently fabricated; full analysis
fails unless their prepared files exist, while explicit lightweight mode uses
documented aggregate caches from `reference/`.

To validate existing files:

```bash
python3 scripts/prepare_corpora.py
```

To fetch and rebuild the two UD resources (CLASSLA 2.2.1 is required for SST):

```bash
python3 scripts/prepare_corpora.py --download-ud --force
```

Use `--require-all` when every one of the 18 prepared corpora must be available.
