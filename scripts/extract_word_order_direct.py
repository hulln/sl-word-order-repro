#!/usr/bin/env python3
"""Direct S/V/O extraction from a CoNLL-U file.

For every VERB that governs a NOUN subject
(`nsubj`) and a NOUN object (`obj`), classify the linear order of S/V/O as one of
SVO/SOV/VSO/VOS/OSV/OVS. ``--label`` assigns one corpus label to the input.
Without it, labels are read from SUK's ``# term = zvrst / ...`` metadata, which
also lets this utility inspect a combined SUK source during input preparation.

This mirrors the STARK NOUN-only query `upos=VERB >nsubj upos=NOUN >obj upos=NOUN`
and uses the matching definition independently validated against STARK:
- subject deprel must be exactly `nsubj` (no subtypes such as `nsubj:pass`);
- object deprel must be exactly `obj`;
- when a verb has several matching subjects/objects, EVERY subject x object pair
  counts as one instance (STARK counts each matched subtree).
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from pathlib import Path

WORD_ORDERS = ["SVO", "SOV", "VSO", "VOS", "OSV", "OVS"]


def genre_of_term(line: str) -> str | None:
    if "zvrst / umetnostna" in line:
        return "leposlovno"        # literary
    if "zvrst / neumetnostna / strokovna" in line:
        return "strokovno"         # specialised/expert
    if "zvrst / neumetnostna / nestrokovna" in line:
        return "publicisticno_splosno"  # journalistic/general non-fiction
    return None


def classify(s_id: int, v_id: int, o_id: int) -> str:
    order = sorted([(s_id, "S"), (v_id, "V"), (o_id, "O")])
    return "".join(tag for _, tag in order)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True, help="CoNLL-U input")
    ap.add_argument("--out", type=Path, required=True, help="word-order count table")
    ap.add_argument(
        "--label",
        default=None,
        help="use one corpus label for the whole file; otherwise read SUK genre metadata",
    )
    args = ap.parse_args()

    counts: dict[str, Counter] = defaultdict(Counter)
    genre: str | None = args.label  # if --label given, one fixed group for the whole file
    # per-sentence token store: id -> (upos, deprel, head)
    upos: dict[int, str] = {}
    deprel: dict[int, str] = {}
    head: dict[int, int] = {}

    def flush_sentence():
        if genre is None or not upos:
            return
        # children of each verb by relation
        for vid, vpos in upos.items():
            if vpos != "VERB":
                continue
            subj = [i for i in upos if head.get(i) == vid and deprel[i] == "nsubj" and upos[i] == "NOUN"]
            obj = [i for i in upos if head.get(i) == vid and deprel[i] == "obj" and upos[i] == "NOUN"]
            for s_id in subj:
                for o_id in obj:
                    counts[genre][classify(s_id, vid, o_id)] += 1

    with args.input.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("#"):
                if args.label is None:  # only auto-detect genre when no fixed label
                    if line.startswith("# newdoc"):
                        genre = None
                    elif line.startswith("# term ="):
                        g = genre_of_term(line)
                        if g:
                            genre = g
                continue
            if not line.strip():
                flush_sentence()
                upos, deprel, head = {}, {}, {}
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 8 or not cols[0].isdigit():
                continue
            i = int(cols[0])
            upos[i] = cols[3]
            deprel[i] = cols[7]
            head[i] = int(cols[6]) if cols[6].isdigit() else 0
        flush_sentence()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as w:
        w.write("corpus\tpattern\tcount\ttotal\tproportion\n")
        for g in sorted(counts):
            total = sum(counts[g].values())
            for pat in WORD_ORDERS:
                c = counts[g][pat]
                prop = c / total if total else 0.0
                w.write(f"{g}\t{pat}\t{c}\t{total}\t{prop:.6f}\n")
    # console summary
    for g in sorted(counts):
        total = sum(counts[g].values())
        svo = counts[g]["SVO"]
        print(f"{g:24s} n={total:6d}  SVO={svo:6d} ({100*svo/total:.1f}%)" if total else f"{g}: n=0")


if __name__ == "__main__":
    main()
