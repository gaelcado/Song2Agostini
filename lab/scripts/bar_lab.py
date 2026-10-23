"""Étude hors ligne du découpage en mesures (activations Beat This en cache + barres de référence privées)."""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from drum_lab.bars import segment_bars, beat_activation, default_prior  # noqa: E402
from drum_lab.grid import clean_model_grid  # noqa: E402
from drum_lab.evaluation import match  # noqa: E402

ACTS = REPO / 'work/research/loop-20261017/acts'
REFS = REPO / 'work/verification/loop-20261017/refbars'


def load(case):
    z = np.load(ACTS / f'{case}.npz')
    g = clean_model_grid({'beat_times_seconds': z['beats'].tolist(), 'downbeat_times_seconds': z['downbeats'].tolist(),
                          'raw_beat_downbeat_activation': beat_activation(z['beats'], z['down'])})
    return z, g, json.loads((REFS / f'{case}.json').read_text())


def score(pred_starts, ref):
    hb = [b for b in ref if b['has_hits']]
    lo, hi = hb[0]['start'] - .2, hb[-1]['end'] - .2
    rb = [b for b in ref if lo <= b['start'] < hi]
    pred = np.asarray([p for p in pred_starts if lo <= p < hi])
    rs = [b['start'] for b in rb]
    tp = len(match(rs, list(pred), .1))
    f1 = 2 * tp / (len(rs) + len(pred)) if len(rs) + len(pred) else None
    exact = 0
    for b in rb:
        inside = pred[(pred > b['start'] + .1) & (pred < b['end'] - .1)]
        if len(pred) and np.min(abs(pred - b['start'])) <= .1 and np.min(abs(pred - b['end'])) <= .1 and not len(inside):
            exact += 1
    return f1, exact / len(rb)


def methods(z, g, **kw):
    beats = np.asarray(g['beat_times_seconds'])
    a = g['beat_downbeat_activation']
    out = {}
    origin = g['origin_seconds']
    i0 = int(np.argmin(abs(beats - origin)))
    out['fixed4'] = list(beats[i0::4])
    out['raw_downbeats'] = list(g['downbeat_times_seconds'])
    out['dp'] = list(beats[segment_bars(a, **kw)])
    return out


if __name__ == '__main__':
    cases = sys.argv[1:] or sorted(p.stem for p in REFS.glob('*.json'))
    agg = {}
    for case in cases:
        z, g, ref = load(case)
        row = []
        for name, starts in methods(z, g).items():
            f1, ex = score(starts, ref)
            agg.setdefault(name, []).append((f1, ex))
            row.append(f'{name}: F1 {f1:.2f} exact {ex:.2f}')
        print(f'{case:9s}', ' | '.join(row))
    for name, v in agg.items():
        print('MOYENNE', name, 'F1 %.3f exact %.3f' % tuple(np.mean(v, axis=0)))


def drum_evidence(beats, events, wc=1., wk=.5, ws=.5):
    t = {c: np.asarray([e['time'] for e in events if e['class'] == c]) for c in ('kick', 'snare', 'cymbals')}
    near = lambda c, b, tol: bool(len(t[c]) and np.min(abs(t[c] - b)) <= tol)
    return np.asarray([wc * near('cymbals', b, .06) + wk * near('kick', b, .05) - ws * (near('snare', b, .05) and not near('kick', b, .05))
                       for b in beats])


def run_h2(cases, runs, **w):
    agg = []
    for case in cases:
        z, g, ref = load(case)
        ev = json.loads((REPO / runs[case] / 'events.json').read_text())['events']
        beats = np.asarray(g['beat_times_seconds'])
        a = np.asarray(g['beat_downbeat_activation'])
        base = segment_bars(a)
        lg = np.log(a + 1e-3) - np.log(1 - a + 1e-3) + drum_evidence(beats, ev, **w)
        boosted = 1 / (1 + np.exp(-lg))
        h2 = segment_bars(boosted, prior=default_prior(a))
        r0, r1 = score(list(beats[base]), ref), score(list(beats[h2]), ref)
        agg.append((r0[1], r1[1]))
        print(f'{case:8s} dp exact {r0[1]:.2f} -> h2 {r1[1]:.2f}')
    print('MOYENNE', np.mean(agg, axis=0))
