"""Audio-only interfaces; no reference parameter or manifest access."""
import hashlib
import json
import subprocess
from pathlib import Path
from .files import ROOT, digest, load, write, resource_path, env_python, worker_path, worker_environment, installed_package_path, runtime_root

def adtof(audio, out, piece_id, thresholds=None, synthetic=False):
    audio=Path(audio).resolve(); out=Path(out); out.mkdir(parents=True,exist_ok=True)
    if not audio.is_file(): raise FileNotFoundError(f'Audio absent : {audio}')
    if thresholds is not None and (len(thresholds)!=5 or any(not 0<t<1 for t in thresholds)):
        raise ValueError('ADTOF attend cinq seuils entre 0 et 1')
    env=env_python('adtof')
    worker=worker_path('adtof_worker.py')
    lock=resource_path('configs/adtof.lock.txt')
    weights=installed_package_path('adtof', 'adtof_pytorch', weights=True)
    identity={'audio':digest(audio),'worker':digest(worker),'dependencies':digest(lock),'weights':digest(weights)}
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    cache=ROOT/'work/cache'/key; cache.mkdir(parents=True,exist_ok=True)
    cmd=[str(env),str(worker),str(audio),str(cache/'activations.npy'),str(out),piece_id,json.dumps(thresholds),str(synthetic)]
    with (out/'inference.log').open('w') as log:
        subprocess.run(cmd,env=worker_environment(),check=True,stdout=log,stderr=subprocess.STDOUT,timeout=3600)
    (out/'cache.json').write_text(json.dumps({'key':key,**identity},indent=2))
    return json.loads((out/'events.json').read_text())

def demucs(audio, out):
    audio=Path(audio).resolve();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    weights=runtime_root()/'models/demucs/955717e8-8726e21a.th'
    if not weights.is_file():
        raise RuntimeError('Poids Demucs absents ; lancer scripts/setup_demucs.py')
    identity={'audio':digest(audio),'weights':digest(weights),'worker':digest(worker_path('demucs_worker.py')),
              'dependencies':digest(resource_path('configs/demucs.lock.txt'))}
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    cache=ROOT/'work/cache/separation'/key
    if not (cache/'drums.wav').is_file():
        cache.mkdir(parents=True,exist_ok=True)
        cmd=[str(env_python('demucs')),str(worker_path('demucs_worker.py')),str(audio),str(cache),str(weights)]
        with (out/'separation.log').open('w') as log:
            subprocess.run(cmd,env=worker_environment(),check=True,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    import shutil
    shutil.copy2(cache/'drums.wav',out/'drums.wav')
    shutil.copy2(cache/'separation.json',out/'separation.json')
    write(out/'cache.json',{'key':key,**identity})
    return out/'drums.wav'

def allinone(audio, out):
    subprocess.run([str(env_python('allinone')),str(worker_path('allinone_worker.py')),str(audio),str(out)],env=worker_environment(),check=True,timeout=3600)

def drumscript(audio, out, piece_id, full_song=False, synthetic=False):
    """DSP baseline, retaining unquantized onset seconds; separation uses our pinned cache."""
    audio=Path(audio).resolve(); out=Path(out).resolve(); out.mkdir(parents=True,exist_ok=True)
    if not audio.is_file(): raise FileNotFoundError(f'Audio absent : {audio}')
    if full_song: audio=demucs(audio,out/'separation')
    worker=worker_path('drumscript_worker.py')
    package=installed_package_path('drumscript', 'drumscript')
    identity={'audio':digest(audio),'worker':digest(worker),'dependencies':digest(resource_path('configs/drumscript.lock.txt')),
              'package_sources':{str(p.relative_to(package)):digest(p) for p in sorted(package.rglob('*.py'))}}
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    cache=ROOT/'work/cache/drumscript'/key; cache.mkdir(parents=True,exist_ok=True)
    cmd=[str(env_python('drumscript')),str(worker),str(audio),str(cache),str(out),piece_id,str(synthetic)]
    with (out/'inference.log').open('w') as log:
        subprocess.run(cmd,env=worker_environment(),check=True,stdout=log,stderr=subprocess.STDOUT,timeout=3600)
    write(out/'cache.json',{'key':key,**identity})
    return load(out/'events.json')
