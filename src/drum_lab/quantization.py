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
        increments = np.where(gaps > 1.8*interval, np.maximum(1, np.rint(gaps/interval)), 1)
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
    # Include pickup material without changing beat phase: prepend complete bars.
    first = min(to_beat(n.start) for n in hits)
    prepend = max(0, math.ceil(-round(first*4)/16))
    mapped=[]
    for n in hits:
        slot=round((to_beat(n.start)+prepend*4)*4)
        start=to_seconds(slot/4-prepend*4)
        # An onset extremely close to audio zero can round before the audio domain.
        start=max(0., start)
        mapped.append((n, slot, start))
    shifts=np.asarray([abs(start-n.start) for n,slot,start in mapped])
    pairs=[(slot,n.pitch) for n,slot,start in mapped]
    quality={'median_shift_ms':float(np.median(shifts)*1000),
             'max_shift_ms':float(np.max(shifts)*1000),
             'large_shift_threshold_ms':50, 'large_shift_count':int((shifts>.05).sum()),
             'collision_count':len(pairs)-len(set(pairs)), 'pickup_prepend_measures':prepend,
             'extrapolation_policy':'edge interval, tracked beats only; no fabricated beat at audio zero'}
    return mapped, lambda t: to_beat(t)+prepend*4, lambda b: to_seconds(b-prepend*4), quality
