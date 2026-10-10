"""Bounded real CPU forwards on artificial audio; no fidelity claim/reference."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-root', required=True, type=Path)
    parser.add_argument('--audio', required=True, type=Path)
    parser.add_argument('--out', type=Path, default=Path('work/model-smoke'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    runtime, audio, out = args.runtime_root.resolve(), args.audio.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DRUM_LAB_RUNTIME_ROOT=str(runtime), DRUM_LAB_RESOURCE_ROOT=str(root))
    report = {'synthetic': True, 'benchmark': False, 'fidelity': None, 'engines': {}}
    def run(engine, arguments):
        py = runtime / 'envs' / engine / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        started = time.monotonic()
        with (out / f'{engine}.log').open('w', encoding='utf-8') as log:
            subprocess.run([str(py), *arguments], env=env, check=True, stdout=log,
                           stderr=subprocess.STDOUT, timeout=600)
        report['engines'][engine] = {'forward': 'passed', 'duration_seconds': time.monotonic() - started}
    adtof = out / 'adtof'
    adtof.mkdir(exist_ok=True)
    run('adtof', [str(root / 'scripts/adtof_worker.py'), str(audio), str(adtof / 'activations.npy'),
                  str(adtof), 'synthetic', 'null', 'True'])
    # Test model tensors even when no beat/downbeat is detectable on a fixture.
    # Do not invent a musical grid or require synthetic pulses to be recognized.
    beat_code = '''import sys, torch
from beat_this.inference import Audio2Frames
from beat_this.preprocessing import load_audio
signal,sr=load_audio(sys.argv[1])
torch.set_num_threads(4)
model=Audio2Frames(checkpoint_path=sys.argv[2],device="cpu",float16=False)
beat,downbeat=model(signal,sr)
assert beat.numel()>0 and downbeat.numel()>0
assert torch.isfinite(beat).all() and torch.isfinite(downbeat).all()
print("finite logits", beat.shape, downbeat.shape)
'''
    run('beat_this', ['-c', beat_code, str(audio), str(runtime / 'models/beat_this/final0.ckpt')])
    if shutil.which('ffmpeg') or os.environ.get('DRUM_LAB_FFMPEG'):
        run('demucs', [str(root / 'scripts/demucs_worker.py'), str(audio), str(out / 'demucs'),
                       str(runtime / 'models/demucs/955717e8-8726e21a.th')])
    else:
        report['engines']['demucs'] = {'forward': 'N/A', 'reason': 'ffmpeg absent; import checked by bootstrap'}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
