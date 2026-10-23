"""Variable-length bars from audio downbeat activations; no reference access.

The beat tracker proposes downbeat peaks that are often right but also adds
spurious ones (fills, odd bars). A fixed 4/4 count from the first tracked beat
instead propagates any intro irregularity to the whole score. Here a dynamic
programme chooses one bar segmentation of the tracked beats: it rewards bar
starts where the downbeat activation is high, penalises activation inside
bars, prefers the dominant bar length and charges each change of length.
Local changes (4/4 -> 5/4) are therefore representable without a song rule.
"""
import numpy as np

POLICY = 'downbeat-activation-dp-v1'
LENGTHS = (2, 3, 4, 5, 6, 7)


def segment_bars(activation, prior=None, change_penalty=1.0, eps=1e-3, max_lead=8):
    """Return beat indices that start bars, using per-beat downbeat activation."""
    a = np.clip(np.asarray(activation, dtype=float), 0, 1)
    n = len(a)
    if n < 2:
        return [0] if n else []
    prior = prior or default_prior(a)
    logit = np.log(a + eps) - np.log(1 - a + eps)
    lengths = sorted(prior)
    best, back = {}, {}
    for i in range(min(max_lead, n)):
        for length in lengths:
            best[(i, length)] = logit[i] - .5 * i + prior[length]
            back[(i, length)] = None
    for i in range(n):
        for previous in lengths:
            score = best.get((i, previous))
            if score is None:
                continue
            for length in lengths:
                j = i + previous
                if j >= n:
                    continue
                value = score + logit[j] + prior[length] - (change_penalty if length != previous else 0)
                if value > best.get((j, length), -np.inf):
                    best[(j, length)], back[(j, length)] = value, (i, previous)
    # The final bar must contain the last tracked beat; it may stay incomplete.
    end = max((k for k in best if k[0] + k[1] >= n), key=best.get)
    path, key = [], end
    while key is not None:
        path.append(key[0])
        key = back[key]
    return sorted(path)


def dominant_length(activation, threshold=.5):
    """Most frequent beat count between confident downbeat peaks (4 when undecided)."""
    peaks = np.flatnonzero(np.asarray(activation) > threshold)
    gaps = [g for g in np.diff(peaks) if g in LENGTHS]
    if len(gaps) < 4:
        return 4
    counts = {length: gaps.count(length) for length in LENGTHS}
    return max(counts, key=lambda length: (counts[length], length == 4))


def default_prior(activation):
    """Prefer the piece's dominant bar length; other lengths cost more with distance."""
    dominant = dominant_length(activation)
    return {length: 0. if length == dominant else -(2. + .5 * abs(length - dominant)) for length in LENGTHS}


def beat_activation(beats, frames, fps=50, radius=2):
    """Maximum frame activation within ±radius frames of each beat."""
    frames = np.asarray(frames, dtype=float)
    index = np.rint(np.asarray(beats, dtype=float) * fps).astype(int)
    return [float(frames[max(0, i - radius):min(len(frames), i + radius + 1)].max()) if 0 <= i < len(frames) else 0.
            for i in index]


def bar_lengths(starts, beat_count):
    """Beat counts of consecutive bars; a short final remainder keeps the previous length."""
    if not starts:
        return []
    lengths = list(np.diff(starts).astype(int))
    tail = beat_count - starts[-1]
    lengths.append(int(tail if tail in LENGTHS or not lengths else lengths[-1]))
    return lengths


def drum_downbeat_evidence(beats, events, crash=1.5, kick=1.0, snare=1.0):
    """Generic kit cues added to the downbeat log-odds of each beat.

    Crash cymbals and kicks often mark a bar start; a snare without kick on
    the beat suggests a backbeat. These are weak, style-dependent cues: they
    only shift the model evidence, they never place a bar line alone.
    """
    times = {c: np.asarray([e['time'] for e in events if e['class'] == c]) for c in ('kick', 'snare', 'cymbals')}
    def near(c, t, tolerance):
        return bool(len(times[c]) and np.min(abs(times[c] - t)) <= tolerance)
    return np.asarray([crash * near('cymbals', t, .06) + kick * near('kick', t, .05)
                       - snare * (near('snare', t, .05) and not near('kick', t, .05)) for t in beats])


def apply_variable_bars(grid, change_penalty=1.0, events=None):
    """Add bar starts/lengths to a simple-meter grid; compound grids are unchanged."""
    result = dict(grid)
    activation = grid.get('beat_downbeat_activation')
    beats = grid.get('beat_times_seconds', [])
    if activation is None or len(activation) != len(beats) or len(beats) < 4:
        result['bar_evidence'] = {'policy': POLICY, 'status': 'abstained', 'reason': 'no per-beat downbeat activation'}
        return result
    if float(grid.get('pulse_quarter_length', 1.)) != 1. or grid.get('time_signature', '4/4').split('/')[1] != '4':
        result['bar_evidence'] = {'policy': POLICY, 'status': 'abstained', 'reason': 'compound pulse: global meter kept'}
        return result
    prior = default_prior(activation)
    evidence = np.asarray(activation, dtype=float)
    if events:
        logit = np.log(evidence + 1e-3) - np.log(1 - evidence + 1e-3) + drum_downbeat_evidence(beats, events)
        evidence = 1 / (1 + np.exp(-logit))
    starts = segment_bars(evidence, prior=prior, change_penalty=change_penalty)
    lengths = bar_lengths(starts, len(beats))
    counts = {n: lengths.count(n) for n in sorted(set(lengths))}
    dominant = max(counts, key=counts.get)
    result.update(bar_start_beat_indices=[int(i) for i in starts], bar_beats=[int(n) for n in lengths],
                  origin_seconds=float(beats[starts[0]]), time_signature=f'{dominant}/4',
                  variable_meter=len(counts) > 1)
    result['bar_evidence'] = {'policy': POLICY, 'status': 'inferred_hypothesis', 'bar_length_counts': {str(k): v for k, v in counts.items()},
                              'change_penalty': change_penalty, 'prior': {str(k): v for k, v in prior.items()},
                              'drum_cues': bool(events),
                              'confidence_status': 'uncalibrated_model_activation_not_accuracy'}
    return result
