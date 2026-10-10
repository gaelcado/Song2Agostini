#!/usr/bin/env python3
"""Sync frozen benchmark PDFs into private UI; failed runs have no fallback."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from drum_lab.human_review import motor_visual_label
report=json.loads((ROOT/'work/benchmark-results.json').read_text());count=0
for case in report['cases']:
 piece=case['piece_id']
 if piece not in {f'bench_{i:02d}' for i in range(1,11)}:raise ValueError('Unknown corpus piece')
 folder=ROOT/'work/verification/ui'/piece
 if case['status']=='failed':
  (folder/'motor-artifacts.json').write_text(json.dumps({'piece_id':piece,'state':'failed','run_id':case['run_id'],'files':{},'label':'Génération échouée : aucun PDF final disponible.'},ensure_ascii=False))
  for name in ['motor.pdf','motor-preview.png']:(folder/name).unlink(missing_ok=True)
  continue
 if case['status']!='awaiting_verification':continue
 run_id=case['run_id']
 if not run_id or not all(c.isalnum() or c=='-' for c in run_id):raise ValueError('Invalid run identifier')
 pdf=ROOT/'work/runs'/run_id/'notation/score.pdf'
 if not pdf.is_file():continue
 existing=folder/'motor-artifacts.json'
 pdf_hash=hashlib.sha256(pdf.read_bytes()).hexdigest()
 registry=json.loads(existing.read_text()) if existing.is_file() else {}
 unchanged=registry.get('files',{}).get('motor-pdf',{}).get('sha256')==pdf_hash
 if not unchanged:
  subprocess.run([sys.executable,str(ROOT/'lab/scripts/render_output_review.py'),piece,str(pdf)],check=True)
  count+=1
 registry=json.loads(existing.read_text());registry['run_id']=run_id
 feedback_file=pdf.parent.parent/'final-feedback.json'
 try:feedback=json.loads(feedback_file.read_text())
 except (OSError,ValueError):feedback={}
 registry['label']=motor_visual_label(feedback,piece,pdf_hash)
 existing.write_text(json.dumps(registry,ensure_ascii=False,indent=2))
print('New frozen PDFs registered:',count)
