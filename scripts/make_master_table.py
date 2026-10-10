#!/usr/bin/env python3
"""Build thesis Table 4.1: the six S/V/O orders in all 18 analysed sources.

Input (read only): outputs/data/word_order_summary.tsv. Nothing is recomputed
from corpora; the script turns the stored counts into percentages, rounds the
stored entropies and lays the rows out in the order used in the thesis.

Outputs (in --out, by default outputs/tables/):
  word_order_overview.tex   the LaTeX table as printed in the thesis
  word_order_overview.tsv   the same rows with corpus IDs, counts, percentages,
                            entropy and short notes, readable without LaTeX

Row groups follow the thesis: I core comparison (SUK genre groups and SST),
II other analysed human sources, III supplementary case study (human and
GPT-5 essays, with the AI-GenT model comparison as an indented sub-block).
Robustness subsets are deliberately not rows.

This is the self-contained public form of the generator used for the thesis
(make_master_table_v2.py in the thesis repository). The table body it writes
is identical to the table in the thesis.

Usage:
  python3 scripts/make_master_table.py
"""

import argparse
import csv
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

PATTERNS = ["SVO", "SOV", "VSO", "VOS", "OSV", "OVS"]

GROUPS = {
    "I": "I. Osrednja primerjava",
    "II": "II. Drugi analizirani človeški viri",
    "III": "III. Dopolnilna študija primera: eseji (Šolar, AI-GenT 1.0)",
}
# LaTeX forms of the group III heading and of the AI-GenT sub-block heading.
LATEX_GROUP_III = r"III. Dopolnilna študija primera: eseji (\textit{Šolar}, \textit{AI-GenT}~1.0)"
LATEX_AIGENT_HEADER = r"primerjava modelov (205 esejev na model)\textsuperscript{b}"
SYNTAX_NOTE = (r"Skladenjske oznake so ročno pregledane v \textit{SSJ} in \textit{SST}, v \textit{SUK} "
               r"le v delu \mbox{\textit{ssj500k-syn}}; drugod so pripisane samodejno.")

# One row per analysed source, in display order:
# (group, corpus_id, label, syntax, role, note, marker, subordinate)
ROWS = [
    ("I", "suk-professional", "strokovno (SUK)", "mixed",
     "osrednja primerjava: žanrska skupina (H1, H2)",
     "SUK 1.1, žanrsko označeni del ssj500k; skladnja ročno pregledana le v delu ssj500k-syn", "", False),
    ("I", "suk-publicistic", "publicistično (SUK)", "mixed",
     "osrednja primerjava: žanrska skupina (H1, H2)",
     "kot zgoraj; skupine SUK se med seboj ne prekrivajo", "", False),
    ("I", "suk-literary", "leposlovno (SUK)", "mixed",
     "osrednja primerjava: žanrska skupina (H1, H2)",
     "kot zgoraj; majhen vzorec (54 dokumentov)", "", False),
    ("I", "sst", "spontani govor (SST)", "manual",
     "osrednja primerjava: pogovorno gradivo (H2); govorna stran referenčne primerjave SSJ–SST",
     "UD 2.18; 168 primerov v 83 govornih dogodkih; v tabeli naveden enkrat", "", False),
    ("II", "ssj", "SSJ (standardno pisno)", "manual",
     "referenčna drevesnica: primerjava dveh ročno pregledanih drevesnic (SSJ–SST)",
     "UD 2.18; večinoma iste ročno označene povedi kot ročno pregledani del skupin SUK "
     "(ssj500k-syn); ni neodvisna podatkovna točka; 194 skupnih povedi s CLASSLA-Wikipedia", "a", False),
    ("II", "janes-news", "Janes-News", "automatic",
     "opisna razširitev", "komentarji na novice; samodejna skladnja", "", False),
    ("II", "janes-blog", "Janes-Blog", "automatic",
     "opisna razširitev", "blogi in komentarji; samodejna skladnja", "", False),
    ("II", "janes-forum", "Janes-Forum", "automatic",
     "opisna razširitev", "forumi; samodejna skladnja", "", False),
    ("II", "janes-tweet", "Janes-Tweet", "automatic",
     "opisna razširitev", "tviti; samodejna skladnja", "", False),
    ("II", "janes-wiki", "Janes-Wiki (pogovorne strani)", "automatic",
     "opisna razširitev", "pogovorne strani Wikipedije; samodejna skladnja", "", False),
    ("II", "classla-wikipedia", "CLASSLA-Wikipedia (članki)", "automatic",
     "opisna razširitev", "članki Wikipedije (2020); distribuirana samodejna skladnja", "", False),
    ("II", "parlamint", "ParlaMint-SI", "automatic",
     "opisna razširitev", "uradni zapisi sej DZ (ParlaMint.ana 4.0); distribuirana samodejna skladnja", "", False),
    ("II", "kdsp", "KDSP", "automatic",
     "opisna razširitev: dopolnilo leposlovju, zunaj formalnih preizkusov",
     "zgodovinska pripovedna proza 1836–1918; samodejna skladnja", "", False),
    ("III", "human-essays", "človeški eseji", "automatic",
     "dopolnilna študija primera",
     "691 esejev 4. letnika (celica 4y-ss); označevalnik skladnje ni dokumentiran", "", False),
    ("III", "gpt5-essays", "eseji modela GPT-5", "automatic",
     "dopolnilna študija primera",
     "691 esejev, tvorjenih za iste naloge (poziv pap); Trankit (UD 2.15)", "", False),
    ("III", "aigent-gpt5", "GPT-5", "automatic",
     "dopolnilna primerjava modelov (podrejena študiji primera)",
     "celica 4y-gs, privzeti poziv; isti model kot zgoraj, 205 izhodiščnih dokumentov "
     "je med 691; ni neodvisna ponovitev", "", True),
    ("III", "aigent-gemma2-27b", "gemma-2-27b", "automatic",
     "dopolnilna primerjava modelov (podrejena študiji primera)",
     "istih 205 izhodiščnih dokumentov; Trankit (UD 2.15)", "", True),
    ("III", "aigent-gams27b", "GaMS-27B", "automatic",
     "dopolnilna primerjava modelov (podrejena študiji primera)",
     "istih 205 izhodiščnih dokumentov; Trankit (UD 2.15)", "", True),
]

