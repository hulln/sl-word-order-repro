#!/usr/bin/env python3
"""Streaming, within-corpus exact-text deduplication sensitivity (Python >=3.10).

Only the four verified inputs below are processed. Source files and the canonical
package are read only. Three sequential input passes: SHA-256, ordinary canonical
extraction, then deduplication. An exact SQLite BLOB primary key stores sentence
identities on disk; RAM does not grow with the number of unique sentences.

The canonical extractor's nested flush_sentence() is compiled unchanged inside
a small callable wrapper, because it is not exported by the canonical module.
No independent subject/object matching implementation is maintained here.

Entropy uses natural logarithms. JSD means Jensen-Shannon DISTANCE, base 2,
including the square root, as in canonical compute_statistics.py::js_distance.
Ranking checks replace these four distributions only; other sources retain their
canonical counts. Ties require review. No significance tests are performed.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import math
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

PATTERNS = ("SVO", "SOV", "VSO", "VOS", "OSV", "OVS")
# corpus ID: (CJVT filename, SHA-256, ordinary canonical S/V/O total)
INPUTS = {
    "janes-tweet": ("janes_tweet.conllu", "4a3f1c85f45094941670bf1d1fad7e50dc1fe117b3aa18d7a583ebdf0ca83bb1", 496602),
    "janes-wiki": ("janes.wiki.conllu", "aa398403028feede657d8fb21cb5b4e92e64b10738e650d7345d9d9a838b0e42", 11281),
    "classla-wikipedia": ("classlawiki-sl.conllu", "d163fd9647110e6721131f5d204516f2b3f8ca102c61611807da87349b17ec8d", 296395),
    "parlamint": ("parlamint-si.conllu", "be53ad8a8b28e1f7996ba79de045b1c3516324cd8adbe902ea2500e7d02bd81e", 497572),
}
REGISTER = ("ssj", "sst", "janes-news", "janes-blog", "janes-forum",
            "janes-tweet", "janes-wiki", "classla-wikipedia", "parlamint")
WEB = REGISTER[2:-1]
AUTO_REGISTER = REGISTER[2:]
HUMAN = REGISTER + ("suk-literary", "suk-publicistic", "suk-professional", "kdsp", "human-essays")
WRITTEN = tuple(cid for cid in HUMAN if cid not in ("sst", "parlamint"))
JSD_SOURCES = REGISTER + ("kdsp", "human-essays", "gpt5-essays")
FIELDS = (
    ["corpus_id", "corpus", "input_path", "status", "error", "input_sha256",
     "sentences_before", "sentences_after", "duplicates_n", "duplicates_pct",
     "fallback_sentences_n", "svo_instances_before", "svo_instances_after"]
    + [f"{p}_n_before" for p in PATTERNS] + [f"{p}_n_after" for p in PATTERNS]
    + [f"{p}_pct_after" for p in PATTERNS]
    + ["SVO_pct_before", "entropy_nat_before", "entropy_nat_after",
       "js_distance_base2_pre_post", "abs_SVO_change_pp", "abs_entropy_change_nat"]
)


class Logger:
    def __init__(self, handle):
        self.handle = handle

    def __call__(self, message):
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        line = f"[{stamp}] {message}"
        print(line, flush=True)
        self.handle.write(line + "\n")
        self.handle.flush()


class Progress:
    def __init__(self, label, size, interval, log):
        self.label, self.size, self.interval, self.log = label, size, interval, log
        self.start = self.last = time.monotonic()

    def update(self, done, detail="", final=False):
        now = time.monotonic()
        if not final and now - self.last < self.interval:
            return
        elapsed = now - self.start
        rate = done / max(elapsed, 1e-9)
        eta = max(0, self.size - done) / rate if rate else 0
        pct = 100 * done / self.size if self.size else 100
        self.log(f"{self.label}: {pct:.1f}% ({done / 2**30:.2f}/{self.size / 2**30:.2f} GiB), "
                 f"{rate / 2**20:.1f} MiB/s, elapsed {elapsed / 60:.1f} min, "
                 f"ETA {eta / 60:.1f} min {detail}")
        self.last = now


def load_extractor(repo):
    """Reuse the exact canonical nested function, including every S x O pair."""
    path = repo / "scripts/extract_word_order_direct.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    flush = next(node for node in main.body if isinstance(node, ast.FunctionDef) and node.name == "flush_sentence")
    wrapper = ast.parse(
        "def extract_sentence(upos, deprel, head):\n"
        "    genre = 'dedup'\n"
        "    counts = {'dedup': Counter()}\n"
        "    pass\n"
        "    flush_sentence()\n"
        "    return counts['dedup']\n"
    )
    wrapper.body[0].body[2] = flush
    ast.fix_missing_locations(wrapper)
    spec = importlib.util.spec_from_file_location("dedup_canonical_direct", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load canonical extractor: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if tuple(module.WORD_ORDERS) != PATTERNS:
        raise ValueError("Canonical word-order categories changed")
    namespace = dict(vars(module))
    namespace["Counter"] = Counter
    exec(compile(wrapper, str(path), "exec"), namespace)
    return namespace["extract_sentence"], hashlib.sha256(source.encode("utf-8")).hexdigest()


def read_table(path):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    result = {row["corpus_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate corpus IDs: {path}")
    return result


def load_references(repo):
    manifest = read_table(repo / "config/corpora.tsv")
    summary = read_table(repo / "outputs/data/word_order_summary.tsv")
    vectors = {}
    for cid, row in summary.items():
        counts = [int(row[f"{p}_n"]) for p in PATTERNS]
        if any(n < 0 for n in counts) or sum(counts) != int(row["total"]) or not sum(counts):
            raise ValueError(f"Invalid canonical distribution: {cid}")
        vectors[cid] = counts
    for cid, (_, digest, total) in INPUTS.items():
        if manifest[cid]["prepared_sha256"] != digest or sum(vectors[cid]) != total:
            raise ValueError(f"Canonical reference disagrees with fixed input checkpoint: {cid}")
    for cid in HUMAN + ("gpt5-essays",):
        if cid not in vectors:
            raise ValueError(f"Missing comparison source: {cid}")
    return manifest, vectors


def fingerprint(path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def verify_unchanged(path, original):
    if fingerprint(path) != original:
        raise ValueError(f"Input changed during processing: {path}")


def file_sha256(path, interval, log):
    progress = Progress(f"{path.name} SHA-256", path.stat().st_size, interval, log)
    digest, done = hashlib.sha256(), 0
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 2**20):
            digest.update(chunk)
            done += len(chunk)
            progress.update(done)
    progress.update(done, final=True)
    return digest.hexdigest()


def sentences(path):
    """One sentence at a time; mirror canonical token parsing, retain identity.

    Text content is exact after '# text = ', with only the physical line ending
    removed. No stripping, case folding, or Unicode normalization. Empty text
    is a valid explicit identity. FORM fallback ignores MWTs and empty nodes.
    """
    upos, deprel, head, forms = {}, {}, {}, []
    text, done = None, 0
    with path.open("rb") as handle:
        for raw in handle:
            done += len(raw)
            # Same UTF-8 error handling as the canonical extractor.
            line = raw.decode("utf-8", errors="ignore")
            if line.startswith("#"):
                if line.startswith("# text = "):
                    value = line[len("# text = "):].removesuffix("\n").removesuffix("\r")
                    if text is not None and text != value:
                        raise ValueError("Conflicting # text lines in one sentence")
                    text = value
                continue
            if not line.strip():
                if forms:
                    identity = text if text is not None else " ".join(forms)
                    yield identity, text is None, upos, deprel, head, done
                upos, deprel, head, forms = {}, {}, {}, []
                text = None
                continue
            cols = line.rstrip("\n").split("\t")
            if not cols[0].isdigit():
                continue
            if len(cols) < 2:
                raise ValueError("Integer-ID token has no FORM column")
            forms.append(cols[1])
            if len(cols) < 8:
                continue
            token_id = int(cols[0])
            upos[token_id], deprel[token_id] = cols[3], cols[7]
            head[token_id] = int(cols[6]) if cols[6].isdigit() else 0
        if forms:
            identity = text if text is not None else " ".join(forms)
            yield identity, text is None, upos, deprel, head, done


def scan(path, extract, interval, log, seen=None):
    phase = "deduplication" if seen is not None else "ordinary extraction"
    progress = Progress(f"{path.name} {phase}", path.stat().st_size, interval, log)
    counts, total, unique, fallback = Counter(), 0, 0, 0
    for identity, missing, upos, deprel, head, done in sentences(path):
        total += 1
        fallback += missing
        keep = True
        if seen is not None:
            # Exact keys, including fallback collisions with explicit # text.
            cursor = seen.execute("INSERT OR IGNORE INTO seen VALUES (?)", (identity.encode("utf-8"),))
            keep = cursor.rowcount == 1
        if keep:
            unique += 1
            counts.update(extract(upos, deprel, head))
        if total % 10000 == 0:
            if seen is not None:
                seen.commit()
            progress.update(done, f"sentences={total:,}, retained={unique:,}")
    if seen is not None:
        seen.commit()
    progress.update(path.stat().st_size, f"sentences={total:,}, retained={unique:,}", final=True)
    return total, unique, fallback, [counts[p] for p in PATTERNS]


def entropy(counts):
    total = sum(counts)
    if not total:
        raise ValueError("Undefined distribution: no S/V/O instances")
    return -sum((n / total) * math.log(n / total) for n in counts if n)


def js_distance(a, b):
    if not sum(a) or not sum(b):
        raise ValueError("Undefined JSD: empty distribution")
    pa, pb = [n / sum(a) for n in a], [n / sum(b) for n in b]
    midpoint = [(x + y) / 2 for x, y in zip(pa, pb)]
    divergence = sum(p * math.log2(p / m) for ps in (pa, pb) for p, m in zip(ps, midpoint) if p) / 2
    return math.sqrt(max(0.0, divergence))


def process_corpus(path, expected_hash, expected_counts, extract, scratch, interval, log, row):
    original = fingerprint(path)
    row["input_sha256"] = file_sha256(path, interval, log)
    verify_unchanged(path, original)
    if row["input_sha256"] != expected_hash:
        raise ValueError(f"SHA-256 mismatch; expected {expected_hash}")
    log(f"{row['corpus_id']}: SHA-256 verified")
    total, _, fallback, before = scan(path, extract, interval, log)
    verify_unchanged(path, original)
    row.update(sentences_before=total, fallback_sentences_n=fallback, svo_instances_before=sum(before))
    if sum(before) != sum(expected_counts):
        raise ValueError(f"Ordinary total {sum(before)} != canonical {sum(expected_counts)}")
    if before != expected_counts:
        raise ValueError(f"Ordinary six-pattern counts {before} != canonical {expected_counts}")
    log(f"{row['corpus_id']}: ordinary total AND all six counts verified; starting deduplication")
    with tempfile.TemporaryDirectory(prefix=f"dedup-{row['corpus_id']}-", dir=scratch) as directory:
        database = Path(directory) / "seen.sqlite3"
        with closing(sqlite3.connect(database)) as seen:
            # Disposable index; bounded cache, no redundant rollback/WAL files.
            seen.execute("PRAGMA journal_mode=OFF")
            seen.execute("PRAGMA synchronous=OFF")
            seen.execute("PRAGMA cache_size=-65536")
            seen.execute("PRAGMA temp_store=FILE")
            seen.execute("CREATE TABLE seen (identity BLOB PRIMARY KEY) WITHOUT ROWID")
            after_total, unique, after_fallback, after = scan(path, extract, interval, log, seen)
        log(f"{row['corpus_id']}: exact identity index size {database.stat().st_size / 2**30:.2f} GiB (removed now)")
    verify_unchanged(path, original)
    if after_total != total or after_fallback != fallback or any(a > b for a, b in zip(after, before)):
        raise ValueError("Inconsistent pre/post scan")
    hb, ha = entropy(before), entropy(after)
    svo_before, svo_after = 100 * before[0] / sum(before), 100 * after[0] / sum(after)
    row.update(status="ok", sentences_after=unique, duplicates_n=total - unique,
               duplicates_pct=100 * (total - unique) / total, svo_instances_after=sum(after),
               SVO_pct_before=svo_before, entropy_nat_before=hb, entropy_nat_after=ha,
               js_distance_base2_pre_post=js_distance(before, after),
               abs_SVO_change_pp=abs(svo_after - svo_before), abs_entropy_change_nat=abs(ha - hb))
    for p, b, a in zip(PATTERNS, before, after):
        row[f"{p}_n_before"], row[f"{p}_n_after"] = b, a
        row[f"{p}_pct_after"] = 100 * a / sum(after)
    log(f"{row['corpus_id']}: VERIFIED RESULT; input SHA-256={row['input_sha256']}")
    log(f"  Sentences: {total:,} before; {unique:,} unique after; "
        f"{total - unique:,} duplicates ({row['duplicates_pct']:.6f}%); {fallback:,} FORM fallbacks")
    log(f"  S/V/O instances: {sum(before):,} before; {sum(after):,} after")
    log("  Six orders after: " + "; ".join(
        f"{p}={a:,} ({100 * a / sum(after):.6f}%)" for p, a in zip(PATTERNS, after)))
    log(f"  SVO: {svo_before:.9f}% before; {svo_after:.9f}% after; "
        f"absolute change={row['abs_SVO_change_pp']:.9f} percentage points")
    log(f"  Shannon entropy (natural log): {hb:.12g} before; {ha:.12g} after; "
        f"absolute change={abs(ha - hb):.12g}")
    log(f"  Jensen-Shannon distance (base 2), pre vs post: {row['js_distance_base2_pre_post']:.12g}")
    return after


def descriptive_checks(vectors):
    """Explicit affected rankings/directions from empirija.tex (read-only scope).

    Strict margin >0 supports a claim; <=0 reports a tie or reversal. Qualitative
    'approximately equal' statements have no numerical threshold and are omitted.
    """
    checks = {}
    share = lambda cid, p=0: vectors[cid][p] / sum(vectors[cid])
    h = lambda cid: entropy(vectors[cid])

    def extreme(label, target, ids, metric, highest=True):
        competitors = [metric(cid) for cid in ids if cid != target]
        checks[label] = (metric(target) - max(competitors) if highest
                         else min(competitors) - metric(target))

    extreme("JANES-Tweet highest SVO among all analyzed human sources", "janes-tweet", HUMAN, share)
    extreme("ParlaMint highest OVS in nine-source register comparison", "parlamint", REGISTER, lambda c: share(c, 5))
    extreme("CLASSLA-Wikipedia lowest entropy in nine-source comparison", "classla-wikipedia", REGISTER, h, False)
    extreme("Tweet second-lowest entropy in nine-source comparison", "janes-tweet",
            tuple(c for c in REGISTER if c != "classla-wikipedia"), h, False)
    extreme("ParlaMint lowest SVO among seven automatic register sources", "parlamint", AUTO_REGISTER, share, False)
    extreme("Forum highest entropy among six web sources", "janes-forum", WEB, h)
    extreme("Forum highest VSO among six web sources", "janes-forum", WEB, lambda c: share(c, 2))
    extreme("KDSP lowest SVO among written human sources", "kdsp", WRITTEN, share, False)
    extreme("KDSP highest entropy among written human sources", "kdsp", WRITTEN, h)
    for cid in vectors:
        checks[f"SVO dominant (>2 x next order): {cid}"] = vectors[cid][0] - 2 * max(vectors[cid][1:])
    for p, label in ((0, "SVO article > talk"), (2, "VSO talk > article")):
        direction = 1 if p == 0 else -1
        checks[label] = direction * (share("classla-wikipedia", p) - share("janes-wiki", p))
    checks["Entropy talk > article"] = h("janes-wiki") - h("classla-wikipedia")
    checks["SVO Tweet > Wikipedia > Blog (Wikipedia > Blog)"] = share("classla-wikipedia") - share("janes-blog")
    for cid in ("janes-blog", "janes-tweet", "classla-wikipedia"):
        checks[f"Entropy SSJ > {cid}"] = h("ssj") - h(cid)
    checks["Entropy Forum > SSJ"] = h("janes-forum") - h("ssj")
    checks["ParlaMint entropy higher than majority of web sources"] = sum(h("parlamint") > h(c) for c in WEB) - len(WEB) / 2
    checks["Essay SVO gap > human-source SVO range"] = (
        share("gpt5-essays") - share("human-essays") - (max(map(share, HUMAN)) - min(map(share, HUMAN))))
    # Explicit nearest/farthest claims in the twelve-source JSD comparison.
    for anchor, target, highest in (("gpt5-essays", "janes-tweet", False),
                                   ("human-essays", "janes-news", False),
                                   ("ssj", "parlamint", False),
                                   ("kdsp", "janes-forum", False)):
        ids = tuple(c for c in JSD_SOURCES if c != anchor and c != "gpt5-essays")
        extreme(f"JSD {anchor}: {'farthest' if highest else 'nearest'} {target}", target, ids,
                lambda c: js_distance(vectors[anchor], vectors[c]), highest)
    distance_gpt = lambda c: js_distance(vectors["gpt5-essays"], vectors[c])
    checks["JSD GPT-5: KDSP and SST are the two farthest human sources"] = (
        min(distance_gpt(c) for c in ("kdsp", "sst"))
        - max(distance_gpt(c) for c in JSD_SOURCES if c not in ("gpt5-essays", "kdsp", "sst")))
    written_jsd = tuple(c for c in JSD_SOURCES if c not in ("sst", "parlamint", "gpt5-essays"))
    distance_sst = lambda c: js_distance(vectors["sst"], vectors[c])
    checks["JSD SST: Forum and KDSP are the two nearest written sources"] = (
        min(distance_sst(c) for c in written_jsd if c not in ("janes-forum", "kdsp"))
        - max(distance_sst(c) for c in ("janes-forum", "kdsp")))
    peers = tuple(c for c in JSD_SOURCES if c not in ("human-essays", "gpt5-essays"))
    checks["Human essays closer than GPT-5 to majority of other human sources"] = (
        sum(js_distance(vectors["human-essays"], vectors[c]) < distance_gpt(c) for c in peers) - len(peers) / 2)
    return checks


def report_robustness(before, after, complete, log):
    log("ROBUSTNESS: four deduplicated distributions; every other source held at canonical counts. "
        "ParlaMint OVS scope is the nine-source register comparison. Strict ties require review.")
    old, new = descriptive_checks(before), descriptive_checks(after)
    invalid, changed = [], []
    for label, margin in old.items():
        if margin <= 1e-12:
            invalid.append(label)
        if new[label] <= 1e-12:
            changed.append(label)
        state = "preserved" if new[label] > 1e-12 else "tie/reversal"
        log(f"CLAIM {label}: before_margin={margin:.12g}; after_margin={new[label]:.12g}; {state}")
    if not complete:
        result = "INCOMPLETE: at least one input failed or was not selected; cannot classify stability."
    elif invalid:
        result = "UNRESOLVED: baseline does not support every encoded claim: " + "; ".join(invalid)
    elif changed:
        result = "NOT STABLE: at least one stated ranking/direction lost: " + "; ".join(changed)
    else:
        result = "STABLE: encoded descriptive conclusions are stable under within-corpus deduplication of these four inputs."
    log(result)
    log("No statistical significance inferred. Approximately-equal/qualitative claims and analyses "
        "requiring other extraction queries are outside these six-pattern checks.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="canonical sl-word-order-repro root")
    parser.add_argument("--corpus-dir", type=Path, default=Path("/mnt/local-hddpool/niveshull/thesis/corpora"))
    parser.add_argument("--out-dir", type=Path, default=Path("dedup_sensitivity_outputs"))
    parser.add_argument("--scratch-dir", type=Path, required=True, help="local disk for exact SQLite index; allow tens of GB")
    parser.add_argument("--progress-seconds", type=float, default=30)
    parser.add_argument("--corpora", nargs="+", choices=tuple(INPUTS), default=list(INPUTS))
    args = parser.parse_args()
    if args.progress_seconds <= 0 or len(set(args.corpora)) != len(args.corpora):
        parser.error("Progress interval must be positive; corpus IDs must not repeat")
    repo, corpus_dir = args.repo.expanduser().resolve(), args.corpus_dir.expanduser().resolve()
    out, scratch = args.out_dir.expanduser().resolve(), args.scratch_dir.expanduser().resolve()
    # Do not allow generated files anywhere inside either read-only input tree.
    if any(p == root or root in p.parents for p in (out, scratch) for root in (repo, corpus_dir)):
        parser.error("Output/scratch directories must be outside the canonical package and corpus directory")
    manifest, before = load_references(repo)
    extract, extraction_hash = load_extractor(repo)
    out.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    after, failures = dict(before), []
    with (out / "dedup_sensitivity.log").open("w", encoding="utf-8") as handle, \
            (out / "dedup_sensitivity.tsv").open("w", encoding="utf-8", newline="") as table:
        log = Logger(handle)
        writer = csv.DictWriter(table, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        table.flush()
        log(f"Canonical extractor: {repo / 'scripts/extract_word_order_direct.py'}; SHA-256={extraction_hash}; "
            "unchanged flush_sentence() plus canonical classify()")
        for relative in ("config/corpora.tsv", "outputs/data/word_order_summary.tsv"):
            log(f"Reference {relative}: SHA-256={hashlib.sha256((repo / relative).read_bytes()).hexdigest()}")
        log("Identity: exact # text content; integer-token FORM fallback; first occurrence; within corpus only. "
            "Entropy: natural log. JSD: sqrt(base-2 Jensen-Shannon divergence). SQLite cache: 64 MiB.")
        for cid in args.corpora:
            filename, expected_hash, _ = INPUTS[cid]
            path = corpus_dir / filename
            row = dict(corpus_id=cid, corpus=manifest[cid]["display_name"], input_path=str(path), status="aborted", error="")
            try:
                after[cid] = process_corpus(path, expected_hash, before[cid], extract, scratch,
                                            args.progress_seconds, log, row)
            except (OSError, ValueError, sqlite3.Error) as error:
                row["error"] = str(error)
                failures.append(cid)
                log(f"ABORTED {cid}: {error}; no deduplicated result published for this corpus")
            writer.writerow({key: f"{value:.12g}" if isinstance(value, float) else value for key, value in row.items()})
            table.flush()
        report_robustness(before, after, not failures and set(args.corpora) == set(INPUTS), log)
        log(f"Outputs: {out / 'dedup_sensitivity.tsv'}; {out / 'dedup_sensitivity.log'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
