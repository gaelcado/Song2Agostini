"""Quantification indépendante de toute référence ; diagnostics conservés."""
import math
import numpy as np


def quantize_hits(hits, grid):
    bpm = float(grid['bpm'])
    origin = float(grid.get('origin_seconds', 0))
    if not math.isfinite(bpm) or bpm <= 0 or not math.isfinite(origin) or origin < 0:
        raise ValueError('Grille de quantification invalide')
    if not hits:
        raise ValueError('Aucun coup à quantifier')
    beats = np.asarray(grid.get('beat_times_seconds', []), dtype=float)
    if beats.size and (len(beats) < 2 or not np.isfinite(beats).all() or (beats < 0).any() or (np.diff(beats) <= 0).any()):
        raise ValueError('Temps de beats invalides')
    if beats.size:
        # The selected first tracked beat is the proposed bar origin, never audio zero.
        interval = float(np.median(np.diff(beats)))
        gaps = np.diff(beats)
        # Sparse tracking during silence leaves missing quarter beats, not a long slow beat.
        increments = (np.ones(len(gaps)) if grid.get('meter_evidence') else
                      np.where(gaps > 1.8*interval, np.maximum(1, np.rint(gaps/interval)), 1))
        pulse_length = float(grid.get('pulse_quarter_length', 1.))
        increments = increments * pulse_length
        coordinates = np.concatenate(([0.], np.cumsum(increments)))
        # A boundary gap may itself contain missing beats. Extrapolate one
        # quarter beat, not the whole observed gap; use the local edge tempo.
        first_interval = float(gaps[0]/increments[0])
        last_interval = float(gaps[-1]/increments[-1])
        origin_coord = float(np.interp(origin, beats, coordinates))
        if origin < beats[0]: origin_coord = (origin-beats[0])/first_interval
        if origin > beats[-1]: origin_coord = coordinates[-1]+(origin-beats[-1])/last_interval
        def to_beat(t):
            if t < beats[0]: value = (t-beats[0])/first_interval
            elif t > beats[-1]: value = coordinates[-1]+(t-beats[-1])/last_interval
            else: value = np.interp(t, beats, coordinates)
            return float(value-origin_coord)
        def to_seconds(b):
            c = b+origin_coord
            if c < 0: return float(beats[0]+c*first_interval)
            if c > coordinates[-1]: return float(beats[-1]+(c-coordinates[-1])*last_interval)
            return float(np.interp(c, coordinates, beats))
    else:
        def to_beat(t): return (t-origin)*bpm/60
        def to_seconds(b): return origin+b*60/bpm
    # A local tuplet requires both inner thirds in the actual predicted attacks.
    # Never complete a triplet from one onset or from a musical expectation.
    triplet_beats = []
    if grid.get('local_tuplets') and grid.get('time_signature', '4/4').split('/')[1] == '4':
        groups = {}
        for n in hits:
            b = to_beat(n.start)
            groups.setdefault(math.floor(b), []).append(b % 1)
        for beat, fractions in groups.items():
            values = np.asarray(fractions)
            ternary = np.rint(values * 3) / 3
            binary = np.rint(values * 4) / 4
            inner = set(np.rint(values * 3).astype(int)) & {1, 2}
            if (inner == {1, 2} and np.max(abs(values-ternary)) <= .07
                    and np.mean(abs(values-binary)-abs(values-ternary)) >= .035):
                triplet_beats.append(beat)
    divisions = 12 if triplet_beats else 4
    # Include pickup material without changing beat phase: prepend complete bars.
    first = min(to_beat(n.start) for n in hits)
    numerator, denominator = map(int, grid.get('time_signature', '4/4').split('/'))
    bar_quarters = numerator * 4 / denominator
    if grid.get('bar_beats'):
        # Variable bars: a pickup is completed with the first estimated bar length.
        bar_quarters = float(grid['bar_beats'][0]) * float(grid.get('pulse_quarter_length', 1.))
    # A dotted pulse spans six sixteenth slots; never discard its inner offbeats.
    step = 1
    prepend = max(0, math.ceil(-round(first*4/step)*step/(bar_quarters*4)))
    mapped=[]
    for n in hits:
        b = to_beat(n.start)
        if math.floor(b) in triplet_beats:
            quantized = math.floor(b) + round((b % 1)*3)/3
        else:
            quantized = round(b*4)/4
        slot = round((quantized+prepend*bar_quarters)*divisions)
        start=to_seconds(slot/divisions-prepend*bar_quarters)
        # An onset extremely close to audio zero can round before the audio domain.
        start=max(0., start)
        mapped.append((n, slot, start))
    shifts=np.asarray([abs(start-n.start) for n,slot,start in mapped])
    pairs=[(slot,n.pitch) for n,slot,start in mapped]
    quality={'divisions':divisions, 'local_triplet_beats':[int(b+prepend*bar_quarters) for b in triplet_beats],
             'tuplet_policy':'two observed inner thirds; max error .07 quarter; mean gain .035 quarter; no added hits',
             'median_shift_ms':float(np.median(shifts)*1000),
             'max_shift_ms':float(np.max(shifts)*1000),
             'large_shift_threshold_ms':50, 'large_shift_count':int((shifts>.05).sum()),
             'tracked_gap_policy':'observed pulses without global missing-beat repair' if grid.get('meter_evidence') else 'global median missing-beat repair',
             'collision_count':len(pairs)-len(set(pairs)), 'pickup_prepend_measures':prepend,
             'pickup_bar_quarters':bar_quarters,
             'extrapolation_policy':'edge interval, tracked beats only; no fabricated beat at audio zero'}
    return mapped, lambda t: to_beat(t)+prepend*bar_quarters, lambda b: to_seconds(b-prepend*bar_quarters), quality
