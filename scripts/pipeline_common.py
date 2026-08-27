#!/usr/bin/env python3
"""Shared validation and TSV helpers for the public reproducibility pipeline."""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "config" / "corpora.tsv"
PATTERNS = ("SVO", "SOV", "VSO", "VOS", "OSV", "OVS")
MANIFEST_COLUMNS = (
    "corpus_id",
    "display_name",
    "version",
    "source_input",
    "prepared_input",
    "preparation",
    "expected_sentences",
    "prepared_sha256",
    "syntax_layer",
    "ner_layer",
    "ner_family",
    "analyses",
    "compute_note",
    "notes",
)


def read_tsv(path: Path, columns: tuple[str, ...] | None = None) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"Required file does not exist: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        actual = tuple(reader.fieldnames or ())
        if columns is not None and actual != columns:
            raise RuntimeError(f"{path}: expected columns {list(columns)}, found {list(actual)}")
        return list(reader)


def write_tsv(path: Path, columns: Iterable[str], rows: Iterable[dict[str, object]]) -> None:
    fieldnames = list(columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def load_manifest() -> list[dict[str, str]]:
    rows = read_tsv(MANIFEST_PATH, MANIFEST_COLUMNS)
    if len(rows) != 18:
        raise RuntimeError(f"{MANIFEST_PATH}: expected 18 rows, found {len(rows)}")
    ids = [row["corpus_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise RuntimeError(f"{MANIFEST_PATH}: duplicate corpus_id values")
    required = {
        "corpus_id",
        "display_name",
        "version",
        "source_input",
        "prepared_input",
        "preparation",
        "syntax_layer",
        "ner_layer",
        "ner_family",
        "analyses",
        "compute_note",
        "notes",
    }
    for line_number, row in enumerate(rows, 2):
        empty = sorted(column for column in required if not row[column].strip())
        if empty:
            raise RuntimeError(
                f"{MANIFEST_PATH}:{line_number}: empty required fields: {empty}"
            )
        for column in ("source_input", "prepared_input"):
            path = Path(row[column])
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(
                    f"{MANIFEST_PATH}:{line_number}: {column} must stay inside the package"
                )
        if "word_order" not in analyses(row):
            raise RuntimeError(f"{MANIFEST_PATH}:{line_number}: word_order tag is required")
        if row["ner_family"] not in {"manual_ner", "automatic_ner", "not_used"}:
            raise RuntimeError(
                f"{MANIFEST_PATH}:{line_number}: invalid ner_family {row['ner_family']!r}"
            )
    return rows


def analyses(row: dict[str, str]) -> set[str]:
    return {value.strip() for value in row["analyses"].split(",") if value.strip()}


def package_path(relative: str) -> Path:
    result = (ROOT / relative).resolve()
    try:
        result.relative_to(ROOT.resolve())
    except ValueError as error:
        raise RuntimeError(f"Path escapes reproducibility/: {relative}") from error
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_conllu(path: Path, expected_sentences: str = "") -> dict[str, int]:
    if not path.is_file():
        raise RuntimeError(f"Prepared corpus is missing: {path}")
    sentence_blocks = 0
    sentence_ids = 0
    tokens = 0
    ner_tokens = 0
    in_sentence = False
    with path.open(encoding="utf-8-sig", errors="strict") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                if in_sentence:
                    sentence_blocks += 1
                    in_sentence = False
                continue
            if line.startswith("#"):
                if line.startswith("# sent_id = "):
                    sentence_ids += 1
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) != 10:
                raise RuntimeError(f"{path}:{line_number}: expected 10 CoNLL-U columns")
            in_sentence = True
            if not columns[0].isdigit():
                continue
            tokens += 1
            if not columns[6].isdigit():
                raise RuntimeError(
                    f"{path}:{line_number}: token {columns[0]} has no numeric dependency HEAD"
                )
            if any(part.upper().startswith("NER=") for part in columns[9].split("|")):
                ner_tokens += 1
    if in_sentence:
        sentence_blocks += 1
    sentence_count = sentence_ids or sentence_blocks
    if expected_sentences and sentence_count != int(expected_sentences):
        raise RuntimeError(
            f"{path}: expected {expected_sentences} sentences, found {sentence_count}"
        )
    if not tokens:
        raise RuntimeError(f"{path}: no integer-ID tokens found")
    return {"sentences": sentence_count, "tokens": tokens, "ner_tokens": ner_tokens}


def validate_distribution(
    rows: list[dict[str, str]], corpus_id: str, source: Path, tolerance: float = 5.1e-7
) -> dict[str, tuple[int, int]]:
    if len(rows) != len(PATTERNS):
        raise RuntimeError(f"{source}: {corpus_id} needs six rows, found {len(rows)}")
    result: dict[str, tuple[int, int]] = {}
    for row in rows:
        pattern = row["pattern"]
        if pattern in result:
            raise RuntimeError(f"{source}: duplicate {corpus_id} + {pattern}")
        try:
            count, total = int(row["count"]), int(row["total"])
            proportion = float(row["proportion"])
        except ValueError as error:
            raise RuntimeError(f"{source}: non-numeric count row for {corpus_id}") from error
        if count < 0 or total <= 0:
            raise RuntimeError(f"{source}: invalid count/total for {corpus_id} {pattern}")
        if not math.isclose(proportion, count / total, rel_tol=0, abs_tol=tolerance):
            raise RuntimeError(f"{source}: invalid proportion for {corpus_id} {pattern}")
        result[pattern] = (count, total)
    if set(result) != set(PATTERNS):
        raise RuntimeError(f"{source}: invalid pattern set for {corpus_id}: {sorted(result)}")
    totals = {total for _, total in result.values()}
    if len(totals) != 1 or sum(count for count, _ in result.values()) != next(iter(totals)):
        raise RuntimeError(f"{source}: inconsistent total for {corpus_id}")
    return result
