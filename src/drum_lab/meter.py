"""Bounded audio-only meter evidence, deliberately without song identity rules."""
import copy
import subprocess
import numpy as np
from scipy.signal import stft, find_peaks
from .files import find_tool

POLICY = 'audio-downbeat-subdivision-v3'


def audio_onsets(audio):
    """Spectral-flux peaks on the complete local mix, independent of drum labels."""
    decoded = subprocess.run([find_tool('ffmpeg') or 'ffmpeg', '-v', 'error', '-i', str(audio),
                              '-f', 'f32le', '-ac', '1', '-ar', '22050', '-'],
                             capture_output=True, check=True, timeout=120)
    signal = np.frombuffer(decoded.stdout, dtype='<f4')
    _, times, spectrum = stft(signal, fs=22050, nperseg=1024, noverlap=804)
    magnitude = np.log1p(10 * abs(spectrum))
    flux = np.maximum(0, np.diff(magnitude, axis=1)).mean(axis=0)
    peaks, _ = find_peaks(flux, prominence=max(float(np.median(flux)), 1e-6), distance=5)
    return times[1:][peaks], flux[peaks]


def infer_meter(grid, onset_times, onset_weights=None):
    result = copy.deepcopy(grid)
    # Never inherit a prior meter decision when reprocessing frozen model peaks.
    result.update(time_signature='4/4', subdivision=4, pulse_quarter_length=1.)
    result.pop('meter_evidence', None)
    beats = np.asarray(grid.get('beat_times_seconds', []), dtype=float)
    if len(beats) > 1:
        result['bpm'] = 60 / float(np.median(np.diff(beats)))
    downbeats = np.asarray(grid.get('downbeat_times_seconds', []), dtype=float)
    if len(beats) < 8 or len(downbeats) < 3:
        result['meter_evidence'] = {'policy': POLICY, 'status': 'abstained', 'reason': 'insufficient tracked pulses/downbeats'}
        result['time_signature_status'] = 'fallback_assumption_not_verified'
        return result
    indices = np.unique([np.argmin(abs(beats - t)) for t in downbeats])
    gaps = np.diff(indices)
    fractions = {n: float(np.mean(gaps == n)) for n in (2, 3, 4, 6)}
    cycle = max(fractions, key=fractions.get)
    # Missing downbeats can double a cycle; retain their count, never manufacture them.
    fit = float(np.mean((gaps == cycle) | (gaps == 2 * cycle)))
    times = np.asarray(onset_times)
    weights = np.ones(len(times)) if onset_weights is None else np.asarray(onset_weights)
    inside = (times >= beats[0]) & (times < beats[-1])
    times, weights = times[inside], weights[inside]
    left = np.searchsorted(beats, times, side='right') - 1
    phases = (times - beats[left]) / (beats[left + 1] - beats[left])
    off = (phases > .18) & (phases < .82)
    # Only offbeat evidence discriminates: downbeat-heavy mixes fit both grids.
    binary = abs(phases - .5) < .09
    ternary = np.minimum(abs(phases - 1/3), abs(phases - 2/3)) < .09
    mass = float(weights[off].sum())
    binary_fit = float(weights[binary & off].sum() / mass) if mass else 0.
    ternary_fit = float(weights[ternary & off].sum() / mass) if mass else 0.
    subdivision = 'ternary' if ternary_fit > binary_fit + .15 else 'binary' if binary_fit > ternary_fit + .15 else 'ambiguous'
    windows = []
    for start in range(0, len(gaps), 16):
        block = gaps[start:start+16]
        windows.append({'start_seconds': float(beats[indices[start]]),
                        'end_seconds': float(beats[indices[min(start+16, len(indices)-1)]]),
                        'cycle_counts': {str(n): int(np.sum(block == n)) for n in np.unique(block)}})
    stable = fractions[cycle] >= .65 and fit >= .85
    evidence = {'policy': POLICY, 'status': 'inferred_hypothesis' if stable and subdivision != 'ambiguous' else 'abstained',
                'pulse_cycle': int(cycle), 'cycle_fractions': {str(k):v for k,v in fractions.items()},
                'cycle_or_double_fraction': fit, 'subdivision': subdivision,
                'binary_offbeat_weight_fraction': binary_fit, 'ternary_offbeat_weight_fraction': ternary_fit,
                'offbeat_peak_count': int(off.sum()), 'local_cycle_windows': windows,
                'confidence_status': 'uncalibrated_descriptive_evidence_not_accuracy',
                'tempo_octave_status': 'tracked pulse scale; half/double alternatives unresolved',
                'local_meter_changes_status': 'diagnosed_cycle_variation_not_exported',
                'reason': None if stable and subdivision != 'ambiguous' else 'heterogeneous downbeats or indistinguishable subdivisions'}
    # Stable 3-pulse cycles are useful even with unresolved subdivisions: simple
    # 3/4 versus 6/8 at another pulse scale remains an explicit notation ambiguity.
    provisional_compound = (not stable and subdivision == 'ternary' and cycle in (2, 4) and fractions[cycle] >= .60)
    if stable or provisional_compound:
        compound = subdivision == 'ternary' and cycle in (2, 4)
        signature = f'{cycle*3}/8' if compound else f'{cycle}/4'
        if cycle == 6: signature = '6/4'
        result.update(time_signature=signature, subdivision=6 if compound else 4,
                      pulse_quarter_length=1.5 if compound else 1.,
                      bpm=float(result['bpm']) * (1.5 if compound else 1),
                      time_signature_status='audio_hypothesis_unverified')
        evidence['notation_alternatives'] = (['3/4', '6/8 at another pulse scale'] if cycle == 3
                                            else ['compound meter', 'simple meter with triplets'] if compound
                                            else ['simple meter', 'half/double tempo interpretation'])
        evidence['export_policy'] = ('dominant compound candidate; abstention on bar grouping and local changes'
                                     if provisional_compound else 'dominant global hypothesis; local deviations retained as warnings')
    else:
        result['time_signature_status'] = 'fallback_assumption_not_verified'
        evidence['export_policy'] = 'fallback 4/4 draft; no claim of detected signature'
    result['meter_evidence'] = evidence
    return result


def infer_audio_meter(audio, grid):
    times, weights = audio_onsets(audio)
    return infer_meter(grid, times, weights)
