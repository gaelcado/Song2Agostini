"""Portable delivery smoke; generated fixture only, no musical reference/model."""
import argparse
import importlib
import http.client
import threading
import json
import platform
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pretty_midi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('work/platform-smoke'))
    parser.add_argument('--require-pdf', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ('drum_lab.cli', 'drum_lab.ui', 'drum_lab.pipeline', 'drum_lab.rendering'):
        importlib.import_module(name)
    subprocess.run([sys.executable, '-c', 'from drum_lab.cli import main; main()', '--help'], check=True)
    from drum_lab.ui import Application, LocalServer
    app = Application(out / 'http-state')
    server = LocalServer(('127.0.0.1', 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        client.request('GET', '/')
        response = client.getresponse()
        assert response.status == 200 and b'/app.js' in response.read()
        client.close()
    finally:
        server.shutdown()
        server.server_close()
        app.close()
        thread.join(5)
    duration, sample_rate = 8, 22050
    t = np.arange(duration * sample_rate) / sample_rate
    y = np.zeros_like(t)
    times = np.arange(.5, duration, .5)
    for onset in times:
        dt = t - onset
        y += np.where(dt >= 0, .25 * np.sin(2 * np.pi * 80 * dt) * np.exp(-np.maximum(dt, 0) * 35), 0)
    audio = out / 'synthetic.wav'
    with wave.open(str(audio), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes((y * 32767).astype('<i2').tobytes())
    report = {'synthetic': True, 'benchmark': False, 'inference_tested': False,
              'python': platform.python_version(), 'platform': platform.platform(),
              'machine': platform.machine(), 'audio_validation': 'N/A', 'pdf': 'N/A'}
    if shutil.which('ffprobe'):
        from drum_lab.ui import validate_audio
        validate_audio(audio)
        report['audio_validation'] = 'passed'
    midi = pretty_midi.PrettyMIDI(initial_tempo=120)
    kit = pretty_midi.Instrument(0, is_drum=True)
    for index, onset in enumerate(times):
        kit.notes.append(pretty_midi.Note(100, 36 if index % 2 == 0 else 38, float(onset), float(onset + .1)))
    midi.instruments.append(kit)
    raw = out / 'raw.mid'
    midi.write(str(raw))
    from drum_lab.engraving import engrave, renderer
    engine = renderer()
    # Without renderer, engrave still writes audited XML and quantized MIDI,
    # then raises its documented missing-renderer diagnostic.
    try:
        engrave(raw, {'bpm': 120, 'duration_seconds': duration}, out / 'notation', 'Fixture synthétique CI')
    except RuntimeError as error:
        if engine or 'MuseScore absent' not in str(error):
            raise
    for name in ('quantized.mid', 'score.musicxml'):
        assert (out / 'notation' / name).stat().st_size > 0, name
    assert len(pretty_midi.PrettyMIDI(str(out / 'notation/quantized.mid')).instruments[0].notes) == len(times)
    pdf = out / 'notation/score.pdf'
    if engine:
        assert pdf.read_bytes().startswith(b'%PDF'), 'Invalid PDF'
        report['pdf'] = 'passed'
    elif args.require_pdf:
        raise RuntimeError('This smoke requires MuseScore and a real PDF export')
    report['midi_musicxml'] = 'passed'
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
