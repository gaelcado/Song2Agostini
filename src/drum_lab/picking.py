"""Optional absolute-height peak picking on cached ADTOF activations.

ADTOF's picker keeps a frame only if it exceeds the mean of the previous
100 ms plus the threshold. Under a sustained (half-open) hi-hat or dense
snare playing that mean stays high, so regular strokes are rejected. This
variant keeps local maxima above the same absolute threshold (minimum 30 ms
apart) for the chosen classes; other classes keep ADTOF's result.
"""
import json
from pathlib import Path

import numpy as np
import pretty_midi
from scipy.signal import find_peaks

CHANNELS = {'kick': (0, 35), 'snare': (1, 38), 'toms': (2, 47), 'hi-hat': (3, 42), 'cymbals': (4, 49)}
FPS = 100


def absolute_peaks(curve, threshold, distance_frames=3):
    peaks, _ = find_peaks(np.asarray(curve, dtype=float), height=threshold, distance=distance_frames)
    return [p / FPS for p in peaks]


def repick(out, activations_path, thresholds, classes):
    """Rewrite events.json/raw.mid in out, replacing the listed classes."""
    out = Path(out)
    classes = [c for c in classes if c in CHANNELS]
    if not classes:
        return json.loads((out / 'events.json').read_text())
    activations = np.load(activations_path, allow_pickle=False)
    activations = activations[0] if activations.ndim == 3 else activations
    document = json.loads((out / 'events.json').read_text())
    (out / 'detector-events.json').write_text(json.dumps(document, indent=2))
    events = [e for e in document['events'] if e['class'] not in classes]
    for cls in classes:
        channel, pitch = CHANNELS[cls]
        events += [{'time': t, 'class': cls, 'pitch': pitch} for t in absolute_peaks(activations[:, channel], thresholds[channel])]
    document['events'] = sorted(events, key=lambda e: (e['time'], e['pitch']))
    document['peak_picking'] = {'absolute_classes': classes, 'policy': 'local maxima >= threshold, 30 ms apart; others ADTOF'}
    (out / 'events.json').write_text(json.dumps(document, indent=2))
    midi = pretty_midi.PrettyMIDI()
    kit = pretty_midi.Instrument(program=1, is_drum=True)
    for e in document['events']:
        kit.notes.append(pretty_midi.Note(velocity=100, pitch=e['pitch'], start=e['time'], end=e['time'] + .1))
    midi.instruments.append(kit)
    midi.write(str(out / 'raw.mid'))
    return document
