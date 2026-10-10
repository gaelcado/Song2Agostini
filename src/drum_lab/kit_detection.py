"""Experimental audio-only kit separation; no reference access."""
import hashlib
import json
import shutil
import subprocess
from .processes import run_external
from pathlib import Path
from .files import ROOT, digest, load, write, resource_path, env_python, worker_path, worker_environment, runtime_root, source_file, runtime_identity


def kit_identity(audio):
    config = load(resource_path('configs/kit-model.json'))
    weights = {}
    for instrument, info in config['models'].items():
        path = runtime_root()/'models/kit'/info['filename']
        actual = digest(path)
        if actual != info['sha256']:
            raise ValueError(f'Poids kit non conformes: {instrument}')
        weights[instrument] = actual
    return {'audio': digest(audio), 'worker': digest(worker_path('kit_worker.py')),
            'dependencies': digest(resource_path('configs/kit.lock.txt')),
            'config': digest(resource_path('configs/kit-model.json')), 'weights': weights,
            'adapter': digest(source_file(__file__)), 'runtime': runtime_identity('kit')}


def separate_kit(audio, out):
    """Input must be a drum-only stem, generated without a reference."""
    audio = Path(audio).resolve(); out = Path(out); out.mkdir(parents=True, exist_ok=True)
    identity = kit_identity(audio)
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    cache = ROOT/'work/cache/kit'/key
    if not (cache/'complete.json').is_file():
        cache.mkdir(parents=True, exist_ok=True)
        cmd = [str(env_python('kit')), str(worker_path('kit_worker.py')),
               str(audio), str(cache), str(resource_path('configs/kit-model.json'))]
        with (out/'kit-inference.log').open('w') as log:
            run_external(cmd, env=worker_environment(), check=True, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
    write(out/'kit-cache.json', {'key': key, **identity})
    shutil.copy2(cache/'complete.json', out/'kit-separation.json')
    return {name: cache/f'{name}.wav' for name in ('kick', 'snare')}


def adtof_kit(audio, out, piece_id, thresholds=None, synthetic=False):
    """Keep only kick/snare from isolated stems; other classes from original stem."""
    from .adapters import adtof
    import pretty_midi
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    stems = separate_kit(audio, out)
    original = adtof(audio, out/'original', piece_id, thresholds, synthetic)
    events = [e for e in original['events'] if e['class'] not in stems]
    counts = {}
    for instrument, stem in stems.items():
        detected = adtof(stem, out/instrument, piece_id, thresholds, synthetic)
        retained = [e for e in detected['events'] if e['class'] == instrument]
        events.extend(retained); counts[instrument] = len(retained)
    events.sort(key=lambda e: e['time'])
    result = dict(original, events=events)
    write(out/'events.json', result)
    midi = pretty_midi.PrettyMIDI()
    track = pretty_midi.Instrument(program=0, is_drum=True)
    for event in events:
        track.notes.append(pretty_midi.Note(velocity=100, pitch=event['pitch'], start=event['time'], end=event['time']+.05))
    midi.instruments.append(track); midi.write(str(out/'raw.mid'))
    write(out/'kit-composition.json', {'policy': 'kick/snare from respective stems; other classes from original drum stem',
          'counts': counts, 'experimental': True, 'reference_access': False})
    return result
