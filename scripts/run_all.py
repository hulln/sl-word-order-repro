#!/usr/bin/env python3
"""Run the public preparation-to-figures reproducibility pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from pipeline_common import ROOT, load_manifest, package_path

SCRIPTS = ROOT / "scripts"


def run(script: str, *arguments: str) -> None:
    subprocess.run([sys.executable, str(SCRIPTS / script), *arguments], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stark", type=Path, required=True, help="path to STARK's stark.py")
    parser.add_argument(
        "--use-reference-cache",
        action="store_true",
        help="run the explicitly labeled lightweight pipeline for unavailable corpora",
    )
    parser.add_argument("--download-ud", action="store_true", help="download UD r2.18 sources")
    parser.add_argument("--force-preparation", action="store_true", help="rebuild available prepared inputs")
    args = parser.parse_args()

    print("[1/5] Validating source inputs", flush=True)
    manifest = load_manifest()
    source_count = sum(package_path(row["source_input"]).exists() for row in manifest)
    prepared_count = sum(package_path(row["prepared_input"]).is_file() for row in manifest)
    print(
        f"manifest: {len(manifest)} corpus/result sets; "
        f"sources present: {source_count}; prepared files present: {prepared_count}"
    )

    print("[2/5] Preparing corpora", flush=True)
    preparation_arguments = []
    if args.download_ud:
        preparation_arguments.append("--download-ud")
    if args.force_preparation:
        preparation_arguments.append("--force")
    if not args.use_reference_cache:
        preparation_arguments.append("--require-all")
    run("prepare_corpora.py", *preparation_arguments)

    print("[3/5] Running analyses", flush=True)
    analysis_arguments = ["--stark", str(args.stark.expanduser())]
    ner_arguments = []
    if args.use_reference_cache:
        analysis_arguments.append("--use-reference-cache")
        ner_arguments.append("--use-reference-cache")
    run("extract_word_order.py", *analysis_arguments)
    run("analyze_ner.py", *ner_arguments)

    print("[4/5] Computing statistics", flush=True)
    run("compute_statistics.py")
    run("supplementary_manual_subset.py")
    run("supplementary_robustness.py")

    print("[5/5] Generating figures", flush=True)
    run("make_figures.py")
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
