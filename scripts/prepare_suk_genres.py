#!/usr/bin/env python3
"""Split combined_suk.conllu into one CoNLL-U file per SUK genre (zvrst).

STARK processes whole files and cannot group by SUK's `# term = zvrst / ...`
document metadata, so the STARK-per-genre run needs physical per-genre files.
Uses the same genre mapping as `extract_word_order_direct.py`. The values
`leposlovno`, `strokovno`, and `publicisticno_splosno` are source-metadata
labels for literary, professional, and publicistic/general material.
Documents without a mapped genre are skipped and reported. Document boundaries
(`# newdoc`) reset the genre.

Output: <outdir>/suk_<genre>.conllu + a per-genre sentence count on stdout.

Data quirk handled here (verified on combined_suk, 2026-07-08): in the ssj
docs beyond the UD-SSJ export (ssj1001+), root tokens are written with
HEAD=`_` + DEPREL=`root` instead of HEAD=`0`. The trees are otherwise
complete, but they are NOT gold: these are the `ssj500k-tag` documents, which
the official SUK release distributes without manually checked syntax (and
without NER), so their parses were added automatically during data
preparation. STARK (via pyconll) crashes on the empty HEAD, so this
script always repairs `HEAD=_` + `DEPREL=root` to `HEAD=0` (all genre-mapped
SUK sentences are fully annotated after this repair — there are no partially
or fully unannotated genre-mapped sentences).

--require-syntax additionally drops sentences that still contain a
non-numeric HEAD after the repair (a safety net for other inputs; on
combined_suk it drops nothing).
"""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path

from extract_word_order_direct import genre_of_term


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True, help="combined_suk.conllu")
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--require-syntax", action="store_true",
                    help="keep only sentences where every token has a numeric HEAD "
                         "(needed for STARK; does not change dependency-query counts)")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    handles: dict[str, object] = {}
    sent_counts: Counter = Counter()
    skipped_sents = 0

    def handle(genre: str):
        if genre not in handles:
            handles[genre] = (args.outdir / f"suk_{genre}.conllu").open("w", encoding="utf-8")
        return handles[genre]

    genre: str | None = None
    sentence: list[str] = []
    has_syntax = True
    no_syntax_sents = 0

    def flush():
        nonlocal skipped_sents, no_syntax_sents
        if not sentence:
            return
        # count only real sentences (blocks with at least one token line)
        has_tokens = any(not l.startswith("#") and l.strip() for l in sentence)
        if genre is None:
            if has_tokens:
                skipped_sents += 1
        elif args.require_syntax and has_tokens and not has_syntax:
            no_syntax_sents += 1
        else:
            handle(genre).write("".join(sentence) + "\n")
            if has_tokens:
                sent_counts[genre] += 1

    with args.input.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("# newdoc"):
                genre = None
            elif line.startswith("# term ="):
                g = genre_of_term(line)
                if g:
                    genre = g
            if not line.strip():
                flush()
                sentence = []
                has_syntax = True
                continue
            if not line.startswith("#"):
                cols = line.rstrip("\n").split("\t")
                if len(cols) >= 8 and cols[0].isdigit() and not cols[6].isdigit():
                    if cols[7] == "root" and cols[6] == "_":
                        cols[6] = "0"  # repair: root written as HEAD=_ in ssj1001+
                        line = "\t".join(cols)
                        if not line.endswith("\n"):
                            line += "\n"
                    else:
                        has_syntax = False
            sentence.append(line)
        flush()

    for h in handles.values():
        h.close()
    for g in sorted(sent_counts):
        print(f"{g:26s} {sent_counts[g]:7d} sentences -> suk_{g}.conllu")
    print(f"{'(no mapped genre, skipped)':26s} {skipped_sents:7d} sentences")
    if args.require_syntax:
        print(f"{'(genre ok, no syntax, skipped)':30s} {no_syntax_sents:7d} sentences")


if __name__ == "__main__":
    main()
