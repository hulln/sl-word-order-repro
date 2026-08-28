# Prepared corpora

`prepared/` is where the canonical CoNLL-U files read by the analysis scripts
belong. No CoNLL-U file is tracked in Git. `checksums.sha256` covers only the
locally materialized `.conllu` files, with paths relative to this directory. The
authoritative prepared hash and count inventory for all 18 corpora is
`config/corpora.tsv`.

`scripts/prepare_corpora.py` builds files when a supported source is available,
then checks CoNLL-U structure, sentence count, SHA-256 and required NER tags.
`expected_sentences` is the number of non-empty, blank-line-delimited CoNLL-U
blocks in the prepared file, including comment-only blocks, and is used for
validation. Corpus sizes quoted in the thesis count only blocks containing at
least one word/token row. The resulting manifest-minus-thesis differences are
0 for JANES-News, +7,371 for JANES-Blog, +25,160 for JANES-Forum, +1 for
JANES-Tweet and 0 for JANES-Wiki. Comment-only blocks cannot contribute S/V/O
instances and therefore do not affect the thesis results.
Blank validation fields in `config/corpora.tsv` are skipped, not guessed.

```bash
python3 scripts/prepare_corpora.py
python3 scripts/prepare_corpora.py --download-ud --force
```

The second command rebuilds SSJ and SST; SST needs
`requirements-annotation.txt`. Add `--require-all` to fail unless every one of
the 18 prepared files is present. See [`../inputs/README.md`](../inputs/README.md)
for acquisition and preparation details.

## Validation-field status

🟢 **Recorded** = the prepared count and SHA-256 are recorded.

| Corpus | Manifest validation status |
|---|---|
| All 18 corpora | 🟢 Prepared count and SHA-256 recorded. |

Prepared-file fingerprints may identify retained converted or concatenated files
that differ from public source distributions.

For the Human/GPT-5 essay pair, the prepared hashes identify canonical
reconstructions from the exact base inputs and CLASSLA 2.2.1 standard NER model
[`11356/2014/ner`](https://hdl.handle.net/11356/2014/ner). They reproduce the
thesis analysis but do not prove byte-for-byte identity with the lost historical
NER-enriched derivatives.
