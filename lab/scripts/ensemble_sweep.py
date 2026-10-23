"""Combinaison d'activations ADTOF mix + batterie isolée (caches existants, aucune inférence).

python lab/scripts/ensemble_sweep.py STEM_RUNS MIX_RUNS CASE... [--methods stem mix mean max]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from threshold_sweep import CLASSES, coverage, scores  # noqa: E402

PICK = r'''
import sys, json, numpy as np, adtof_pytorch as a
stem = np.load(sys.argv[1]); mix = np.load(sys.argv[2]); methods = json.loads(sys.argv[3]); th = json.loads(sys.argv[4])
n = min(stem.shape[1], mix.shape[1]); stem, mix = stem[:, :n], mix[:, :n]
combos = {'stem': stem, 'mix': mix, 'mean': (stem + mix) / 2, 'max': np.maximum(stem, mix), 'min': np.minimum(stem, mix)}
mapping = {35:'kick',38:'snare',47:'toms',42:'hi-hat',49:'cymbals'}
out = {}
for m in methods:
    peaks = a.PeakPicker(thresholds=th, fps=100).pick(combos[m], labels=a.LABELS_5)[0]
    out[m] = [[float(t), mapping[p]] for p, times in peaks.items() for t in times]
print(json.dumps(out))
'''


def acts(run):
    key = json.loads((run / 'cache.json').read_text())['key']
    return REPO / 'work/cache' / key / 'activations.npy'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem_runs'); ap.add_argument('mix_runs'); ap.add_argument('cases', nargs='+')
    ap.add_argument('--methods', nargs='+', default=['stem', 'mix', 'mean', 'max'])
    ap.add_argument('--thresholds', default='[0.22,0.24,0.32,0.22,0.30]')
    a = ap.parse_args()
    total = {m: {c: np.zeros(3) for c in CLASSES} for m in a.methods}
    for case in a.cases:
        res = subprocess.run([str(REPO / 'work/envs/adtof/bin/python'), '-c', PICK, str(acts(REPO / a.stem_runs / case)),
                              str(acts(REPO / a.mix_runs / case)), json.dumps(a.methods), a.thresholds],
                             capture_output=True, text=True, check=True)
        preds = json.loads(res.stdout.strip().splitlines()[-1])
        ref = json.loads((REPO / 'work/verification/loop-20261017/refevents' / f'{case}.json').read_text())
        lo, hi, ex = coverage(case)
        row = []
        for m in a.methods:
            s = scores(ref, preds[m], lo, hi, ex)
            for c in CLASSES:
                total[m][c] += s[c]
            tp, fp, fn = (sum(s[c][j] for c in CLASSES) for j in range(3))
            row.append(f'{m} {2 * tp / (2 * tp + fp + fn):.3f}')
        print(f'{case:9s}', ' | '.join(row), flush=True)
    f = lambda v: 2 * v[0] / (2 * v[0] + v[1] + v[2]) if v.sum() else float('nan')
    for m in a.methods:
        allv = sum(total[m].values())
        print(f'{m:5s} micro {f(allv):.4f} ' + ' '.join(f'{c}:{f(total[m][c]):.3f}' for c in CLASSES))


if __name__ == '__main__':
    main()
