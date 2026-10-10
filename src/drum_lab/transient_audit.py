"""Audio-only transient evidence. Scores are uncalibrated, never instrument proof."""
import numpy as np
from scipy.signal import stft


def band_flux(samples, sample_rate, *, low_hz=5000., high_hz=16000.):
    """Return spectral positive flux at ~5 ms steps from a local waveform."""
    samples = np.asarray(samples)
    scale = max(abs(np.iinfo(samples.dtype).min), np.iinfo(samples.dtype).max) if np.issubdtype(samples.dtype, np.integer) else 1
    samples = samples.astype(float) / scale
    if not np.isfinite(sample_rate) or sample_rate <= 0 or (samples.ndim == 2 and samples.shape[1] == 0):
        raise ValueError('Audio invalide')
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if samples.ndim != 1 or sample_rate <= 0 or not np.isfinite(samples).all():
        raise ValueError('Audio invalide')
    if len(samples) < 1024 or sample_rate / 2 <= low_hz:
        return np.array([]), np.array([])
    hop = min(1023, max(1, round(sample_rate * .005)))
    frequencies, times, spectrum = stft(samples, sample_rate, nperseg=1024,
                                      noverlap=1024-hop, boundary='zeros')
    band = np.abs(spectrum[(frequencies >= low_hz) & (frequencies <= high_hz)])
    flux = np.maximum(np.diff(band, axis=1, prepend=band[:, :1]), 0).sum(axis=0)
    return times, flux


def transient_evidence(times, flux, onset, *, tolerance=.025, context=.5):
    """Contrast the strongest nearby transient against its local background."""
    times, flux = np.asarray(times), np.asarray(flux)
    if times.ndim != 1 or times.shape != flux.shape or not np.isfinite(times).all() or not np.isfinite(flux).all() or not np.isfinite(onset):
        raise ValueError('Flux invalide')
    local = np.abs(times-onset) <= tolerance
    background = (np.abs(times-onset) <= context) & ~local
    if not local.any() or background.sum() < 10:
        return {'supported': False, 'reason': 'insufficient_audio'}
    nearby = np.flatnonzero(local)
    index = int(nearby[np.argmax(flux[local])])
    value = float(flux[index]); bg = flux[background]
    median = float(np.median(bg)); mad = float(np.median(np.abs(bg-median)))
    scale = max(mad*1.4826, float(np.max(bg))*1e-6, 1e-12)
    contrast = (value-median)/scale
    percentile = float(np.mean(bg < value))
    supported = bool(value > 1e-10 and contrast >= 3 and percentile >= .9)
    return {'supported': supported, 'reason': 'transient' if supported else 'weak_transient',
            'contrast': contrast, 'percentile': percentile,
            'peak_time': float(times[index]), 'offset_ms': 1000*(float(times[index])-onset)}


def audit_candidates(baseline, candidates, times, flux, *, cymbal_guard=.07):
    """Retain existing hits; propose only extra hats with a distinct transient.

    A coincident detected cymbal makes the instrument identity ambiguous, so
    the candidate is withheld. No expected pattern or musical grid is consulted.
    """
    existing = {(e['pitch'], e['time']) for e in baseline}
    cymbals = [e['time'] for e in baseline if e['class'] == 'cymbals']
    used_peaks = set()
    for event in baseline:
        if event['class'] == 'hi-hat':
            evidence = transient_evidence(times, flux, event['time'])
            if evidence['supported']:
                used_peaks.add(evidence['peak_time'])
    rows = []
    for event in sorted(candidates, key=lambda e: e['time']):
        if event['class'] != 'hi-hat' or (event['pitch'], event['time']) in existing:
            continue
        existing.add((event['pitch'], event['time']))
        evidence = transient_evidence(times, flux, event['time'])
        ambiguous = any(abs(t-event['time']) <= cymbal_guard for t in cymbals)
        reused = evidence.get('peak_time') in used_peaks
        accepted = evidence['supported'] and not ambiguous and not reused
        if accepted:
            used_peaks.add(evidence['peak_time'])
        rows.append({'event': event, **evidence, 'cymbal_ambiguous': ambiguous,
                     'transient_already_used': reused, 'accepted': accepted})
    return rows


def apply_hat_candidates(audio, out, piece_id, thresholds, prediction, *, synthetic=False):
    """Experimental opt-in: keep baseline and add audio-supported hat candidates."""
    import warnings
    import shutil
    from scipy.io import wavfile
    import pretty_midi
    from . import adapters
    from .files import write, digest
    for name in ('raw.mid', 'events.json'):
        target = out/('detector-'+name)
        if target.exists():
            raise ValueError('Original détecteur déjà présent : utiliser un nouveau run')
    for name in ('raw.mid', 'events.json'):
        shutil.copy2(out/name, out/('detector-'+name))
    lowered = list(thresholds)
    if lowered[3] <= .16:
        raise ValueError('Le seuil initial hats doit dépasser 0.16')
    lowered[3] = .16
    candidate = adapters.adtof(audio, out/'hat-candidates', piece_id, lowered, synthetic)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', wavfile.WavFileWarning)
        rate, samples = wavfile.read(audio)
    times, flux = band_flux(samples, rate)
    rows = audit_candidates(prediction['events'], candidate['events'], times, flux)
    additions = [row['event'] for row in rows if row['accepted']]
    write(out/'transient-audit.json', {'status': 'experimental_candidates',
          'musical_fidelity': None, 'policy': 'additions_only_abstain_cymbal_overlap',
          'audio_sha256': digest(audio), 'detector_events_sha256': digest(out/'detector-events.json'),
          'detector_midi_sha256': digest(out/'detector-raw.mid'), 'source_sha256': digest(__file__), 'parameters': {'candidate_hat_threshold': .16,
          'band_hz': [5000, 16000], 'tolerance_seconds': .025, 'context_seconds': .5,
          'min_contrast': 3, 'min_percentile': .9, 'cymbal_guard_seconds': .07},
          'added_count': len(additions), 'candidates': rows})
    # Preserve the original raw timing and MIDI metadata, including velocities.
    midi = pretty_midi.PrettyMIDI(str(out/'raw.mid'))
    drums = next((part for part in midi.instruments if part.is_drum), None)
    if additions and drums is None:
        drums = pretty_midi.Instrument(0, is_drum=True); midi.instruments.append(drums)
    for event in additions:
        drums.notes.append(pretty_midi.Note(100, event['pitch'], event['time'], event['time']+.05))
    if additions:
        midi.write(str(out/'raw.mid'))
    prediction = {**prediction, 'events': sorted(prediction['events']+additions, key=lambda e:e['time'])}
    write(out/'events.json', prediction)
    return prediction
