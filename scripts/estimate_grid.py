"""Audio-only grid; tracked beats trimmed to audible activity, phase provisional."""
import hashlib,json,sys,os
from pathlib import Path
import numpy as np


def estimate(audio, out):
    import librosa
    audio,out=Path(audio),Path(out)
    y,sr=librosa.load(audio,sr=22050)
    envelope=librosa.onset.onset_strength(y=y,sr=sr)
    bpm,frames=librosa.beat.beat_track(onset_envelope=envelope,sr=sr,trim=True)
    bpm=float(np.asarray(bpm).item())
    if not np.isfinite(bpm) or bpm<=0 or len(frames)<2: raise ValueError('Tempo audio non estimable')
    times=librosa.frames_to_time(frames,sr=sr)
    # Reject fabricated beats in padding/silence; envelope and RMS both audio-only.
    rms=librosa.feature.rms(y=y)[0]
    active=np.flatnonzero(rms>max(float(np.max(rms))*.02,1e-6))
    if len(active):
        active_start=float(librosa.frames_to_time(active[0],sr=sr)); active_end=float(librosa.frames_to_time(active[-1],sr=sr))
        times=times[(times>=active_start)&(times<=active_end)]
        audible=[]
        for t in times:
            frame=int(librosa.time_to_frames(t,sr=sr))
            window=rms[max(0,frame-7):min(len(rms),frame+8)]
            if len(window) and float(np.max(window))>max(float(np.max(rms))*.02,1e-6): audible.append(t)
        times=np.asarray(audible)
    else: raise ValueError('Audio silencieux')
    if len(times)<2: raise ValueError('Beats audibles insuffisants')
    tracked_bpm=60/float(np.median(np.diff(times)))
    factor=1
    while tracked_bpm/factor>160: factor*=2
    quarter_times=times[::factor].tolist()
    if len(quarter_times)<2: raise ValueError('Grille trop courte')
    grid={'source':'librosa beat tracker, trimmed audio only','audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),
          'librosa_version':librosa.__version__,'bpm':tracked_bpm/factor,'origin_seconds':quarter_times[0],
          'origin_policy':'first audible tracked quarter beat; proposed downbeat, not inferred bar phase',
          'raw_tempo_estimate_bpm':bpm,'tempo_octave_factor':factor,
          'tempo_octave_policy':'halve tracked tempo while >160 BPM, pedagogical assumption',
          'beat_times_seconds':quarter_times,'active_audio_interval_seconds':[active_start,active_end],
          'time_signature':'4/4','time_signature_status':'assumed_not_verified','downbeat_status':'hypothesis_first_tracked_beat',
          'subdivision':4,'duration_seconds':len(y)/sr,'silence_policy':'no tracked beats outside local audible RMS support; gaps retain missing beat coordinates; edge extrapolation explicit'}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(grid,indent=2)+'\n')
    return grid

def beat_this_grid(audio, out):
    """Experimental CPU downbeats, local pinned checkpoint, audio only."""
    import importlib.metadata
    import time
    import torch
    from beat_this.inference import Audio2Frames
    from beat_this.model.postprocessor import Postprocessor
    from beat_this.preprocessing import load_audio
    root=Path(os.environ.get('DRUM_LAB_RESOURCE_ROOT', Path(__file__).resolve().parents[1]))
    info=json.loads((root/'configs/beat-this-model.json').read_text())
    weights=Path(os.environ.get('DRUM_LAB_RUNTIME_ROOT', root/'work'))/Path(info['checkpoint']).relative_to('work')
    if hashlib.sha256(weights.read_bytes()).hexdigest()!=info['sha256']:
        raise ValueError('Poids Beat This non conformes')
    started=time.monotonic(); audio,out=Path(audio),Path(out)
    signal,sr=load_audio(audio)
    torch.set_num_threads(4)
    model=Audio2Frames(checkpoint_path=str(weights),device='cpu',float16=False)
    beat_logits,downbeat_logits=model(signal,sr)
    beats,downbeats=Postprocessor(type='minimal')(beat_logits,downbeat_logits)
    beats=np.asarray(beats,dtype=float); downbeats=np.asarray(downbeats,dtype=float)
    if len(beats)<2 or not len(downbeats): raise ValueError('Premiers temps audio non estimables')
    indices=np.asarray([int(np.argmin(abs(beats-t))) for t in downbeats])
    bar_gaps=np.diff(indices)
    fit=float(np.mean(bar_gaps==4)) if len(bar_gaps) else None
    probs=torch.sigmoid(downbeat_logits).cpu().numpy()
    frames=np.minimum(np.rint(downbeats*50).astype(int),len(probs)-1)
    grid={'source':'Beat This! final0 CPU, audio only','audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),
          'bpm':60/float(np.median(np.diff(beats))),'origin_seconds':float(downbeats[0]),
          'origin_policy':'first model-predicted downbeat; independent of drum pitch',
          'beat_times_seconds':beats.tolist(),'downbeat_times_seconds':downbeats.tolist(),
          'time_signature':'4/4','time_signature_status':'assumed_export_limit',
          'downbeat_status':'model_prediction_unverified','subdivision':4,'duration_seconds':len(signal)/sr,
          'phase_evidence':{'four_beat_bar_fraction':fit,'bar_intervals_observed':len(bar_gaps),
                            'median_downbeat_activation':float(np.median(probs[frames])),
                            'confidence_status':'uncalibrated_model_activation_not_accuracy'},
          'checkpoint_sha256':info['sha256'],'code_commit':info['code_commit'],
          'beat_this_version':importlib.metadata.version('beat-this'),
          'inference_seconds':time.monotonic()-started,'status':'draft',
          'silence_policy':'model tracked beats; local edge extrapolation explicit'}
    sys.path.insert(0,str(root/'src'))
    from drum_lab.grid import clean_model_grid
    grid=clean_model_grid(grid)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(grid,indent=2)+'\n')
    return grid


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('audio');parser.add_argument('out')
    parser.add_argument('--engine',choices=['librosa','beat_this'],default='librosa')
    args=parser.parse_args()
    (beat_this_grid if args.engine=='beat_this' else estimate)(args.audio,args.out)
