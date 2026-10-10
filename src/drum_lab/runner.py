import datetime
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from .files import ROOT, load, write, digest
from .pieces import registered_audio, BENCHMARK_IDS, PERCUSSION_IDS, USER_IDS

def run(audio, configs, piece, synthetic=False):
    if not 1<=len(configs)<=13: raise ValueError('Une baseline et au plus 12 variantes')
    registered_audio(piece,audio,ROOT)
    if piece=='piece_02' and len(configs)!=1: raise ValueError('Un seul contrôle après gel')
    if piece=='piece_02':
        freeze=ROOT/'configs/frozen.json'
        if not freeze.exists() or load(freeze)!=configs[0]: raise ValueError('Configuration de contrôle non gelée')
        if any(load(p).get('piece_id')=='piece_02' for p in (ROOT/'work/runs').glob('*/record.json')):
            raise ValueError('Contrôle déjà consulté : poursuivre uniquement en développement documenté')
    existing=[load(p) for p in (ROOT/'work/runs').glob('*/record.json')]
    if piece in ('piece_01',)+BENCHMARK_IDS+PERCUSSION_IDS+USER_IDS and not synthetic and sum(r.get('piece_id')==piece and not r.get('synthetic',False) for r in existing)+len(configs)>13:
        raise ValueError('Budget total atteint : baseline et 12 variantes de développement')
    records=[]
    for config in configs:
        if not isinstance(config.get('hypothesis'),str) or not config['hypothesis'].strip(): raise ValueError('Hypothèse nécessaire')
        rid=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
        out=ROOT/'work/runs'/rid; out.mkdir(parents=True)
        started=time.monotonic()
        record={'id':rid,'piece_id':piece,'synthetic':synthetic,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'audio_sha256':digest(audio),'config':config,
                'evaluation_sha256':digest(ROOT/'configs/evaluation.v2.json'),'command':['drum-lab','run',str(Path(audio).resolve()),'--piece',piece],'seed':None,
                'dependencies':(ROOT/'configs'/('drumscript.lock.txt' if config.get('engine')=='drumscript' else 'adtof.lock.txt')).read_text(),'status':'running',
                'git_commit':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip() or None,
                'git_status':subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True).stdout,
                'source_sha256':{str(p.relative_to(ROOT)):digest(p) for folder in ('src','scripts') for p in (ROOT/folder).rglob('*.py')}}
        write(out/'record.json',record); write(out/'config.json',config)
        try:
            from .pipeline import generate
            from .titles import audio_title
            result=generate(audio,out,config,piece,audio_title(audio),synthetic=synthetic)
            record['event_count']=result['event_count'];record['status']='awaiting_verification'
            record['notation_status']=result['notation_status'];record['artifacts']=result['artifacts']
        except Exception as e:
            record['status']='failed'; record['error']=str(e)
        record['duration_seconds']=time.monotonic()-started
        write(out/'record.json',record); records.append(record)
    # Each group is separated to avoid presenting synthetic or control as development.
    group=[load(p) for p in (ROOT/'work/runs').glob('*/record.json') if load(p).get('piece_id')==piece and load(p).get('synthetic')==synthetic]
    # Ranking uses only feedback published by the independent verifier.
    for item in group:
        item.pop('macro_f1_50ms',None)
        feedback=ROOT/'work/runs'/item['id']/'final-feedback.json'
        if feedback.exists():
            checked=load(feedback)
            if checked.get('integrity')=='passed' and checked.get('visual_review')=='accepted_as_readable_draft' and checked.get('musical_fidelity'):
                item['macro_f1_50ms']=checked['musical_fidelity']['tolerances']['50']['macro_f1']
    group.sort(key=lambda x:(x.get('macro_f1_50ms') is not None,x.get('macro_f1_50ms') or 0),reverse=True)
    write(ROOT/'work'/f'leaderboard-{piece}.json',group)
    return records
