#!/usr/bin/env python3
"""Explain exact-text ParlaMint duplication, without modifying corpus or thesis.

Python >=3.10; standard library only. Keep dedup_sensitivity.py beside this
script: its sentence reader and unchanged canonical extractor wrapper are reused
directly. Verify the fixed input/extractor hashes, then stream one extraction
pass into a disposable SQLite database (64 MiB cache). Publish only the two
requested reports, after reconciling all counts with the completed dedup run.

Identity is exactly the completed run's # text content / integer-FORM fallback.
All repeated types, including zero-instance types, are exported. Every later
occurrence is extracted independently: equal text need not imply equal parses.
The requested (occurrences-1)*first vector and the actual later-occurrence vector
are both shown, with per-vector frequencies whenever they differ.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from dedup_sensitivity import (
    INPUTS, PATTERNS, Progress, entropy, file_sha256, fingerprint,
    load_extractor, read_table, sentences, verify_unchanged,
)

INPUT_SHA256 = INPUTS["parlamint"][1]
EXTRACTOR_SHA256 = "2276cbbc7317e7d1c11848be2c8c9c4e790df0585653c19e68a059c320a982a3"
EXPECTED_BEFORE = (337886, 31837, 18345, 17326, 10377, 81801)
EXPECTED_AFTER = (326388, 30434, 17386, 14801, 10014, 54788)
EXPECTED_SENTENCES = 3876183
EXPECTED_UNIQUE = 3133122
EXAMPLES_NAME = "parlamint_duplicate_examples.tsv"
REPORT_NAME = "parlamint_duplicate_audit.txt"
FIELDS = (
    ["sentence_text", "first_sentence_index", "occurrences", "fallback_occurrences",
     "count_vectors_identical", "later_occurrences_with_different_counts",
     "pattern_count_variants_json", "first_total", "excess_total",
     "nominal_excess_total"]
    + [f"first_{p}" for p in PATTERNS]
    + [f"excess_{p}" for p in PATTERNS]
    + [f"nominal_excess_{p}" for p in PATTERNS]
)


def log(message):
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{stamp}] {message}", file=sys.stderr, flush=True)


def create_database(db):
    # Disposable scratch: do not resume it after interruption.
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA synchronous=OFF")
    db.execute("PRAGMA cache_size=-65536")
    db.execute("PRAGMA temp_store=FILE")
    columns = ", ".join(
        [f"first_{p} INTEGER NOT NULL" for p in PATTERNS]
        + [f"excess_{p} INTEGER NOT NULL DEFAULT 0" for p in PATTERNS]
    )
    db.execute(f"""CREATE TABLE sentence (
        identity BLOB PRIMARY KEY,
        first_sentence_index INTEGER NOT NULL,
        occurrences INTEGER NOT NULL DEFAULT 1,
        fallback_occurrences INTEGER NOT NULL,
        mismatches INTEGER NOT NULL DEFAULT 0,
        {columns}
    ) WITHOUT ROWID""")
    # Only later vectors that differ from the first need this extra table.
    db.execute("""CREATE TABLE variant (
        identity BLOB NOT NULL, vector TEXT NOT NULL, occurrences INTEGER NOT NULL,
        PRIMARY KEY (identity, vector)
    ) WITHOUT ROWID""")


def scan_duplicates(path, extract, db, interval=30):
    before, after = [0] * 6, [0] * 6
    total = unique = fallback = 0
    insert = (
        "INSERT OR IGNORE INTO sentence "
        "(identity, first_sentence_index, fallback_occurrences, "
        + ", ".join(f"first_{p}" for p in PATTERNS)
        + ") VALUES (" + ",".join("?" for _ in range(9)) + ")"
    )
    select = "SELECT " + ", ".join(f"first_{p}" for p in PATTERNS) + " FROM sentence WHERE identity=?"
    update = (
        "UPDATE sentence SET occurrences=occurrences+1, "
        "fallback_occurrences=fallback_occurrences+?, mismatches=mismatches+?, "
        + ", ".join(f"excess_{p}=excess_{p}+?" for p in PATTERNS)
        + " WHERE identity=?"
    )
    progress = Progress(f"{path.name} duplicate audit", path.stat().st_size, interval, log)
    for identity, missing, upos, deprel, head, done in sentences(path):
        total += 1
        fallback += missing
        counter = extract(upos, deprel, head)
        counts = tuple(counter[p] for p in PATTERNS)
        if any(n < 0 for n in counts) or sum(counts) != sum(counter.values()):
            raise ValueError("Unexpected canonical count categories")
        for i, n in enumerate(counts):
            before[i] += n
        key = identity.encode("utf-8")
        inserted = db.execute(insert, (key, total, int(missing), *counts)).rowcount == 1
        if inserted:
            unique += 1
            for i, n in enumerate(counts):
                after[i] += n
        else:
            first = db.execute(select, (key,)).fetchone()
            different = counts != first
            db.execute(update, (int(missing), int(different), *counts, key))
            if different:
                db.execute(
                    """INSERT INTO variant VALUES (?, ?, 1)
                    ON CONFLICT(identity, vector)
                    DO UPDATE SET occurrences=occurrences+1""",
                    (key, json.dumps(counts, separators=(",", ":"))),
                )
        if total % 10000 == 0:
            db.commit()
            progress.update(done, f"sentences={total:,}, unique={unique:,}")
    db.commit()
    progress.update(path.stat().st_size, f"sentences={total:,}, unique={unique:,}", final=True)
    return dict(sentences=total, unique=unique, fallback=fallback,
                before=before, after=after)


def variant_record(counts, occurrences, retained):
    return dict(occurrences=occurrences, retained_occurrences=retained,
                counts=dict(zip(PATTERNS, counts)),
                excess_counts={p: (occurrences - retained) * n
                               for p, n in zip(PATTERNS, counts)})


def write_examples(db, path, stats):
    """Stream the full TSV; retain only 30 examples per ranking in memory."""
    columns = (
        "identity, first_sentence_index, occurrences, fallback_occurrences, mismatches, "
        + ", ".join(f"first_{p}" for p in PATTERNS) + ", "
        + ", ".join(f"excess_{p}" for p in PATTERNS)
    )
    heaps = {metric: [] for metric in ("excess_total", "excess_OVS", "excess_SVO")}
    removed, nominal_removed = [0] * 6, [0] * 6
    repeated_types = repeated_copies = mismatch_types = mismatch_occurrences = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for values in db.execute(f"SELECT {columns} FROM sentence WHERE occurrences > 1"):
            key, first_index, occurrences, fallback, mismatches = values[:5]
            first, excess = values[5:11], values[11:17]
            nominal = tuple((occurrences - 1) * n for n in first)
            variants = [variant_record(first, occurrences - mismatches, 1)]
            if mismatches:
                for vector, frequency in db.execute(
                    "SELECT vector, occurrences FROM variant WHERE identity=? ORDER BY vector", (key,)
                ):
                    variants.append(variant_record(json.loads(vector), frequency, 0))
            if sum(v["occurrences"] for v in variants) != occurrences:
                raise ValueError("Variant occurrence accounting mismatch")
            if tuple(sum(v["excess_counts"][p] for v in variants) for p in PATTERNS) != excess:
                raise ValueError("Variant excess accounting mismatch")
            row = dict(sentence_text=key.decode("utf-8"), first_sentence_index=first_index,
                       occurrences=occurrences, fallback_occurrences=fallback,
                       count_vectors_identical=int(not mismatches),
                       later_occurrences_with_different_counts=mismatches,
                       pattern_count_variants_json=json.dumps(variants, ensure_ascii=False, separators=(",", ":")),
                       first_total=sum(first), excess_total=sum(excess), nominal_excess_total=sum(nominal))
            for i, p in enumerate(PATTERNS):
                row[f"first_{p}"] = first[i]
                row[f"excess_{p}"] = excess[i]
                row[f"nominal_excess_{p}"] = nominal[i]
                removed[i] += excess[i]
                nominal_removed[i] += nominal[i]
            writer.writerow(row)
            repeated_types += 1
            repeated_copies += occurrences - 1
            mismatch_types += bool(mismatches)
            mismatch_occurrences += mismatches
            for metric, heap in heaps.items():
                # Positive contributors only; first corpus occurrence breaks ties.
                if row[metric] > 0:
                    entry = (row[metric], -first_index, row)
                    if len(heap) < 30:
                        heapq.heappush(heap, entry)
                    elif entry[:2] > heap[0][:2]:
                        heapq.heapreplace(heap, entry)
            if repeated_types % 10000 == 0:
                log(f"Report export: {repeated_types:,} repeated types written")
    if removed != [b - a for b, a in zip(stats["before"], stats["after"])]:
        raise ValueError("Exported excess does not reconcile with before minus after")
    if repeated_copies != stats["sentences"] - stats["unique"]:
        raise ValueError("Exported repeated copies do not reconcile with sentence totals")
    if stats["unique"] != db.execute("SELECT COUNT(*) FROM sentence").fetchone()[0]:
        raise ValueError("SQLite unique count does not reconcile with stream")
    return dict(repeated_types=repeated_types, repeated_copies=repeated_copies,
                mismatch_types=mismatch_types, mismatch_occurrences=mismatch_occurrences,
                removed=removed, nominal_removed=nominal_removed,
                top={metric: [item[2] for item in sorted(heap, key=lambda item: item[:2], reverse=True)]
                     for metric, heap in heaps.items()})


def percentage(n, denominator):
    return f"{100 * n / denominator:.9f}" if denominator else "NA"


def write_report(path, stats, result, provenance):
    before, after = stats["before"], stats["after"]
    with path.open("w", encoding="utf-8") as handle:
        def line(value=""):
            handle.write(str(value) + "\n")

        line("ParlaMint-SI exact-text duplicate audit (explanatory only)")
        for key, value in provenance.items():
            line(f"{key}: {value}")
        line("Reconciliation: VERIFIED against the completed ParlaMint dedup checkpoint, all six orders and sentence totals.")
        line("Identity: exact # text = content, physical line ending removed; integer-token FORM fallback only if absent.")
        line("Within ParlaMint only; preserve first occurrence in file order; no manual normalization.")
        line("Canonical NOUN nsubj / VERB / NOUN obj counts; every matching subject x object pair counts.")
        line("Exact text does not guarantee identical annotations or count vectors. Every occurrence was extracted.")
        line("excess_* = actual contributions of later copies; nominal_excess_* = (occurrences-1)*first_*.")
        line("pattern_count_variants_json gives vector frequencies, retained copies and exact excess by vector.")
        line("No repeated example is classified as a procedural formula; no linguistic or information-structure cause is inferred.")
        line("H1/H2 and other extraction queries are outside this audit.")
        line()
        line(f"Sentences before: {stats['sentences']:,}")
        line(f"Unique texts retained: {stats['unique']:,}")
        line(f"Later copies removed: {result['repeated_copies']:,}")
        line(f"Repeated text types (including zero S/V/O instances): {result['repeated_types']:,}")
        line(f"FORM-fallback occurrences: {stats['fallback']:,}")
        line(f"Repeated types with differing count vectors: {result['mismatch_types']:,}")
        line(f"Later occurrences with a vector different from the first: {result['mismatch_occurrences']:,}")
        line(f"S/V/O instances: {sum(before):,} before; {sum(after):,} after; {sum(result['removed']):,} removed")
        line(f"Entropy (natural log): {entropy(before):.12g} before; {entropy(after):.12g} after")
        line()
        line("order\tbefore\tafter\texcess_removed\tpct_before_due_to_later_copies\tshare_before_pct\tshare_after_pct\tnominal_excess_using_first")
        for i, p in enumerate(PATTERNS):
            line("\t".join(map(str, (p, before[i], after[i], result['removed'][i],
                                     percentage(result['removed'][i], before[i]),
                                     percentage(before[i], sum(before)), percentage(after[i], sum(after)),
                                     result['nominal_removed'][i]))))
        for p in ("OVS", "SVO"):
            i = PATTERNS.index(p)
            line()
            line(f"{p} reduction concentration (ranked by actual excess_{p}; denominator = total {p} removed)")
            line(f"Before: {before[i]:,}; after: {after[i]:,}; removed: {result['removed'][i]:,}")
            ranked = result['top'][f'excess_{p}']
            for k in (5, 10, 20):
                removed = sum(row[f'excess_{p}'] for row in ranked[:k])
                line(f"Top {k} types ({min(k, len(ranked))} positive contributors available): "
                     f"{removed:,} removed; {percentage(removed, result['removed'][i])}% of reduction")
        for metric, ranked in result["top"].items():
            line()
            line(f"TOP 30 BY {metric} (positive contributors; ties by first sentence index)")
            line("rank\toccurrences\tfirst_index\texcess_total\texcess_OVS\texcess_SVO\tfirst_counts\texcess_counts\tcount_vectors_identical\tsentence_text_json")
            for rank, row in enumerate(ranked, 1):
                line("\t".join(map(str, (
                    rank, row['occurrences'], row['first_sentence_index'], row['excess_total'],
                    row['excess_OVS'], row['excess_SVO'],
                    json.dumps({p: row[f'first_{p}'] for p in PATTERNS}, separators=(",", ":")),
                    json.dumps({p: row[f'excess_{p}'] for p in PATTERNS}, separators=(",", ":")),
                    row['count_vectors_identical'], json.dumps(row['sentence_text'], ensure_ascii=False),
                ))))
        line()
        line("TSV contains every repeated type and unaltered decoded text; use a CSV-aware TSV reader for quoted tabs/quotes.")
        line("Report sentence_text_json is reversible display escaping, not normalization or truncation.")
        line("Sort TSV numerically by occurrences, excess_total, excess_OVS or excess_SVO.")
        line("The concentration denominators are count reductions, not changes in percentage share.")
        line("Differing count vectors may reflect differing tokenization, POS or dependencies; this audit does not diagnose them.")
        line("Inherited UTF-8 errors='ignore' matches dedup_sensitivity.py; raw source identity is pinned by SHA-256.")


def validate_checkpoint(stats, checkpoint=None):
    if (tuple(stats["before"]) != EXPECTED_BEFORE or tuple(stats["after"]) != EXPECTED_AFTER
            or stats["sentences"] != EXPECTED_SENTENCES or stats["unique"] != EXPECTED_UNIQUE
            or stats["fallback"] != 0):
        raise ValueError(f"Audit disagrees with completed ParlaMint checkpoint: {stats}")
    if checkpoint is not None:
        row = read_table(checkpoint)["parlamint"]
        if row["status"] != "ok" or row["input_sha256"] != INPUT_SHA256:
            raise ValueError("Completed dedup reference status/hash mismatch")
        for phase in ("before", "after"):
            if tuple(int(row[f"{p}_n_{phase}"]) for p in PATTERNS) != tuple(stats[phase]):
                raise ValueError(f"Completed dedup reference {phase} count mismatch")
            if int(row[f"svo_instances_{phase}"]) != sum(stats[phase]):
                raise ValueError(f"Completed dedup reference {phase} instance total mismatch")
        for key, value in (("sentences_before", stats["sentences"]),
                           ("sentences_after", stats["unique"]),
                           ("duplicates_n", stats["sentences"] - stats["unique"]),
                           ("fallback_sentences_n", stats["fallback"])):
            if int(row[key]) != value:
                raise ValueError(f"Completed dedup reference {key} mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="canonical sl-word-order-repro root used in completed run")
    parser.add_argument("--input", type=Path, default=Path("/mnt/local-hddpool/niveshull/thesis/corpora/parlamint-si.conllu"))
    parser.add_argument("--dedup-results", type=Path, help="optional completed dedup_sensitivity.tsv; fixed checkpoint always checked")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--scratch-dir", type=Path, required=True, help="local disk, allow 3-5 GiB; temporary SQLite removed on completion")
    parser.add_argument("--progress-seconds", type=float, default=30)
    args = parser.parse_args()
    if not 0 < args.progress_seconds < float("inf"):
        parser.error("Progress interval must be positive and finite")
    repo, source, out, scratch = (p.expanduser().resolve() for p in
                                  (args.repo, args.input, args.out_dir, args.scratch_dir))
    checkpoint = args.dedup_results.expanduser().resolve() if args.dedup_results else None
    # Guard the canonical package, corpus tree and thesis tree against writes.
    for destination in (out, scratch):
        if any(destination == root or root in destination.parents for root in (repo, source.parent)):
            parser.error("Output/scratch must be outside the canonical package and corpus directory")
        if "latex" in destination.parts:
            parser.error("Output/scratch must not be inside latex/")
    if any((out / name).exists() for name in (EXAMPLES_NAME, REPORT_NAME)):
        parser.error("Audit output already exists; choose a new output directory")
    start = time.monotonic()
    extract, extractor_hash = load_extractor(repo)
    if extractor_hash != EXTRACTOR_SHA256:
        raise ValueError("Canonical extractor hash differs from completed run")
    original = fingerprint(source)
    source_hash = file_sha256(source, args.progress_seconds, log)
    verify_unchanged(source, original)
    if source_hash != INPUT_SHA256:
        raise ValueError(f"ParlaMint SHA-256 mismatch; expected {INPUT_SHA256}")
    log("Input and canonical extractor SHA-256 verified")
    scratch.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="parlamint-duplicate-audit-", dir=scratch) as directory:
        database = Path(directory) / "sentences.sqlite3"
        with closing(sqlite3.connect(database)) as db:
            create_database(db)
            stats = scan_duplicates(source, extract, db, args.progress_seconds)
            verify_unchanged(source, original)
            validate_checkpoint(stats, checkpoint)
            log("All six before/after counts and sentence totals reconcile with completed dedup run")
            log(f"Scratch SQLite size: {database.stat().st_size / 2**30:.3f} GiB")
            # Stage on output filesystem; failed validation never publishes partial reports.
            with tempfile.TemporaryDirectory(prefix=".parlamint-audit-stage-", dir=out) as staged:
                examples_path, report_path = Path(staged) / EXAMPLES_NAME, Path(staged) / REPORT_NAME
                result = write_examples(db, examples_path, stats)
                verify_unchanged(source, original)
                write_report(report_path, stats, result, {
                    "Generated UTC": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "Input": source, "Input SHA-256": source_hash,
                    "Canonical extractor": repo / "scripts/extract_word_order_direct.py",
                    "Canonical extractor SHA-256": extractor_hash,
                    "Reused implementation": Path(__file__).with_name("dedup_sensitivity.py").resolve(),
                    "Reused implementation SHA-256": hashlib.sha256(Path(__file__).with_name("dedup_sensitivity.py").read_bytes()).hexdigest(),
                    "Audit script SHA-256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "Completed dedup TSV": checkpoint or "embedded verified checkpoint",
                    "Completed dedup TSV SHA-256": hashlib.sha256(checkpoint.read_bytes()).hexdigest() if checkpoint else "not supplied",
                    "Elapsed seconds before publication": f"{time.monotonic() - start:.1f}",
                    "SQLite cache": "64 MiB; disk-backed exact BLOB keys; one sentence in memory",
                })
                examples_path.rename(out / EXAMPLES_NAME)
                report_path.rename(out / REPORT_NAME)
    log(f"Outputs: {out / EXAMPLES_NAME}; {out / REPORT_NAME}")
    log(f"Elapsed: {(time.monotonic() - start) / 60:.1f} minutes; temporary SQLite removed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, sqlite3.Error) as error:
        log(f"ABORTED: {error}")
        raise SystemExit(1)
