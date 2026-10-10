"""Pinned official Demucs checkpoint, deterministic CPU, local audio only."""
import os
import hashlib,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0, str(Path(os.environ.get('DRUM_LAB_RESOURCE_ROOT', Path(__file__).resolve().parents[1]))/'src'))
from drum_lab.processes import run_external
import numpy as np
import soundfile as sf
import torch
from demucs.states import load_model
from demucs.apply import apply_model

audio,out,weights=map(Path,sys.argv[1:])
started=time.monotonic()
checksum=hashlib.sha256(weights.read_bytes()).hexdigest()
if not checksum.startswith('8726e21a'): raise ValueError('Poids officiels Demucs non conformes')
torch.manual_seed(0); torch.set_num_threads(4)
# Checkpoint pinned and verified before trusted class deserialization.
pkg=torch.load(weights,map_location='cpu',weights_only=False)
model=load_model(pkg).cpu().eval()
sr=model.samplerate
raw=run_external([os.environ.get('DRUM_LAB_FFMPEG', 'ffmpeg'),'-v','error','-i',str(audio),'-f','f32le','-ar',str(sr),'-ac','2','pipe:1'],check=True,capture_output=True).stdout
wav=torch.from_numpy(np.frombuffer(raw,dtype='<f4').copy().reshape(-1,2).T)
ref=wav.mean(0);mean=ref.mean();scale=ref.std()
if not torch.isfinite(scale) or scale<=1e-8: raise ValueError('Audio silencieux ou invalide')
with torch.no_grad():
 sources=apply_model(model,((wav-mean)/scale)[None],device='cpu',shifts=0,split=True,overlap=.25,progress=True,num_workers=0)[0]
 sources=sources*scale+mean
out.mkdir(parents=True,exist_ok=True)
drums=sources[model.sources.index('drums')].T.numpy()
peak=float(np.max(np.abs(drums)))
if peak>1: drums=drums/peak
sf.write(out/'drums.wav',drums,sr,subtype='FLOAT')
metadata={'model':'htdemucs','weights_sha256':checksum,'source_names':model.sources,'samplerate':sr,
          'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'seed':0,'shifts':0,'overlap':.25,'device':'cpu',
          'torch_version':torch.__version__,'duration_seconds':time.monotonic()-started,'peak_before_rescale':peak}
(out/'separation.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata))
