"""Vérificateur automatique partition ↔ référence symbolique (rôle vérification).

Lit une référence texte privée (data/reference/*.ref.txt), l'aligne sur l'audio
SANS utiliser les prédictions (enveloppes d'attaques par bandes + suivi mesure à
mesure), puis compare une sortie déjà produite :

- détection : événements bruts (events.json) contre coups de référence, 50/25 ms ;
- partition : notes du MusicXML expansé (ce que lit le musicien), position
  écrite convertie en secondes, et position mesure/temps comparée telle quelle ;
- structure : barres de mesure (premiers temps) et longueur des mesures (4/4, 5/4…).

Usage : python lab/scripts/score_check.py REF.txt AUDIO RUN_DIR [--out rapport.json]
Les rapports contiennent des détails : ils restent sous work/verification/.
"""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.signal import stft

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from drum_lab.evaluation import match  # noqa: E402

CLASSES = ('kick', 'snare', 'hi-hat', 'toms', 'cymbals')
REF_KEYS = {'bd': 'kick', 'sd': 'snare', 'hh': 'hi-hat', 'tt': 'toms', 'cr': 'cymbals'}
GM = {35: 'kick', 36: 'kick', 37: 'snare', 38: 'snare', 40: 'snare', 42: 'hi-hat', 44: 'hi-hat', 46: 'hi-hat',
      **{p: 'toms' for p in (41, 43, 45, 47, 48, 50)}, **{p: 'cymbals' for p in (49, 51, 52, 53, 55, 57, 59)}}
KICKS = {'a': [1, 3], 'b': [1, 3, 4.5], 'c': [1, 3, 3.5], 'd': [1, 3, 3.5, 4.5]}


# ---------------------------------------------------------------- référence
def _numbers(text):
    return [float(Fraction(v)) for v in text.split(',') if v]


def parse_reference(path):
    """Format texte : une ligne par mesure. Voir data/reference/*.ref.txt.

    def NOM jetons…  définit un motif ; [n/4] [*]MOTIF|x|rest [clé(=|+=|-=)temps…] [?]
    « ? » : mesure jouée mais non évaluée (roulement, notation ambiguë).
    repN répète les N mesures précédentes ; free = durée libre ; !fade = fondu.
    """
    bars, fade, macros = [], False, {}
    for raw in Path(path).read_text(encoding='utf-8').splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        tokens = line.split()
        if tokens[0] == '!fade':
            fade = True
            continue
        if tokens[0] == 'tempo':
            continue
        if tokens[0] == 'def':
            macros[tokens[1]] = tokens[2:]
            continue
        scored = '?' not in tokens
        tokens = [t for t in tokens if t != '?']
        if tokens[0].startswith('rest') and tokens[0][4:].isdigit() or tokens[0] == 'rest':
            for _ in range(int(tokens[0][4:] or 1)):
                bars.append({'free': False, 'num': 4, 'fade': fade, 'hits': {}, 'scored': scored})
            continue
        if tokens[0] == 'free':
            bars.append({'free': True, 'num': None, 'hits': {}, 'fade': fade})
            continue
        if tokens[0].startswith('rep'):
            n = int(tokens[0][3:])
            bars.extend({**json.loads(json.dumps(b)), 'fade': fade} for b in bars[-n:])
            continue
        num = 4
        if '/' in tokens[0] and '=' not in tokens[0]:
            num = int(tokens.pop(0).split('/')[0])
        hits = {k: set() for k in REF_KEYS}
        if tokens and '=' not in tokens[0]:
            base = tokens.pop(0)
            crash = base.startswith('*')
            base = base.lstrip('*')
            if base in macros:
                tokens = macros[base] + tokens
                if crash:
                    tokens.append('cr+=1'); tokens.append('hh-=1')
                crash = False
            elif base in KICKS:
                hits['hh'] = {1 + i / 2 for i in range(num * 2)}
                hits['sd'] = {2, 4}
                hits['bd'] = set(KICKS[base])
            elif base != 'x':
                raise ValueError(f'Motif inconnu : {raw}')
            if crash:
                hits['cr'].add(1)
                hits['hh'].discard(1)
        for token in tokens:
            for op in ('+=', '-=', '='):
                if op in token:
                    key, values = token.split(op)
                    values = set(_numbers(values))
                    hits[key] = hits[key] | values if op == '+=' else hits[key] - values if op == '-=' else values
                    break
            else:
                raise ValueError(f'Jeton inconnu : {raw}')
        for key, values in hits.items():
            if any(not 1 <= v < num + 1 for v in values):
                raise ValueError(f'Temps hors mesure : {raw}')
        bars.append({'free': False, 'num': num, 'fade': fade, 'scored': scored, 'hits': {k: sorted(v) for k, v in hits.items() if v}})
    return bars


