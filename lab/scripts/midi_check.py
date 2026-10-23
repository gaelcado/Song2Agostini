"""Vérification d'un run contre une référence MIDI (corpus GMD tech_* / OGA bench_*).

Le MIDI fournit coups, tempo et signature ; les premiers temps viennent de sa
grille. Le décalage audio↔MIDI est estimé sur l'audio seul (enveloppes de
bandes), jamais sur les prédictions. Usage :
  python lab/scripts/midi_check.py MIDI AUDIO RUN [--offset auto|0] [--out f.json]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pretty_midi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_check import CLASSES, Scorer, band_envelopes, compare, summary  # noqa: E402

# GM + extensions Roland du Groove MIDI Dataset (mapping documenté par Magenta).
MIDI_CLASS = {35: 'kick', 36: 'kick', 37: 'snare', 38: 'snare', 40: 'snare',
              22: 'hi-hat', 26: 'hi-hat', 42: 'hi-hat', 44: 'hi-hat', 46: 'hi-hat',
              41: 'toms', 43: 'toms', 45: 'toms', 47: 'toms', 48: 'toms', 50: 'toms', 58: 'toms',
              49: 'cymbals', 51: 'cymbals', 52: 'cymbals', 53: 'cymbals', 55: 'cymbals', 57: 'cymbals', 59: 'cymbals'}


def midi_reference(path):
    midi = pretty_midi.PrettyMIDI(str(path))
    events = sorted((n.start, MIDI_CLASS[n.pitch]) for i in midi.instruments if i.is_drum for n in i.notes if n.pitch in MIDI_CLASS)
    downbeats = list(midi.get_downbeats())
    beats = list(midi.get_beats())
    sig = midi.time_signature_changes[0] if midi.time_signature_changes else None
    return midi, [(t, c) for t, c in events if c], downbeats, beats, sig


def estimate_offset(events, scorer, span=2.0):
    best = (-1, 0.)
    times = np.asarray([t for t, c in events if c in ('kick', 'snare')])
    classes = [c for t, c in events if c in ('kick', 'snare')]
    for off in np.arange(-span, span + 1e-9, .005):
        v = sum(float(np.sum(scorer.value(c, times[np.array(classes) == c] + off))) for c in ('kick', 'snare'))
        if v > best[0]:
            best = (v, float(off))
    return best[1]


def evaluate(midi_path, audio, run, offset='auto'):
    midi, events, downbeats, beats, sig = midi_reference(midi_path)
    times, env = band_envelopes(audio)
    scorer = Scorer(times, env)
    off = estimate_offset(events, scorer) if offset == 'auto' else float(offset)
    events = [(t + off, c) for t, c in events]
    downbeats = [d + off for d in downbeats]
    beats = np.asarray(beats) + off
    first = min(t for t, _ in events)
    last = max(t for t, _ in events)
    bars = []
    for k, d in enumerate(downbeats):
        end = downbeats[k + 1] if k + 1 < len(downbeats) else d + (d - downbeats[k - 1] if k else 2.)
        if end <= first - .05 or d > last + .05:
            continue
        num = int(np.sum((beats >= d - 1e-6) & (beats < end - 1e-6)))
        bars.append({'index': k, 'start': d, 'end': end, 'num': num})
    lo, hi = bars[0]['start'] - .3, bars[-1]['end']
    ref = []
    for t, c in events:
        if not lo <= t < hi:
            continue
        k = max(i for i, b in enumerate(bars) if b['start'] <= t + .05) if t + .05 >= bars[0]['start'] else 0
        b = bars[k]
        beat_len = (b['end'] - b['start']) / max(b['num'], 1)
        ref.append({'time': t, 'class': c, 'bar': b['index'], 'beat': 1 + (t - b['start']) / beat_len})
    report = compare(ref, bars, run, lo, hi)
    report.update({'reference': str(midi_path), 'reference_bars': len(bars),
                   'alignment': {'offset_seconds': off, 'kick_snare_band_support': float(np.mean(
                       [scorer.value(e['class'], e['time']) > .35 for e in ref if e['class'] in ('kick', 'snare')] or [0])),
                       'start_seconds': bars[0]['start'], 'median_beat_seconds': float(np.median(np.diff(beats)))},
                   'reference_signature': f'{sig.numerator}/{sig.denominator}' if sig else None})
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('midi'); ap.add_argument('audio'); ap.add_argument('run')
    ap.add_argument('--offset', default='auto'); ap.add_argument('--out')
    a = ap.parse_args()
    rep = evaluate(a.midi, a.audio, a.run, a.offset)
    print(summary(rep))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rep, indent=1))
