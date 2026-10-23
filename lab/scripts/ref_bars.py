"""Cache privé des barres de référence alignées (vérification), pour les études de structure.

python lab/scripts/ref_bars.py CASE...  -> work/verification/loop-20261017/refbars/CASE.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_check as sc  # noqa: E402
import midi_check as mc  # noqa: E402
from loop_bench import CASES, REPO  # noqa: E402

OUT = REPO / 'work/verification/loop-20261017/refbars'


def bars_for(case):
    audio, kind, ref = CASES[case]
    audio, ref = REPO / audio, REPO / ref
    times, env = sc.band_envelopes(audio)
    scorer = sc.Scorer(times, env)
    if kind == 'ref':
        bars = sc.parse_reference(ref)
        declared = [float(l.split()[1]) for l in ref.read_text().splitlines() if l.startswith('tempo ')]
        starts, beats, _ = sc.align(bars, scorer, declared[0] if declared else 96)
        out = [{'start': starts[i], 'end': starts[i] + b['num'] * beats[i], 'num': b['num'], 'scored': b.get('scored', True),
                'has_hits': bool(b['hits']), 'fade': b['fade']} for i, b in enumerate(bars) if i in starts]
        events = [e for e in sc.reference_events(bars, starts, beats) if not e['fade'] and e.get('scored', True)]
        (OUT.parent / 'refevents').mkdir(parents=True, exist_ok=True)
        (OUT.parent / 'refevents' / f'{case}.json').write_text(json.dumps(events))
    else:
        midi, events, downbeats, beats, sig = mc.midi_reference(ref)
        off = 0. if kind == 'midi0' else mc.estimate_offset(events, scorer)
        import numpy as np
        beats = np.asarray(beats) + off
        first = min(t for t, _ in events) + off
        last = max(t for t, _ in events) + off
        out = []
        for k, d in enumerate(downbeats):
            d += off
            end = (downbeats[k + 1] + off) if k + 1 < len(downbeats) else d + 2
            if end <= first - .05 or d > last + .05:
                continue
            out.append({'start': d, 'end': end, 'num': int(((beats >= d - 1e-6) & (beats < end - 1e-6)).sum()), 'scored': True, 'has_hits': True})
        (OUT.parent / 'refevents').mkdir(parents=True, exist_ok=True)
        (OUT.parent / 'refevents' / f'{case}.json').write_text(json.dumps([{'time': t + off, 'class': c} for t, c in events]))
    return out


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for case in sys.argv[1:]:
        (OUT / f'{case}.json').write_text(json.dumps(bars_for(case)))
        print(case, 'ok', flush=True)
