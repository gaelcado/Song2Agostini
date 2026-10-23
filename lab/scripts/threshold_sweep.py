"""Balayage de seuils ADTOF sur activations en cache (aucune nouvelle inférence).

python lab/scripts/threshold_sweep.py RUNS_ROOT CASE... --sets '[[.22,.24,.32,.22,.30],[...]]'
Ordre des canaux (LABELS_5) : kick, snare, toms, hi-hat, cymbals.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from drum_lab.evaluation import match  # noqa: E402

CLASSES = ('kick', 'snare', 'hi-hat', 'toms', 'cymbals')
VER = REPO / 'work/verification/loop-20261017'
PICK = r'''
import sys, json, numpy as np, adtof_pytorch as a
acts = np.load(sys.argv[1]); sets = json.loads(sys.argv[2])
mapping = {35:'kick',38:'snare',47:'toms',42:'hi-hat',49:'cymbals'}
out = []
for th in sets:
    peaks = a.PeakPicker(thresholds=th, fps=100).pick(acts, labels=a.LABELS_5)[0]
    out.append([[float(t), mapping[p]] for p, times in peaks.items() for t in times])
print(json.dumps(out))
'''


def coverage(case):
    bars = json.loads((VER / 'refbars' / f'{case}.json').read_text())
    hits = [b for b in bars if b['has_hits']]
    lo = hits[0]['start'] - .3
    last = [b for b in bars if not b.get('fade')][-1]
    hi = last['end']
    excluded = [(b['start'], b['end']) for b in bars if not b.get('scored', True) or b.get('fade')]
    return lo, hi, excluded


def scores(ref, pred, lo, hi, excluded, tol=.05):
    keep = lambda t: lo <= t < hi and not any(a - .03 <= t < b - .03 for a, b in excluded)
    ref = [e for e in ref if keep(e['time'])]
    pred = [p for p in pred if keep(p[0])]
    out = {}
    for c in CLASSES:
        r = [e['time'] for e in ref if e['class'] == c]
        p = [t for t, k in pred if k == c]
        tp = len(match(r, p, tol)) if r and p else 0
        out[c] = (tp, len(p) - tp, len(r) - tp)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('runs'); ap.add_argument('cases', nargs='+'); ap.add_argument('--sets', required=True)
    a = ap.parse_args()
    sets = json.loads(a.sets)
    total = [{c: [0, 0, 0] for c in CLASSES} for _ in sets]
    for case in a.cases:
        run = REPO / a.runs / case
        key = json.loads((run / 'cache.json').read_text())['key']
        acts = REPO / 'work/cache' / key / 'activations.npy'
        res = subprocess.run([str(REPO / 'work/envs/adtof/bin/python'), '-c', PICK, str(acts), json.dumps(sets)],
                             capture_output=True, text=True, check=True)
        preds = json.loads(res.stdout.strip().splitlines()[-1])
        ref = json.loads((VER / 'refevents' / f'{case}.json').read_text())
        lo, hi, excluded = coverage(case)
        line = []
        for k, pred in enumerate(preds):
            sc = scores(ref, pred, lo, hi, excluded)
            for c in CLASSES:
                for j in range(3):
                    total[k][c][j] += sc[c][j]
            tp, fp, fn = (sum(sc[c][j] for c in CLASSES) for j in range(3))
            line.append(f'{2 * tp / (2 * tp + fp + fn):.3f}')
        print(f'{case:9s}', ' '.join(line), flush=True)
    for k, th in enumerate(sets):
        f = {c: (2 * v[0] / (2 * v[0] + v[1] + v[2]) if sum(v) else float('nan')) for c, v in total[k].items()}
        tp, fp, fn = (sum(total[k][c][j] for c in CLASSES) for j in range(3))
        print(th, 'micro %.4f' % (2 * tp / (2 * tp + fp + fn)), ' '.join(f'{c}:{f[c]:.3f}' for c in CLASSES))


if __name__ == '__main__':
    main()
