"""Local independent implementation of the published ONNX mask I/O contract."""
import os
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(os.environ.get('DRUM_LAB_RESOURCE_ROOT', Path(__file__).resolve().parents[1]))/'src'))
from drum_lab.processes import run_external
import numpy as np
from scipy.signal.windows import hann


def spectral_analysis(wave, n_fft=4096, hop=1024):
    if wave.ndim != 2 or wave.shape[1] != 2 or not len(wave) or not np.isfinite(wave).all():
        raise ValueError('Expected nonempty finite stereo waveform')
    padded = np.pad(wave, ((n_fft//2, n_fft//2 + hop), (0, 0)), mode='reflect')
    frames = np.lib.stride_tricks.sliding_window_view(padded, n_fft, axis=0)[::hop]
    window = hann(n_fft, sym=False).astype(np.float32)
    spectrum = np.fft.rfft(frames * window, axis=-1).transpose(1, 2, 0)
    return spectrum.astype(np.complex64)


def spectral_synthesis(spectrum, length, n_fft=4096, hop=1024):
    frames = np.fft.irfft(spectrum.transpose(2, 0, 1), n=n_fft, axis=-1)
    window = hann(n_fft, sym=False)
    size = (len(frames)-1)*hop+n_fft
    result = np.zeros((size, 2)); norm = np.zeros(size)
    for index, frame in enumerate(frames):
        start = index*hop
        result[start:start+n_fft] += (frame * window).T
        norm[start:start+n_fft] += window**2
    result /= np.maximum(norm[:, None], 1e-12)
    return result[n_fft//2:n_fft//2+length].astype(np.float32)


def chunk_magnitudes(magnitude, frames=512):
    for start in range(0, magnitude.shape[-1], frames):
        count = min(frames, magnitude.shape[-1]-start)
        chunk = np.zeros((1, *magnitude.shape[:2], frames), dtype=np.float32)
        chunk[0, :, :, :count] = magnitude[:, :, start:start+count]
        yield start, count, chunk


def main(audio, out, config_path):
    import onnxruntime as ort
    import soundfile as sf
    started = time.monotonic(); config = json.loads(config_path.read_text())
    out.mkdir(parents=True, exist_ok=True)
    raw = run_external([os.environ.get('DRUM_LAB_FFMPEG', 'ffmpeg'),'-v','error','-i',str(audio),'-f','f32le','-ar','44100','-ac','2','pipe:1'],check=True,capture_output=True).stdout
    wave = np.frombuffer(raw, dtype='<f4').reshape(-1,2).copy()
    spectrum = spectral_analysis(wave); magnitude = np.abs(spectrum[:, :2048])
    options = ort.SessionOptions(); options.intra_op_num_threads = 4
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    diagnostics = {}
    for instrument, info in config['models'].items():
        model_path = Path(os.environ.get('DRUM_LAB_RUNTIME_ROOT', config_path.parent.parent/'work'))/'models/kit'/info['filename']
        checksum = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if checksum != info['sha256']: raise ValueError('Model checksum mismatch')
        session = ort.InferenceSession(str(model_path), sess_options=options, providers=['CPUExecutionProvider'])
        if session.get_inputs()[0].shape != [1,2,2048,512]: raise ValueError('Unexpected ONNX contract')
        masks = np.empty(magnitude.shape, dtype=np.float32); outside = 0
        for start, count, chunk in chunk_magnitudes(magnitude):
            mask = session.run(['mask'], {'mag': chunk})[0]
            if mask.shape != chunk.shape or not np.isfinite(mask).all(): raise ValueError('Invalid mask')
            outside += int(np.count_nonzero((mask < 0) | (mask > 1)))
            masks[:,:,start:start+count] = np.clip(mask[0,:,:,:count],0,1)
        target = np.zeros_like(spectrum); target[:,:2048] = spectrum[:,:2048] * masks
        output = spectral_synthesis(target, len(wave))
        sf.write(out/f'{instrument}.wav', output, 44100, subtype='FLOAT')
        np.save(out/f'{instrument}-mask.npy', masks, allow_pickle=False)
        diagnostics[instrument] = {'weights_sha256':checksum,'mask_min':float(masks.min()),'mask_max':float(masks.max()),
          'mask_outside_unit_interval':outside,'peak':float(np.abs(output).max()),'samples_above_one':int((np.abs(output)>1).sum()),
          'rms':float(np.sqrt(np.mean(output**2))), 'output_sha256':hashlib.sha256((out/f'{instrument}.wav').read_bytes()).hexdigest()}
        print(instrument, diagnostics[instrument], flush=True)
    metadata = {'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'config':config,
      'duration_seconds':time.monotonic()-started,'audio_seconds':len(wave)/44100,'frames':spectrum.shape[-1],
      'onnxruntime_version':ort.__version__,'provider':'CPUExecutionProvider','threads':4,'diagnostics':diagnostics}
    (out/'complete.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata), flush=True)

if __name__ == '__main__': main(*map(Path, sys.argv[1:]))