# ---------------------------------------------------------------- audio
def band_envelopes(audio, sr=22050, hop=220):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(audio), '-f', 'f32le', '-ac', '1', '-ar', str(sr), '-'],
                         capture_output=True, check=True).stdout
    signal = np.frombuffer(pcm, dtype='<f4')
    freqs, times, spec = stft(signal, fs=sr, nperseg=1024, noverlap=1024 - hop, boundary=None)
    mag = np.log1p(100 * np.abs(spec))
    flux = np.maximum(0, np.diff(mag, axis=1))
    times = times[1:]
    bands = {'low': (30, 160), 'mid': (160, 2500), 'high': (5000, 11000)}
    env = {}
    for name, (lo, hi) in bands.items():
        e = flux[(freqs >= lo) & (freqs < hi)].mean(axis=0)
        # Normalisation locale robuste (dynamique, fondu) sur ~4 s.
        w = int(4 * sr / hop)
        pad = np.pad(e, w // 2, mode='edge')
        scale = np.array([np.percentile(pad[i:i + w], 95) for i in range(0, len(e), 25)])
        scale = np.interp(np.arange(len(e)), np.arange(0, len(e), 25), scale)
        env[name] = e / np.maximum(scale, 1e-6)
    return times, env


CLASS_BANDS = {'kick': ('low',), 'snare': ('mid',), 'hi-hat': ('high',), 'cymbals': ('high',), 'toms': ('low', 'mid')}
CLASS_WEIGHT = {'kick': 1.0, 'snare': 1.0, 'hi-hat': .35, 'cymbals': .5, 'toms': .7}


class Scorer:
    def __init__(self, times, env):
        self.dt = times[1] - times[0]
        self.t0 = times[0]
        # Maximum local ±20 ms : tolère l'imprécision de l'interprète.
        k = int(round(.02 / self.dt))
        self.env = {}
        for name, e in env.items():
            pad = np.pad(e, k, mode='constant')
            self.env[name] = np.max(np.stack([pad[i:i + len(e)] for i in range(2 * k + 1)]), axis=0)
        self.n = len(times)

    def value(self, cls, t):
        i = np.clip(np.round((np.asarray(t) - self.t0) / self.dt).astype(int), 0, self.n - 1)
        return np.mean([self.env[b][i] for b in CLASS_BANDS[cls]], axis=0)

    def bar(self, bar, start, beat):
        total = 0.
        for key, beats in bar['hits'].items():
            cls = REF_KEYS[key]
            t = start + (np.asarray(beats) - 1) * beat
            total += CLASS_WEIGHT[cls] * float(np.sum(np.minimum(self.value(cls, t), 2.)))
        return total


def align(bars, scorer, bpm_hint, search_until=120.):
    """Suivi mesure à mesure : ancrage sur les 8 premières mesures jouées, puis temps local ±4 %.

    Les mesures vides (silences) avant l'ancrage sont placées à rebours au tempo d'ancrage.
    """
    playable = [i for i, b in enumerate(bars) if not b['free']]
    with_hits = [i for i in playable if bars[i]['hits']]
    anchor = playable.index(with_hits[0])
    beat0 = 60 / bpm_hint
    best = (-1, None, None)
    window = [bars[i] for i in playable[anchor:anchor + 8]]
    for beat in beat0 * np.linspace(.93, 1.07, 29):
        for start in np.arange(0, search_until, .01):
            s, t = 0., start
            for b in window:
                s += scorer.bar(b, t, beat)
                t += b['num'] * beat
            if s > best[0]:
                best = (s, start, beat)
    _, start, beat = best
    starts, beats = {}, {}
    back = start
    for i in reversed(playable[:anchor]):
        back -= bars[i]['num'] * beat
        starts[i], beats[i] = float(back), float(beat)
    for pos in range(anchor, len(playable)):
        i = playable[pos]
        b = bars[i]
        nxt = bars[playable[pos + 1]] if pos + 1 < len(playable) else None
        cand = (-1, start, beat)
        for d in np.arange(-.06, .0601, .005):
            for f in np.linspace(.96, 1.04, 17):
                bb = beat * f
                s = scorer.bar(b, start + d, bb)
                if nxt is not None:
                    s += .5 * scorer.bar(nxt, start + d + b['num'] * bb, bb)
                s -= 2. * abs(d) + 4. * abs(f - 1)
                if s > cand[0]:
                    cand = (s, start + d, bb)
        _, start, bb = cand
        beat = .7 * beat + .3 * bb
        starts[i], beats[i] = float(start), float(bb)
        start = start + b['num'] * bb
    return starts, beats, playable[0]


def reference_events(bars, starts, beats):
    events = []
    for i, b in enumerate(bars):
        if b['free']:
            continue
        for key, values in b['hits'].items():
            for v in values:
                events.append({'time': starts[i] + (v - 1) * beats[i], 'class': REF_KEYS[key], 'bar': i, 'beat': v,
                               'fade': b['fade'], 'scored': b.get('scored', True)})
    return sorted(events, key=lambda e: e['time'])


# ---------------------------------------------------------------- MusicXML
def read_musicxml(path, offset):
    root = ET.parse(path).getroot()
    part = root.find('part')
    measures = part.findall('measure')
    order, stack, i, done = [], [], 0, set()
    while i < len(measures):
        m = measures[i]
        order.append(i)
        for rep in m.iter('repeat'):
            if rep.get('direction') == 'forward':
                stack.append(i)
        back = [r for r in m.iter('repeat') if r.get('direction') == 'backward']
        if back and i not in done:
            times = int(back[0].get('times', 2))
            start = stack.pop() if stack else 0
            for _ in range(times - 1):
                order.extend(range(start, i + 1))
            done.add(i)
        i += 1
    divisions, beats, beat_type, tempo = 1, 4, 4, 120.
    clock, out_measures, notes = offset, [], []
    for index in order:
        m = measures[index]
        attrs = m.find('attributes')
        if attrs is not None:
            if attrs.find('divisions') is not None:
                divisions = int(attrs.find('divisions').text)
            if attrs.find('time') is not None:
                beats = int(attrs.find('time/beats').text)
                beat_type = int(attrs.find('time/beat-type').text)
        pos, last_start, tempos, items = 0, 0, [], []
        for el in m:
            if el.tag == 'direction':
                sound = el.find('sound')
                if sound is not None and sound.get('tempo'):
                    tempos.append((pos, float(sound.get('tempo'))))
            elif el.tag == 'sound' and el.get('tempo'):
                tempos.append((pos, float(el.get('tempo'))))
            elif el.tag == 'backup':
                pos -= int(el.find('duration').text)
            elif el.tag == 'forward':
                pos += int(el.find('duration').text)
            elif el.tag == 'note':
                dur = el.find('duration')
                dur = int(dur.text) if dur is not None else 0
                start = last_start if el.find('chord') is not None else pos
                if el.find('rest') is None and el.find('instrument') is not None:
                    pitch = int(el.find('instrument').get('id').lstrip('I').split('-')[0])
                    items.append((start, GM.get(pitch)))
                if el.find('chord') is None:
                    last_start = pos
                    pos += dur
        length = beats * 4 / beat_type * divisions
        tempos.sort(key=lambda x: x[0])

        def seconds(p, base=clock, tempo0=tempo):
            t, cur, at = base, tempo0, 0
            for tp, tv in tempos:
                if tp > p:
                    break
                t += (tp - at) / divisions * 60 / cur
                cur, at = tv, tp
            return t + (p - at) / divisions * 60 / cur
        out_measures.append({'start': clock, 'quarters': beats * 4 / beat_type, 'signature': f'{beats}/{beat_type}'})
        for p, cls in items:
            if cls:
                notes.append({'time': seconds(p), 'class': cls, 'measure': len(out_measures) - 1,
                              'beat': 1 + p / divisions * beat_type / 4, 'frac': p / length})
        end = seconds(length)
        if tempos:
            tempo = tempos[-1][1]
        clock = end
    for k, m in enumerate(out_measures):
        m['end'] = out_measures[k + 1]['start'] if k + 1 < len(out_measures) else clock
    return out_measures, notes


# ---------------------------------------------------------------- métriques
def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': p, 'recall': r, 'f1': f}


def class_scores(ref, pred, tol):
    out = {}
    for cls in CLASSES:
        r = [e['time'] for e in ref if e['class'] == cls]
        p = [e['time'] for e in pred if e['class'] == cls]
        tp = len(match(r, p, tol)) if r and p else 0
        out[cls] = prf(tp, len(p) - tp, len(r) - tp)
    tot = [sum(out[c][k] for c in CLASSES) for k in ('tp', 'fp', 'fn')]
    present = [out[c]['f1'] for c in CLASSES if out[c]['tp'] + out[c]['fn']]
    return {'classes': out, 'micro': prf(*tot), 'macro_f1': float(np.mean([v or 0 for v in present])) if present else None}


def evaluate(ref_path, audio, run, bpm_hint=None, include_fade=False):
    bars = parse_reference(ref_path)
    times, env = band_envelopes(audio)
    scorer = Scorer(times, env)
    declared = [float(l.split()[1]) for l in Path(ref_path).read_text().splitlines() if l.startswith('tempo ')]
    bpm_hint = declared[0] if declared else (bpm_hint or 96)
    starts, beats, first = align(bars, scorer, bpm_hint)
    ref = reference_events(bars, starts, beats)
    # Qualité d'alignement : part des coups kick/snare avec une attaque de bande nette.
    ks = [e for e in ref if e['class'] in ('kick', 'snare') and not e['fade']]
    support = float(np.mean([scorer.value(e['class'], e['time']) > .35 for e in ks]))
    played = [i for i, b in enumerate(bars) if not b['free'] and (include_fade or not b['fade'])]
    lo = starts[played[0]] - .3
    last = played[-1]
    hi = starts[last] + bars[last]['num'] * beats[last]
    excluded = [(starts[i], starts[i] + bars[i]['num'] * beats[i]) for i in played if not bars[i].get('scored', True)]
    ref_in = [e for e in ref if lo <= e['time'] < hi and (include_fade or not e['fade']) and e.get('scored', True)]
    ref_bars = [{'index': i, 'start': starts[i], 'end': starts[i] + bars[i]['num'] * beats[i], 'num': bars[i]['num']} for i in played]
    report = compare(ref_in, ref_bars, run, lo, hi, excluded=excluded)
    report.update({'reference': str(ref_path), 'reference_bars': len(played),
                   'alignment': {'kick_snare_band_support': support, 'start_seconds': starts[played[0]],
                                 'median_beat_seconds': float(np.median([beats[i] for i in played]))}})
    report['_private'] = {'bar_starts': {str(i): starts[i] for i in played}}
    return report


def compare(ref_in, ref_bars, run, lo, hi, beat_tolerance=.13, excluded=()):
    """Compare a frozen run with reference events {time,class,bar,beat} and bars {index,start,end,num}.

    Predictions inside excluded intervals (unscored bars) are ignored, not counted as errors.
    """
    run = Path(run)
    keep = lambda t: lo <= t < hi and not any(a - .03 <= t < b - .03 for a, b in excluded)
    report = {'run': str(run), 'coverage_seconds': [lo, hi], 'reference_hits': len(ref_in)}
    raw = json.loads((run / 'events.json').read_text())['events']
    raw = [e for e in raw if keep(e['time'])]
    report['detection_50ms'] = class_scores(ref_in, raw, .05)
    report['detection_25ms'] = class_scores(ref_in, raw, .025)
    production = json.loads((run / 'production.json').read_text())
    offset = production.get('quality', {}).get('musicxml_audio_offset_seconds', 0.)
    measures, notes = read_musicxml(run / 'score.musicxml', offset)
    written = [n for n in notes if keep(n['time'])]
    report['written_70ms'] = class_scores(ref_in, written, .07)
    ref_bar_starts = [b['start'] for b in ref_bars]
    pred_bar_starts = [m['start'] for m in measures if lo - .2 <= m['start'] < hi]
    tp = len(match(ref_bar_starts, pred_bar_starts, .1))
    report['barlines_100ms'] = prf(tp, len(pred_bar_starts) - tp, len(ref_bar_starts) - tp)
    # Mesures identiques : début et fin à ±100 ms (vérifie la signature locale).
    exact, bar_map = {}, {}
    for b in ref_bars:
        key = str(b['num'])
        exact.setdefault(key, [0, 0])[1] += 1
        for k, m in enumerate(measures):
            if abs(m['start'] - b['start']) <= .1 and abs(m['end'] - b['end']) <= .1:
                exact[key][0] += 1
                bar_map[k] = b['index']
                break
    report['bars_identical'] = {k: {'ok': v[0], 'total': v[1], 'rate': v[0] / v[1] if v[1] else None} for k, v in sorted(exact.items())}
    # Ce que lit le musicien : même mesure (appariée), même temps écrit (±1/8 de temps), même instrument.
    per_class = {}
    for cls in CLASSES:
        tp = nr = npred = 0
        groups = {}
        nums = {b['index']: b['num'] for b in ref_bars}
        for e in ref_in:
            if e['class'] == cls:
                groups.setdefault(e['bar'], ([], []))[0].append((e['beat'] - 1) / nums[e['bar']])
        for n in written:
            if n['class'] == cls:
                groups.setdefault(bar_map.get(n['measure'], ('unmatched', n['measure'])), ([], []))[1].append(n['frac'])
        # Position en fraction de mesure : indépendante de l'unité de temps écrite (noire, croche…).
        for key, (r, q) in groups.items():
            nr += len(r); npred += len(q)
            tol = beat_tolerance / max(nums.get(key, 4), 1)
            tp += len(match(r, q, tol)) if r and q else 0
        per_class[cls] = prf(tp, npred - tp, nr - tp)
    tot = [sum(per_class[c][k] for c in CLASSES) for k in ('tp', 'fp', 'fn')]
    report['written_bar_position'] = {**prf(*tot), 'classes': per_class}
    report['predicted_measures'] = len(measures)
    report['predicted_signatures'] = sorted({m['signature'] for m in measures})
    return report


def summary(report):
    d, w, b = report['detection_50ms'], report['written_70ms'], report['written_bar_position']
    f = lambda v: '—' if v is None else f'{v:.3f}'
    lines = [f"alignement: support kick/snare {report['alignment']['kick_snare_band_support']:.2f}, "
             f"départ {report['alignment']['start_seconds']:.2f}s, temps médian {report['alignment']['median_beat_seconds']:.3f}s",
             f"détection 50ms  micro {f(d['micro']['f1'])} macro {f(d['macro_f1'])} | " +
             ' '.join(f"{c}:{f(d['classes'][c]['f1'])}" for c in CLASSES),
             f"écrit 70ms      micro {f(w['micro']['f1'])} macro {f(w['macro_f1'])} | " +
             ' '.join(f"{c}:{f(w['classes'][c]['f1'])}" for c in CLASSES),
             f"mesure+temps    F1 {f(b['f1'])} | " + ' '.join(f"{c}:{f(b['classes'][c]['f1'])}" for c in CLASSES),
             f"barres 100ms    F1 {f(report['barlines_100ms']['f1'])} ; mesures identiques " +
             ' '.join(f"{k}:{v['ok']}/{v['total']}" for k, v in report['bars_identical'].items() if v['total']),
             f"sortie: {report['predicted_measures']} mesures, signatures {report['predicted_signatures']}"]
    return '\n'.join(lines)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('reference'); ap.add_argument('audio'); ap.add_argument('run')
    ap.add_argument('--bpm', type=float, default=None); ap.add_argument('--out')
    a = ap.parse_args()
    rep = evaluate(a.reference, a.audio, a.run, a.bpm)
    print(summary(rep))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rep, indent=1))
