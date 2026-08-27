#!/usr/bin/env python3
"""Extract the canonical six-pattern word-order table from prepared corpora."""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from pipeline_common import (
    PATTERNS,
    ROOT,
    load_manifest,
    package_path,
    read_tsv,
    validate_distribution,
    write_tsv,
)

SCRIPTS = ROOT / "scripts"
REFERENCE = ROOT / "reference" / "word_order_counts.tsv"
OUTPUT = ROOT / "outputs" / "data" / "word_order_counts.tsv"
REFERENCE_COLUMNS = ("corpus_id", "corpus", "pattern", "count", "total", "proportion")
TEMP_COLUMNS = ("corpus", "pattern", "count", "total", "proportion")
OUTPUT_COLUMNS = REFERENCE_COLUMNS + ("extraction_status",)


def load_reference(manifest: list[dict[str, str]]) -> dict[str, dict[str, tuple[int, int]]]:
    rows = read_tsv(REFERENCE, REFERENCE_COLUMNS)
    names = {row["corpus_id"]: row["display_name"] for row in manifest}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        corpus_id = row["corpus_id"]
        if corpus_id not in names:
            raise RuntimeError(f"{REFERENCE}: unexpected corpus ID {corpus_id}")
        if row["corpus"] != names[corpus_id]:
            raise RuntimeError(f"{REFERENCE}: display-name mismatch for {corpus_id}")
        grouped[corpus_id].append(row)
    return {
        corpus_id: validate_distribution(corpus_rows, corpus_id, REFERENCE)
        for corpus_id, corpus_rows in grouped.items()
    }


def load_temporary(path: Path, corpus_id: str, display_name: str) -> dict[str, tuple[int, int]]:
    rows = read_tsv(path, TEMP_COLUMNS)
    if any(row["corpus"] != display_name for row in rows):
        raise RuntimeError(f"{path}: unexpected corpus label for {corpus_id}")
    return validate_distribution(rows, corpus_id, path)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def extract_prepared(
    row: dict[str, str], prepared: Path, stark: Path, temporary_root: Path
) -> dict[str, tuple[int, int]]:
    corpus_id = row["corpus_id"]
    display_name = row["display_name"]
    work = temporary_root / corpus_id
    direct_path = work / "direct.tsv"
    stark_path = work / "stark.tsv"
    print(f"{corpus_id}: direct extraction + STARK", flush=True)
    run(
        [
            sys.executable,
            str(SCRIPTS / "extract_word_order_direct.py"),
            "--input",
            str(prepared),
            "--out",
            str(direct_path),
            "--label",
            display_name,
        ]
    )
    run(
        [
            sys.executable,
            str(SCRIPTS / "run_stark_extraction.py"),
            "--input",
            str(prepared),
            "--label",
            display_name,
            "--stark",
            str(stark),
            "--workdir",
            str(work / "stark-work"),
            "--out",
            str(stark_path),
        ]
    )
    direct = load_temporary(direct_path, corpus_id, display_name)
    official = load_temporary(stark_path, corpus_id, display_name)
    if direct != official:
        differences = {
            pattern: {"direct": direct.get(pattern), "stark": official.get(pattern)}
            for pattern in PATTERNS
            if direct.get(pattern) != official.get(pattern)
        }
        raise RuntimeError(f"{corpus_id}: STARK/direct mismatch: {differences}")
    print(f"{corpus_id}: exact STARK/direct agreement, total={official[PATTERNS[0]][1]}")
    return official


def validate_output(rows: list[dict[str, object]], manifest: list[dict[str, str]]) -> None:
    if len(rows) != 108:
        raise RuntimeError(f"Expected 108 final word-order rows, found {len(rows)}")
    expected_ids = [row["corpus_id"] for row in manifest]
    actual_ids = [str(rows[index]["corpus_id"]) for index in range(0, len(rows), 6)]
    if actual_ids != expected_ids:
        raise RuntimeError("Final corpus ordering does not match config/corpora.tsv")
    seen = set()
    for manifest_row, start in zip(manifest, range(0, len(rows), 6)):
        corpus_rows = rows[start : start + 6]
        corpus_id = manifest_row["corpus_id"]
        if [row["pattern"] for row in corpus_rows] != list(PATTERNS):
            raise RuntimeError(f"{corpus_id}: final pattern order is invalid")
        for row in corpus_rows:
            pair = (row["corpus_id"], row["pattern"])
            if pair in seen:
                raise RuntimeError(f"Duplicate final row: {pair}")
            seen.add(pair)
            if row["corpus"] != manifest_row["display_name"]:
                raise RuntimeError(f"{corpus_id}: final display name differs from manifest")
            if not math.isclose(
                float(row["proportion"]), int(row["count"]) / int(row["total"]),
                rel_tol=0, abs_tol=1e-15,
            ):
                raise RuntimeError(f"{pair}: final proportion is inconsistent")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stark", type=Path, required=True, help="path to STARK's stark.py")
    parser.add_argument(
        "--use-reference-cache",
        action="store_true",
        help="explicitly use verified cached counts when a prepared corpus is unavailable",
    )
    args = parser.parse_args()
    stark = args.stark.expanduser().resolve()
    if not stark.is_file():
        raise SystemExit(f"STARK not found: {stark}")

    manifest = load_manifest()
    reference = load_reference(manifest) if args.use_reference_cache else {}
    output_rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="word-order-") as directory:
        temporary_root = Path(directory)
        for row in manifest:
            corpus_id = row["corpus_id"]
            prepared = package_path(row["prepared_input"])
            if prepared.is_file():
                counts = extract_prepared(row, prepared, stark, temporary_root)
                status = "stark_direct_exact"
            elif args.use_reference_cache and corpus_id in reference:
                counts = reference[corpus_id]
                status = "verified_reference_stark_direct_exact"
                print(f"{corpus_id}: explicit verified reference cache")
            else:
                hint = " (try --use-reference-cache for documented cached corpora)"
                raise SystemExit(f"Missing prepared corpus: {prepared}{hint}")

            total = counts[PATTERNS[0]][1]
            for pattern in PATTERNS:
                count, pattern_total = counts[pattern]
                if pattern_total != total:
                    raise RuntimeError(f"{corpus_id}: inconsistent total for {pattern}")
                output_rows.append(
                    {
                        "corpus_id": corpus_id,
                        "corpus": row["display_name"],
                        "pattern": pattern,
                        "count": count,
                        "total": total,
                        "proportion": count / total,
                        "extraction_status": status,
                    }
                )

    validate_output(output_rows, manifest)
    for row in output_rows:
        row["proportion"] = f"{float(row['proportion']):.6f}"
    write_tsv(OUTPUT, OUTPUT_COLUMNS, output_rows)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} (108 rows)")


if __name__ == "__main__":
    main()
