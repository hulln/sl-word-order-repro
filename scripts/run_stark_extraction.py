#!/usr/bin/env python3
"""Run the STARK word-order query on one CoNLL-U corpus.

This script does three things:
  1. split files that are too large for STARK at sentence boundaries;
  2. run STARK on every chunk with exactly the main analysis settings (a verb
     with nominal subject and object heads); and
  3. classify STARK matches into the six word-order patterns and write a
     temporary table for the canonical result builder.

The main builder compares this result with the independent direct extractor
and requires exact agreement for every pattern and for the total.
"""
from __future__ import annotations
import argparse
import csv
import subprocess
import sys
from pathlib import Path

# Query and patterns: changing these would make results incomparable.
POIZVEDBA = "upos=VERB >nsubj upos=NOUN >obj upos=NOUN"
VZORCI = ["SVO", "SOV", "VSO", "VOS", "OSV", "OVS"]


def razdeli_na_kose(vhod: Path, mapa: Path, max_mb: float) -> list[Path]:
    """Split a large file into approximately ``max_mb`` chunks.

    Chunks always end at a blank-line sentence boundary. Sentences are also
    cleaned for STARK, which stops on a missing dependency head: a root written
    as ``HEAD=_`` is changed to ``HEAD=0`` (the same technical case occurs in
    SUK), while a sentence containing any other integer-ID token without a
    numeric head is skipped and counted. Such a sentence cannot match the query
    because its dependency relations are absent. The skipped count is reported
    so its impact can be checked.
    """
    mapa.mkdir(parents=True, exist_ok=True)
    kosi: list[Path] = []
    vrstice: list[str] = []
    velikost = 0
    max_b = int(max_mb * 1024 * 1024)
    poved: list[str] = []
    cakajoci_komentarji: list[str] = []  # comment block waiting for its sentence
    popravljeni_koreni = 0
    popravljene_oznake = 0
    izpuscene_povedi = 0

    def zapisi():
        nonlocal vrstice, velikost
        if not vrstice:
            return
        pot = mapa / f"kos_{len(kosi)+1:04d}.conllu"
        pot.write_text("".join(vrstice), encoding="utf-8")
        kosi.append(pot)
        vrstice, velikost = [], 0

    def ociscena_poved(p: list[str]) -> list[str] | None:
        """Return a cleaned sentence, or ``None`` when it must be skipped.

        The query reads only UPOS and DEPREL, so these cleanups are safe:
          - skip a sentence containing a token row without exactly 10 columns;
          - replace invalid FEATS/DEPS (for example a bare MSD tag) with ``_``;
          - change a root with ``HEAD=_`` to 0, but skip any other headless token.
        """
        nonlocal popravljeni_koreni, popravljene_oznake
        cista: list[str] = []
        for v in p:
            if not v.startswith("#") and v.strip():
                cols = v.rstrip("\n").split("\t")
                if len(cols) != 10:
                    return None  # not a valid CoNLL-U row
                spremenjena = False
                if cols[5] != "_" and "=" not in cols[5]:  # FEATS is _ or Name=Value
                    cols[5] = "_"; popravljene_oznake += 1; spremenjena = True
                if cols[8] != "_" and ":" not in cols[8]:  # DEPS is _ or head:relation
                    cols[8] = "_"; spremenjena = True
                if cols[0].isdigit() and not cols[6].isdigit():
                    if cols[7] == "root" and cols[6] == "_":
                        cols[6] = "0"; popravljeni_koreni += 1; spremenjena = True
                    else:
                        return None  # a headless token means syntax is absent
                if spremenjena:
                    v = "\t".join(cols) + "\n"
            cista.append(v)
        return cista

    def sprejmi_poved():
        nonlocal poved, velikost, izpuscene_povedi, cakajoci_komentarji
        if not poved:
            return
        # A comment-only block (for example a separate ``# newdoc`` block in
        # tweets) cannot stand alone: pyconll would create a tokenless sentence
        # and STARK would stop. Attach it to the next sentence instead.
        if all(v.startswith("#") for v in poved):
            cakajoci_komentarji.extend(poved)
            poved = []
            return
        blok = cakajoci_komentarji + poved
        cakajoci_komentarji = []
        cista = ociscena_poved(blok)
        poved = []
        if cista is None:
            izpuscene_povedi += 1
            return
        for v in cista:
            vrstice.append(v)
            velikost += len(v.encode("utf-8"))
        vrstice.append("\n")
        if velikost >= max_b:
            zapisi()

    with vhod.open(encoding="utf-8-sig") as f:  # utf-8-sig removes an optional BOM
        for vrstica in f:
            if not vrstica.strip():
                sprejmi_poved()
                continue
            poved.append(vrstica)
        sprejmi_poved()
    zapisi()
    if popravljeni_koreni or izpuscene_povedi or popravljene_oznake:
        print(f"  cleaning: corrected roots {popravljeni_koreni}, "
              f"corrected FEATS tags {popravljene_oznake}, "
              f"skipped sentences {izpuscene_povedi}")
    return kosi


