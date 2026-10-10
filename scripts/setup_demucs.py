"""Download only the pinned public model; no audio leaves this machine."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'configs/demucs-model.json').read_text())
target=ROOT/'work/models/demucs'/config['checkpoint'];target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():
 temporary=target.with_suffix('.download')
 urllib.request.urlretrieve(config['url'],temporary)
 if hashlib.sha256(temporary.read_bytes()).hexdigest()!=config['sha256']:
  temporary.unlink();raise ValueError('Poids non conformes')
 temporary.replace(target)
if hashlib.sha256(target.read_bytes()).hexdigest()!=config['sha256']: raise ValueError('Poids non conformes')
print('Poids Demucs vérifiés localement')
