"""Tableau agrégé des variantes (feedback public : uniquement des moyennes et comptes).

python lab/scripts/loop_table.py [VARIANTE...]
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / 'work/research/loop-20261017/results'
GROUPS = {'réels': ['ps', 'md', 'crazy', 'heathens'], 'gmd': [f'tech_{i:02d}' for i in range(1, 10)], 'oga': ['bench_02', 'bench_04', 'bench_08']}
METRICS = ('detection_f1', 'written_f1', 'bar_position_f1', 'barlines_f1')


def exact_rate(r):
    ok = sum(v['ok'] for v in r['bars_identical'].values())
    total = sum(v['total'] for v in r['bars_identical'].values())
    return ok / total if total else None


def main():
    names = sys.argv[1:] or sorted(p.stem for p in ROOT.glob('*.json'))
    print(f"{'variante':22s} {'groupe':6s} " + ' '.join(f'{m[:12]:>12s}' for m in METRICS) + f" {'mesures=':>9s}  n")
    for name in names:
        data = json.loads((ROOT / f'{name}.json').read_text())
        for group, cases in GROUPS.items():
            rows = [data[c] for c in cases if data.get(c, {}).get('status') == 'ok']
            if not rows:
                continue
            vals = [np.mean([r[m] or 0 for r in rows]) for m in METRICS]
            ex = np.mean([exact_rate(r) or 0 for r in rows])
            print(f'{name:22s} {group:6s} ' + ' '.join(f'{v:12.3f}' for v in vals) + f' {ex:9.3f} {len(rows):2d}')
        per = {c: data[c]['bar_position_f1'] for c in GROUPS['réels'] if data.get(c, {}).get('status') == 'ok'}
        if per:
            print(' ' * 30 + 'réels mesure+temps : ' + ', '.join(f'{c} {v:.3f}' for c, v in per.items()))


if __name__ == '__main__':
    main()
