"""Boucle de recherche bornée : génère (audio seul) puis vérifie (processus séparé).

python lab/scripts/loop_bench.py NOM_CONFIG 'JSON_CONFIG' [--cases ps tech_01 ...] [--root work/research/loop-20261017]

La génération appelle drum_lab.pipeline.generate avec l'audio uniquement ; la
vérification relit ensuite la sortie figée avec score_check / midi_check.
Le tableau agrégé est écrit dans ROOT/results/NOM_CONFIG.json.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / '.venv/bin/python')
CASES = {'ps': ('data/raw/audio/desktop-2026-10-17/Deep Purple - Perfect Strangers.mp3', 'ref', 'data/reference/perfect-strangers.ref.txt')}
CASES['md'] = ('data/raw/audio/piece_01.mp3', 'ref', 'data/reference/deluxe-michael.ref.txt')
CASES['bacalao'] = ('data/raw/audio/piece_02.mp3', 'ref', 'data/reference/bacalao.ref.txt')  # contrôle gelé
CASES['heathens'] = ('data/raw/audio/gmail-2026-10-10/twenty-one-pilots-heathens drums.MP3', 'ref', 'data/reference/heathens.ref.txt')
CASES['crazy'] = ('data/raw/audio/gmail-2026-10-10/Simple Plan - Crazy.mp3', 'ref', 'data/reference/crazy.ref.txt')
for i in range(1, 10):
    CASES[f'tech_{i:02d}'] = (f'data/raw/audio/tech_{i:02d}.wav', 'midi0', f'data/raw/scores/tech_{i:02d}.original.mid')
for i in range(1, 11):
    ext = 'mp3' if i in (8, 9) else 'wav'
    CASES[f'bench_{i:02d}'] = (f'data/raw/audio/bench_{i:02d}.{ext}', 'midi', f'data/raw/scores/bench_{i:02d}.original.mid')

GEN = '''
import json, sys
from drum_lab.pipeline import generate
audio, out, cfg, title = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), sys.argv[4]
r = generate(audio, out, config=cfg, piece_id='piece_01', title=title)
print(json.dumps({'status': r['status'], 'seconds': r['duration_seconds']}))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('config')
    ap.add_argument('--cases', nargs='+', default=list(CASES))
    ap.add_argument('--root', default='work/research/loop-20261017')
    ap.add_argument('--verify-only', action='store_true')
    a = ap.parse_args()
    root = REPO / a.root
    results = {}
    out_file = root / 'results' / f'{a.name}.json'
    if out_file.exists():
        results = json.loads(out_file.read_text())
    for case in a.cases:
        audio, kind, ref = CASES[case]
        run = root / 'runs' / a.name / case
        started = time.monotonic()
        if not a.verify_only:
            gen = subprocess.run([PY, '-c', GEN, str(REPO / audio), str(run), a.config, case],
                                 cwd=REPO, capture_output=True, text=True)
            if gen.returncode:
                results[case] = {'status': 'failed', 'error': gen.stderr[-800:]}
                print(case, 'ÉCHEC génération', gen.stderr[-300:], flush=True)
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(json.dumps(results, indent=1))
                continue
        report = root.parent.parent / 'verification' / root.name / a.name / f'{case}.json'
        if kind == 'ref':
            cmd = [PY, 'lab/scripts/score_check.py', ref, audio, str(run), '--out', str(report)]
        else:
            cmd = [PY, 'lab/scripts/midi_check.py', ref, audio, str(run), '--out', str(report)] + (['--offset', '0'] if kind == 'midi0' else [])
        ver = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if ver.returncode:
            results[case] = {'status': 'verify_failed', 'error': ver.stderr[-800:]}
            print(case, 'ÉCHEC vérification', ver.stderr[-300:], flush=True)
        else:
            rep = json.loads(report.read_text())
            results[case] = {'status': 'ok', 'seconds': time.monotonic() - started,
                             'detection_f1': rep['detection_50ms']['micro']['f1'],
                             'detection_macro': rep['detection_50ms']['macro_f1'],
                             'written_f1': rep['written_70ms']['micro']['f1'],
                             'bar_position_f1': rep['written_bar_position']['f1'],
                             'barlines_f1': rep['barlines_100ms']['f1'],
                             'bars_identical': rep['bars_identical'],
                             'per_class_detection': {c: rep['detection_50ms']['classes'][c]['f1'] for c in rep['detection_50ms']['classes']},
                             'per_class_bar_position': {c: rep['written_bar_position']['classes'][c]['f1'] for c in rep['written_bar_position']['classes']},
                             'signatures': rep['predicted_signatures']}
            print(case, ver.stdout.strip().replace('\n', ' || '), flush=True)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(results, indent=1))


if __name__ == '__main__':
    main()
