#!/usr/bin/env python3
"""Register an already frozen motor PDF in the private comparison view."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('piece',choices=['piece_01']+[f'bench_{i:02d}' for i in range(1,11)]);p.add_argument('pdf');a=p.parse_args()
source=Path(a.pdf).resolve()
if not source.is_file() or source.suffix.lower()!='.pdf':raise ValueError('Frozen PDF required')
folder=ROOT/'work/verification/ui';folder=folder if a.piece=='piece_01' else folder/a.piece
if not (folder/'assets.json').is_file():raise ValueError('Prepare private source view first')
shutil.copyfile(source,folder/'motor.pdf');subprocess.run(['pdftoppm','-f','1','-l','1','-scale-to','2000','-png','-singlefile',str(folder/'motor.pdf'),str(folder/'motor-preview')],check=True,capture_output=True)
files={key:{'path':name,'mime':mime,'sha256':hashlib.sha256((folder/name).read_bytes()).hexdigest()} for key,name,mime in [('motor-pdf','motor.pdf','application/pdf'),('motor-preview','motor-preview.png','image/png')]}
(folder/'motor-artifacts.json').write_text(json.dumps({'piece_id':a.piece,'files':files,'label':'Sortie moteur figée · brouillon automatique, comparaison visuelle seulement'},ensure_ascii=False,indent=2))
print('Frozen motor PDF registered privately:',a.piece)
