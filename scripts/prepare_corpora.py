#!/usr/bin/env python3
"""Prepare or validate canonical analysis corpora under ``prepared/``."""

from __future__ import annotations

import argparse
import gzip
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pipeline_common import ROOT, load_manifest, package_path, sha256, validate_conllu

SCRIPTS = ROOT / "scripts"
UD_REPOSITORIES = {
    "ssj": "https://github.com/UniversalDependencies/UD_Slovenian-SSJ.git",
    "sst": "https://github.com/UniversalDependencies/UD_Slovenian-SST.git",
}
SUK_OUTPUTS = {
    "suk-literary": "suk_leposlovno.conllu",
    "suk-publicistic": "suk_publicisticno_splosno.conllu",
    "suk-professional": "suk_strokovno.conllu",
}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def download_ud_sources(manifest: list[dict[str, str]]) -> None:
    for row in manifest:
        corpus_id = row["corpus_id"]
        if corpus_id not in UD_REPOSITORIES:
            continue
        destination = package_path(row["source_input"])
        if destination.exists():
            print(f"source already present: {destination.relative_to(ROOT)}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        run(
            [
                "git",
                "clone",
                "--quiet",
                "--depth",
                "1",
                "--branch",
                "r2.18",
                UD_REPOSITORIES[corpus_id],
                str(destination),
            ]
        )


def merge_ud_splits(source: Path, destination: Path) -> None:
    candidates = []
    for split in ("train", "dev", "test"):
        matches = sorted(source.glob(f"*-ud-{split}.conllu"))
        if len(matches) != 1:
            raise RuntimeError(f"{source}: expected one {split} split, found {matches}")
        candidates.append(matches[0])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        for path in candidates:
            with path.open("rb") as input_handle:
                shutil.copyfileobj(input_handle, output)


def assert_only_misc_changed(before: Path, after: Path) -> None:
    def structural_lines(path: Path):
        with path.open(encoding="utf-8-sig") as handle:
            for line in handle:
                if line.startswith("#") or not line.strip():
                    yield line
                    continue
                columns = line.rstrip("\n").split("\t")
                yield "\t".join(columns[:9]) + "\n"

    for line_number, (left, right) in enumerate(
        zip(structural_lines(before), structural_lines(after), strict=True), 1
    ):
        if left != right:
            raise RuntimeError(
                f"NER merge changed content outside MISC at structural line {line_number}"
            )


def prepare_sst(source: Path, destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="prepare-sst-") as directory:
        raw = Path(directory) / "sst-merged.conllu"
        merge_ud_splits(source, raw)
        run(
            [
                sys.executable,
                str(SCRIPTS / "add_ner_annotation.py"),
                "--input",
                str(raw),
                "--output",
                str(destination),
                "--type",
                "standard",
            ]
        )
        assert_only_misc_changed(raw, destination)


