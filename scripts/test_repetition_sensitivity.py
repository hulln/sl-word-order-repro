#!/usr/bin/env python3
"""Post-run QA: synthetic fixtures and recorded-output reconciliation, no corpora.

Run from the public repository: python3 scripts/test_repetition_sensitivity.py
The original production scripts remain unchanged. Standard library only.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import dedup_sensitivity as dedup
import inspect_parlamint_duplicates as audit

ROOT = Path(__file__).resolve().parents[1]
SUP = ROOT / 'outputs/supplementary'


def block(text, changed=False, zero=False):
    """Synthetic two-OVS annotation, or a one-SVO alternative for the same text."""
    specs = [(1, 'Predlog', 'NOUN', 7, 'obj'),
             (6, 'zboru', 'NOUN', 7, 'obj'),
             (7, 'predložila', 'VERB', 0, 'root'),
             (8, 'vlada', 'NOUN', 7, 'nsubj')]
    if changed:
        specs = [(1, 'Predlog', 'NOUN', 7, 'nsubj'),
                 (6, 'zboru', 'NOUN', 7, 'obl'),
                 (7, 'predložila', 'VERB', 0, 'root'),
                 (8, 'vlada', 'NOUN', 7, 'obj')]
    if zero:
        specs = [(1, 'brez', 'ADP', 0, 'root')]
    header = '' if text is None else '# text = ' + text + '\n'
    return header + ''.join(
        f'{tid}\t{form}\t_\t{upos}\t_\t_\t{head}\t{rel}\t_\t_\n'
        for tid, form, upos, head, rel in specs) + '\n'


class RepetitionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extract, digest = dedup.load_extractor(ROOT)
        if digest != audit.EXTRACTOR_SHA256:
            raise AssertionError('Canonical extractor differs from production')

    def test_exact_identity_and_form_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.conllu'
            # Space, case, tab and Unicode differences must remain distinct.
            texts = ['Poved', 'Poved ', 'poved', 'Poved\t', 'é', 'e\u0301', '']
            source = ''.join(block(t) for t in texts)
            # Ranges/empty nodes are ignored by FORM fallback; EOF is supported.
            source += '1-2\tignored\t_\t_\t_\t_\t_\t_\t_\t_\n'
            source += '1.1\tignored\t_\t_\t_\t_\t_\t_\t_\t_\n'
            source += block(None).rstrip('\n')
            path.write_bytes(source.replace('\n', '\r\n').encode())
            rows = list(dedup.sentences(path))
            self.assertEqual([r[0] for r in rows], texts + ['Predlog zboru predložila vlada'])
            self.assertEqual([r[1] for r in rows], [False]*7 + [True])
            self.assertEqual(dict(type(self).extract(*rows[-1][2:5])), {'OVS': 2})

    def test_all_orders_and_cartesian_pairs(self):
        extract = type(self).extract
        for pattern in dedup.PATTERNS:
            ids = {role: i for i, role in enumerate(pattern, 1)}
            v, s, o = ids['V'], ids['S'], ids['O']
            counts = extract({v:'VERB', s:'NOUN', o:'NOUN'},
                             {v:'root', s:'nsubj', o:'obj'}, {v:0, s:v, o:v})
            self.assertEqual(dict(counts), {pattern:1})
        upos = {1:'NOUN', 2:'NOUN', 3:'VERB', 4:'NOUN', 5:'NOUN',
                6:'PROPN', 7:'NOUN', 8:'NOUN', 9:'AUX'}
        rel = {1:'obj', 2:'obj', 3:'root', 4:'nsubj', 5:'nsubj',
               6:'obj', 7:'iobj', 8:'nsubj:pass', 9:'root'}
        heads = {i:3 for i in upos}; heads[3]=heads[9]=0
        self.assertEqual(dict(extract(upos, rel, heads)), {'OVS':4})

    def test_first_retention_and_actual_later_annotation_accounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fixture.conllu'
            path.write_text(block('A')+block('A')+block('A',changed=True)
                            +block('a')+block('Z',zero=True)+block('Z',zero=True))
            extract = type(self).extract
            ordinary = dedup.scan(path, extract, math.inf, lambda _:None)
            with sqlite3.connect(':memory:') as seen:
                seen.execute('CREATE TABLE seen (identity BLOB PRIMARY KEY) WITHOUT ROWID')
                retained = dedup.scan(path, extract, math.inf, lambda _:None, seen)
            self.assertEqual(ordinary, (6,6,0,[1,0,0,0,0,6]))
            self.assertEqual(retained, (6,3,0,[0,0,0,0,0,4]))
            with sqlite3.connect(':memory:') as db, patch.object(audit, 'log', lambda _:None):
                audit.create_database(db)
                stats = audit.scan_duplicates(path, extract, db, math.inf)
                exported = Path(tmp)/'examples.tsv'
                result = audit.write_examples(db, exported, stats)
            self.assertEqual(stats['before'],ordinary[-1])
            self.assertEqual(stats['after'],retained[-1])
            self.assertEqual((result['repeated_types'],result['repeated_copies'],result['mismatch_types']), (2,3,1))
            with exported.open(newline='') as handle:
                records = {r['sentence_text']:r for r in csv.DictReader(handle,delimiter='\t')}
            a = records['A']
            self.assertEqual((int(a['excess_OVS']),int(a['excess_SVO']),int(a['nominal_excess_OVS'])), (2,1,4))
            self.assertEqual(int(records['Z']['excess_total']),0)
            variants=json.loads(a['pattern_count_variants_json'])
            self.assertEqual(sum(v['occurrences'] for v in variants),3)
            self.assertEqual(sum(v['retained_occurrences'] for v in variants),1)

    def test_entropy_and_distance_units(self):
        self.assertAlmostEqual(dedup.entropy([1]*6),math.log(6))
        self.assertEqual(dedup.entropy([1,0,0,0,0,0]),0)
        self.assertEqual(dedup.js_distance([1,0,0,0,0,0],[0,1,0,0,0,0]),1)
        self.assertEqual(dedup.js_distance([1]*6,[2]*6),0)
        with self.assertRaises(ValueError):
            dedup.entropy([0]*6)

    def test_recorded_results_and_claims(self):
        _, before = dedup.load_references(ROOT)
        after=dict(before)
        rows=dedup.read_table(SUP/'dedup_sensitivity.tsv')
        self.assertEqual(set(rows),set(dedup.INPUTS))
        for cid,r in rows.items():
            self.assertEqual(r['status'],'ok')
            self.assertEqual(r['input_sha256'],dedup.INPUTS[cid][1])
            b=[int(r[f'{p}_n_before']) for p in dedup.PATTERNS]
            a=[int(r[f'{p}_n_after']) for p in dedup.PATTERNS]
            self.assertEqual(b,before[cid]);after[cid]=a
            self.assertEqual(sum(b),int(r['svo_instances_before']))
            self.assertEqual(sum(a),int(r['svo_instances_after']))
            removed=int(r['sentences_before'])-int(r['sentences_after'])
            self.assertEqual(removed,int(r['duplicates_n']))
            self.assertAlmostEqual(100*removed/int(r['sentences_before']),float(r['duplicates_pct']),places=8)
            for p,n in zip(dedup.PATTERNS,a):
                self.assertAlmostEqual(100*n/sum(a),float(r[f'{p}_pct_after']),places=8)
            for phase,counts in [('before',b),('after',a)]:
                expected=math.log(sum(counts))-sum(n*math.log(n) for n in counts if n)/sum(counts)
                self.assertAlmostEqual(expected,float(r[f'entropy_nat_{phase}']),places=9)
            self.assertAlmostEqual(abs(100*a[0]/sum(a)-100*b[0]/sum(b)),float(r['abs_SVO_change_pp']),places=8)
            self.assertAlmostEqual(dedup.js_distance(b,a),float(r['js_distance_base2_pre_post']),places=10)
        baseline_checks=dedup.descriptive_checks(before)
        changed_checks=dedup.descriptive_checks(after)
        self.assertEqual(len(changed_checks),44)
        self.assertTrue(all(v>1e-12 for v in baseline_checks.values()))
        changed={k for k,v in changed_checks.items() if v<=1e-12}
        self.assertEqual(changed,{'ParlaMint highest OVS in nine-source register comparison',
                                  'ParlaMint lowest SVO among seven automatic register sources'})
        shares={cid:after[cid][0]/sum(after[cid]) for cid in dedup.AUTO_REGISTER}
        self.assertEqual(min(shares,key=shares.get),'janes-forum')
        audit.validate_checkpoint(dict(before=before['parlamint'],after=after['parlamint'],
                                       sentences=3876183,unique=3133122,fallback=0),SUP/'dedup_sensitivity.tsv')

    def test_complete_examples(self):
        path=SUP/'parlamint_duplicate_examples.tsv.gz'
        raw=gzip.decompress(path.read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '7dc9ae1f8372237086a1cfb4d381ea7118bd4e16dbb954004ba3fe3d8e7a60dc')
        rows=list(csv.DictReader(io.StringIO(raw.decode()),delimiter='\t'))
        self.assertEqual(len(rows),68984)
        self.assertEqual(sum(int(r['occurrences'])-1 for r in rows),743061)
        self.assertTrue(all(r['count_vectors_identical']=='1' for r in rows))
        removals=[sum(int(r[f'excess_{p}']) for r in rows) for p in dedup.PATTERNS]
        self.assertEqual(removals,[11498,1403,959,2525,363,27013])
        for r in rows:
            variants=json.loads(r['pattern_count_variants_json'])
            self.assertEqual(sum(v['occurrences'] for v in variants),int(r['occurrences']))
            for p in dedup.PATTERNS:
                self.assertEqual(sum(v['excess_counts'][p] for v in variants),int(r[f'excess_{p}']))
        ovs=sorted((int(r['excess_OVS']) for r in rows),reverse=True)
        self.assertEqual([sum(ovs[:k]) for k in [5,10,20]],[3387,4317,5356])
        inspected=next(r for r in rows if r['sentence_text']=='Predlog zakona je v obravnavo zboru predložila vlada Republike Slovenije.')
        self.assertEqual([int(inspected[k]) for k in ['occurrences','first_OVS','excess_OVS']], [513,2,1024])

    def test_preserved_raw_stdout(self):
        self.assertEqual((SUP/'dedup_run.stdout.log').read_bytes(),
                         b'nohup: ignoring input\n'+(SUP/'dedup_sensitivity.log').read_bytes())


if __name__=='__main__':
    unittest.main(verbosity=2)