# Golden numbers of the thesis (UD 2.18 treebanks and SUK genre groups).
GOLDEN = {"ssj": (1969, 1406), "sst": (168, 108)}
GOLDEN_TOTALS = {"suk-literary": 162, "suk-publicistic": 2837, "suk-professional": 1105}


def read_summary(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return {row["corpus_id"]: row for row in csv.DictReader(handle, delimiter="\t")}


def pct(count, total):
    """Percentage rounded half-up to one decimal, from the exact ratio."""
    value = Decimal(count) * 100 / Decimal(total)
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def round2(text):
    return Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def entropy(counts):
    total = sum(counts)
    return -sum(c / total * math.log(c / total) for c in counts if c > 0)


def sl_number(value):
    """Slovene decimal comma: 75.2 -> '75,2'."""
    return str(value).replace(".", ",")


def sl_int(value):
    """Slovene thousands separator: 1105 -> '1.105'."""
    return f"{value:,}".replace(",", ".")


def build_rows(summary, rows=ROWS):
    used = [row[1] for row in rows]
    if sorted(used) != sorted(summary) or len(set(used)) != len(used):
        raise SystemExit(f"Rows do not match the summary exactly: {sorted(set(summary) ^ set(used))}")

    table = []
    for group, cid, label, syntax, role, note, marker, sub in rows:
        src = summary[cid]
        counts = [int(src[f"{p}_n"]) for p in PATTERNS]
        total = int(src["total"])
        if sum(counts) != total:
            raise SystemExit(f"{cid}: counts do not add up to total")
        if abs(entropy(counts) - float(src["entropy_nat"])) > 5e-7:
            raise SystemExit(f"{cid}: stored entropy does not match the counts")
        if src["dominant_flag"] != "dominant" or src["dominant_order"] != "SVO":
            raise SystemExit(f"{cid}: SVO is not flagged as dominant; footnote would be wrong")
        percents = [pct(c, total) for c in counts]
        if abs(sum(percents) - 100) > Decimal("0.3"):
            raise SystemExit(f"{cid}: rounded percentages sum to {sum(percents)}")
        table.append({
            "group": group, "corpus_id": cid, "label": label, "syntax": syntax,
            "role": role, "note": note, "marker": marker, "sub": sub,
            "n": total, "counts": counts, "percents": percents,
            "entropy": round2(src["entropy_nat"]), "entropy_nat": src["entropy_nat"],
        })

    for cid, (n, svo) in GOLDEN.items():
        row = next(r for r in table if r["corpus_id"] == cid)
        if (row["n"], row["counts"][0]) != (n, svo):
            raise SystemExit(f"Golden number mismatch for {cid}")
    for cid, n in GOLDEN_TOTALS.items():
        if next(r for r in table if r["corpus_id"] == cid)["n"] != n:
            raise SystemExit(f"Golden number mismatch for {cid}")
    return table


def write_tsv(table, path):
    header = (["row", "group", "group_label", "subordinate", "marker", "corpus_id", "label", "role",
               "syntax", "n"] + [f"{p}_n" for p in PATTERNS] + [f"{p}_pct" for p in PATTERNS]
              + ["entropy_2dp", "entropy_nat", "note"])
    with open(path, "w", encoding="utf-8", newline="") as handle:
        out = csv.writer(handle, delimiter="\t", lineterminator="\n")
        out.writerow(header)
        for number, row in enumerate(table, start=1):
            out.writerow([number, row["group"], GROUPS[row["group"]], "yes" if row["sub"] else "no",
                          row["marker"], row["corpus_id"], row["label"], row["role"], row["syntax"],
                          row["n"]] + row["counts"] + [str(p) for p in row["percents"]]
                         + [str(row["entropy"]), row["entropy_nat"], row["note"]])


def write_latex(table, path):
    lines = [
        "% Thesis Table 4.1, generated by scripts/make_master_table.py from",
        "% outputs/data/word_order_summary.tsv. Do not edit by hand.",
        r"\providecommand{\podrejeno}[1]{\textcolor{black!70}{#1}}",
        r"\begin{table}[htbp]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{3.5pt}",
        r"\begin{tabular}{@{}lrrrrrrr@{\hspace{1.4em}}r@{}}",
        r"\toprule",
        r"\textbf{Vir / podkorpus} & $n$ & " + " & ".join(rf"\textbf{{{p}}}" for p in PATTERNS)
        + r" & \shortstack[c]{\textbf{Entro-}\\\textbf{pija}} \\",
        r" & & " + " & ".join([r"\%"] * 6) + r" & \\",
        r"\midrule",
    ]
    current = None
    for row in table:
        if row["group"] != current:
            if current is not None:
                lines.append(r"\addlinespace[4pt]")
            current = row["group"]
            heading = LATEX_GROUP_III if current == "III" else GROUPS[current]
            lines.append(rf"\multicolumn{{9}}{{@{{}}l}}{{\textbf{{{heading}}}}} \\")
        if row["corpus_id"] == "aigent-gpt5":
            lines.append(rf"\multicolumn{{9}}{{@{{}}l}}{{\hspace{{1em}}\podrejeno{{{LATEX_AIGENT_HEADER}}}}} \\")
        marker = rf"\textsuperscript{{{row['marker']}}}" if row["marker"] else ""
        values = [sl_int(row["n"])] + [sl_number(p) for p in row["percents"]] + [sl_number(row["entropy"])]
        values[1] = rf"\textbf{{{values[1]}}}"
        cells = [row["label"] + marker] + values
        if row["sub"]:
            cells = [r"\hspace{2em}" + rf"\podrejeno{{{cells[0]}}}"] + [rf"\podrejeno{{{c}}}" for c in cells[1:]]
        lines.append(" & ".join(cells) + r" \\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\caption[Porazdelitev besednorednih vzorcev v vseh analiziranih virih]"
        r"{Porazdelitev šestih besednorednih vzorcev in entropija v vseh analiziranih virih; "
        r"$n$ označuje število izluščenih parov osebka in predmeta.}",
        r"\label{tab:pregled-virov}",
        r"\par\smallskip",
        r"\begin{minipage}{\linewidth}\footnotesize",
        r"Shannonova entropija uporablja naravni logaritem; pri šestih enako pogostih vzorcih doseže "
        r"največjo vrednost $\ln 6 \approx 1{,}79$. " + SYNTAX_NOTE,
        r"\par\smallskip",
        r"\textsuperscript{a}~\textit{SSJ} se v veliki meri prekriva z ročno pregledanim delom \textit{SUK} "
        r"(\mbox{\textit{ssj500k-syn}}), zato rezultati niso neodvisni potrditvi.",
        r"\par",
        r"\textsuperscript{b}~Po 205 ločeno tvorjenih esejev na podlagi metapodatkov 205 človeških esejev iz "
        r"nabora 691 parov človek--GPT-5; primerjava modelov zato ni neodvisna ponovitev na drugem gradivu.",
        r"\end{minipage}",
        r"\end{table}",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=here.parent,
                        help="root of the sl-word-order-repro package")
    parser.add_argument("--out", type=Path, default=here.parent / "outputs" / "tables",
                        help="output directory (default: outputs/tables)")
    args = parser.parse_args()

    summary = read_summary(args.repo / "outputs" / "data" / "word_order_summary.tsv")
    table = build_rows(summary)
    args.out.mkdir(parents=True, exist_ok=True)
    write_latex(table, args.out / "word_order_overview.tex")
    write_tsv(table, args.out / "word_order_overview.tsv")
    print(f"{len(table)} rows written to {args.out}")


if __name__ == "__main__":
    main()