def add_ner_only(source: Path, destination: Path) -> None:
    """Add a CLASSLA NER layer to a supplied CoNLL-U without touching its trees."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            sys.executable,
            str(SCRIPTS / "add_ner_annotation.py"),
            "--input",
            str(source),
            "--output",
            str(destination),
            "--type",
            "standard",
        ]
    )
    assert_only_misc_changed(source, destination)


def prepare_suk(source: Path, rows: list[dict[str, str]]) -> None:
    with tempfile.TemporaryDirectory(prefix="prepare-suk-") as directory:
        output_directory = Path(directory)
        run(
            [
                sys.executable,
                str(SCRIPTS / "prepare_suk_genres.py"),
                "--input",
                str(source),
                "--outdir",
                str(output_directory),
                "--require-syntax",
            ]
        )
        for row in rows:
            source_name = SUK_OUTPUTS[row["corpus_id"]]
            destination = package_path(row["prepared_input"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(output_directory / source_name, destination)


def decompress_conllu(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(source, "rb") as input_handle, destination.open("wb") as output:
        shutil.copyfileobj(input_handle, output)


def concatenate_ana(source: Path, destination: Path) -> None:
    files = sorted(source.rglob("*.conllu"), key=lambda path: str(path))
    if not files:
        raise RuntimeError(f"{source}: no .conllu files found")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        for path in files:
            with path.open("rb") as input_handle:
                shutil.copyfileobj(input_handle, output)


def prepare_one(row: dict[str, str], source: Path, destination: Path) -> None:
    method = row["preparation"]
    if method == "merge_ud_splits":
        merge_ud_splits(source, destination)
    elif method == "merge_ud_splits_then_add_ner":
        prepare_sst(source, destination)
    elif method in {"copy_distributed_conllu", "copy_verified_classla_conllu"}:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    elif method == "decompress_distributed_conllu":
        decompress_conllu(source, destination)
    elif method == "concatenate_distributed_ana":
        concatenate_ana(source, destination)
    elif method == "add_ner_to_supplied_conllu":
        add_ner_only(source, destination)
    elif method in {
        "janes_wiki_vert_to_classla",
        "text_to_classla",
    }:
        raise RuntimeError(
            f"{row['corpus_id']}: preparation method {method} is documented but cannot "
            "currently be regenerated by this public package without unresolved "
            "source/pipeline information; see inputs/README.md"
        )
    else:
        raise RuntimeError(f"{row['corpus_id']}: unsupported preparation method {method}")


def validate_prepared(row: dict[str, str], destination: Path) -> dict[str, int]:
    stats = validate_conllu(destination, row["expected_sentences"])
    expected_hash = row["prepared_sha256"]
    if expected_hash:
        actual_hash = sha256(destination)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"{row['corpus_id']}: prepared checksum mismatch: "
                f"expected {expected_hash}, found {actual_hash}"
            )
    if row["ner_family"] != "not_used" and stats["ner_tokens"] == 0:
        raise RuntimeError(f"{row['corpus_id']}: NER analysis requested but no NER tags found")
    return stats


def write_checksums(manifest: list[dict[str, str]]) -> None:
    destination = ROOT / "prepared" / "checksums.sha256"
    lines = []
    for row in manifest:
        path = package_path(row["prepared_input"])
        if path.is_file():
            lines.append(f"{sha256(path)}  {path.name}\n")
    destination.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download-ud",
        action="store_true",
        help="clone the exact UD r2.18 SSJ and SST source repositories into inputs/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild prepared files when their documented source input is present",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="fail unless every manifest corpus has a validated prepared file",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    if args.download_ud:
        download_ud_sources(manifest)

    suk_rows = [row for row in manifest if row["preparation"] == "split_combined_suk"]
    suk_source = package_path(suk_rows[0]["source_input"])
    if suk_source.is_file() and (args.force or any(not package_path(r["prepared_input"]).is_file() for r in suk_rows)):
        prepare_suk(suk_source, suk_rows)

    missing = []
    for row in manifest:
        destination = package_path(row["prepared_input"])
        source = package_path(row["source_input"])
        if row["preparation"] != "split_combined_suk" and (
            not destination.is_file() or (args.force and source.exists())
        ):
            if source.exists():
                prepare_one(row, source, destination)
            elif not destination.is_file():
                missing.append(row["corpus_id"])
                print(f"missing source and prepared corpus: {row['corpus_id']}")
                continue
        if destination.is_file():
            stats = validate_prepared(row, destination)
            print(
                f"validated {row['corpus_id']}: "
                f"{stats['sentences']} sentences, {stats['tokens']} tokens"
            )

    write_checksums(manifest)
    if missing and args.require_all:
        raise SystemExit(
            "Full preparation is unavailable for: " + ", ".join(missing)
        )
    print(f"Prepared corpora available: {len(manifest) - len(missing)}/{len(manifest)}")


if __name__ == "__main__":
    main()