def pozeni_stark(stark_py: Path, vhod: Path, izhod: Path, shramba: Path) -> None:
    """Run STARK on one file with the public word-order analysis settings."""
    ukaz = [sys.executable, str(stark_py),
            "--input", str(vhod), "--output", str(izhod),
            "--internal_saves", str(shramba),
            "--query", POIZVEDBA,
            "--node_type", "form", "--labeled", "yes", "--label_subtypes", "no",
            "--fixed", "yes", "--complete", "no", "--greedy_counter", "no",
            "--processing_size", "3", "--node_info", "yes", "--head_info", "yes",
            "--grew_match", "no", "--depsearch", "no",
            "--association_measures", "no", "--complexity_measures", "no",
            "--example", "no"]
    rezultat = subprocess.run(ukaz, capture_output=True, text=True)
    if rezultat.returncode != 0:
        sys.exit(f"STARK failed on {vhod}:\n{rezultat.stderr[-2000:]}")


OZNAKE = {"<nsubj": "S", ">nsubj": "S", "<obj": "O", ">obj": "O"}


def razvrsti_drevo(drevo: str) -> str:
    """Classify STARK's linear tree string into one of the six patterns.

    Only the exact tokens ``<nsubj``, ``>nsubj``, ``<obj``, and ``>obj`` count
    as relation markers. Everything else is text, including strings such as
    ``>>`` or ``<b>`` that occur in web material. A ``>rel`` marker applies to
    the next word, a ``<rel`` marker to the previous word, and an unmarked word
    is the verbal head (V).
    """
    oblike: list[str] = []   # word sequence, with one S/V/O role per word
    cakajoca: str | None = None  # role from ``>rel``, waiting for the next word
    for b in str(drevo).split():
        if b in OZNAKE:
            if b.startswith(">"):
                cakajoca = OZNAKE[b]
            else:  # ``<rel`` marks the preceding word
                if not oblike:
                    return ""
                oblike[-1] = OZNAKE[b]
        else:
            oblike.append(cakajoca if cakajoca else "V")
            cakajoca = None
    if len(oblike) != 3:
        return ""  # for example a token containing a space; skip and warn
    vzorec = "".join(oblike)
    return vzorec if vzorec in VZORCI else ""


def prestej(stark_tsv: Path, stevci: dict[str, int]) -> int:
    """Sum pattern frequencies from a STARK output table."""
    preskocenih = 0
    with stark_tsv.open(encoding="utf-8") as f:
        beri = csv.DictReader(f, delimiter="\t")
        for vrstica in beri:
            vzorec = razvrsti_drevo(vrstica["Tree"])
            if vzorec:
                stevci[vzorec] += int(vrstica["Absolute frequency"])
            else:
                preskocenih += 1
    return preskocenih


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True, help="CoNLL-U file")
    ap.add_argument("--label", required=True, help="public corpus name")
    ap.add_argument("--stark", type=Path, required=True, help="path to STARK/stark.py")
    ap.add_argument("--workdir", type=Path, required=True,
                    help="working directory for chunks and intermediate files (large disk needed)")
    ap.add_argument("--out", type=Path, required=True, help="output TSV table")
    ap.add_argument("--max-mb", type=float, default=50,
                    help="maximum chunk size in MB (default: 50)")
    args = ap.parse_args()

    delo = args.workdir
    delo.mkdir(parents=True, exist_ok=True)

    # 1) Split and clean. Small files take the same path for consistent
    # cleaning and simply produce one chunk.
    print(f"{args.label}: splitting into {args.max_mb} MB chunks and cleaning ...")
    kosi = razdeli_na_kose(args.input, delo / "kosi", args.max_mb)
    print(f"{args.label}: {len(kosi)} chunks")

    # 2) Run STARK on each chunk; 3) accumulate pattern counts as it runs.
    stevci = {v: 0 for v in VZORCI}
    preskocenih = 0
    for i, kos in enumerate(kosi, 1):
        izhod = delo / f"stark_{i:04d}.tsv"
        if not izhod.exists():  # resume an interrupted run by keeping finished chunks
            pozeni_stark(args.stark, kos, izhod, delo / "shramba")
        preskocenih += prestej(izhod, stevci)
        print(f"  chunk {i}/{len(kosi)} complete", flush=True)
    if preskocenih:
        print(f"WARNING: skipped {preskocenih} unclassifiable matches")

    # Write a temporary table with the direct extractor's basic schema.
    skupaj = sum(stevci.values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as w:
        w.write("corpus\tpattern\tcount\ttotal\tproportion\n")
        for v in VZORCI:
            delez = stevci[v] / skupaj if skupaj else 0.0
            w.write(f"{args.label}\t{v}\t{stevci[v]}\t{skupaj}\t{delez:.6f}\n")
    svo_percentage = 100 * stevci["SVO"] / skupaj if skupaj else 0.0
    print(f"{args.label}: n={skupaj}, SVO={stevci['SVO']} "
          f"({svo_percentage:.1f}%) -> {args.out}")


if __name__ == "__main__":
    main()
