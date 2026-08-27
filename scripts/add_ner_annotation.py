#!/usr/bin/env python3
"""Add CLASSLA NER tags to an existing CoNLL-U file's MISC column, in place-safe copy.

For corpora that carry (gold or automatic) syntax but no NER layer (in this
thesis: gold SST and the human/AI essays). The existing tokenization,
sentence segmentation and trees are NOT touched: sentences are fed to
CLASSLA-Stanza *pretokenized*, only the `ner` output is merged back as
`NER=<tag>` in MISC. Token alignment is positional (pretokenized mode
guarantees 1:1). Multiword-token range lines and empty nodes are passed
through unchanged (no NER).

The `--type` flag selects the CLASSLA model variant (standard | nonstandard);
for spoken transcripts (SST, lowercase, no punctuation) NER quality is
expectedly lower — treat downstream results as exploratory.
"""
from __future__ import annotations
import argparse
from pathlib import Path

import classla


def read_sentences(path: Path):
    """Yield lists of raw lines per sentence block (comments + tokens)."""
    block: list[str] = []
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():
                if block:
                    yield block
                    block = []
                continue
            block.append(line.rstrip("\n"))
    if block:
        yield block


def token_lines(block: list[str]) -> list[int]:
    """Indices of simple token lines (integer ID) within a block."""
    idx = []
    for i, line in enumerate(block):
        if line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= 10 and cols[0].isdigit():
            idx.append(i)
    return idx


def set_misc_ner(line: str, ner: str) -> str:
    cols = line.split("\t")
    misc = cols[9]
    parts = [p for p in (misc.split("|") if misc != "_" else []) if not p.upper().startswith("NER=")]
    parts.append(f"NER={ner}")
    cols[9] = "|".join(parts)
    return "\t".join(cols)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--type", default="standard", choices=["standard", "standard_jos", "nonstandard"],
                    help="CLASSLA model variant (default: standard)")
    ap.add_argument("--batch-sents", type=int, default=2000, help="sentences per pipeline call")
    args = ap.parse_args()

    nlp = classla.Pipeline("sl", type=args.type, processors="tokenize,ner",
                           tokenize_pretokenized=True, use_gpu=False)

    blocks = list(read_sentences(args.input))
    print(f"{len(blocks)} sentences")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as w:
        for start in range(0, len(blocks), args.batch_sents):
            batch = blocks[start:start + args.batch_sents]
            tok_idx = [token_lines(b) for b in batch]
            pretok = [[b[i].split("\t")[1] for i in idx] for b, idx in zip(batch, tok_idx) if idx]
            doc = nlp(pretok) if pretok else None
            di = 0
            for b, idx in zip(batch, tok_idx):
                if idx:
                    sent = doc.sentences[di]; di += 1
                    assert len(sent.tokens) == len(idx), "pretokenized alignment broke"
                    for line_i, tok in zip(idx, sent.tokens):
                        b[line_i] = set_misc_ner(b[line_i], tok.ner or "O")
                w.write("\n".join(b) + "\n\n")
            print(f"  {min(start + args.batch_sents, len(blocks))}/{len(blocks)}", flush=True)


if __name__ == "__main__":
    main()
