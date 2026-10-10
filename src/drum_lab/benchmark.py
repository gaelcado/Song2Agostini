"""Bounded audio-only corpus run; references belong to a separate verifier."""
import datetime
import subprocess
import sys
from pathlib import Path
from .files import ROOT, load, write, digest
from .pieces import BENCHMARK_IDS,PERCUSSION_IDS,registered_audio
from .runner import run


def benchmark(configs,only=None,percussion=False):
    if not isinstance(configs,list) or len(configs)!=1:
        raise ValueError('Le corpus reçoit un seul profil figé par exécution')
    allowed=PERCUSSION_IDS if percussion else BENCHMARK_IDS
    ids=list(only) if only else list(allowed)
    if not ids or len(ids)>10 or len(set(ids))!=len(ids) or any(i not in allowed for i in ids):
        raise ValueError('Sélection de cas invalide')
    name='benchmark-percussion-research-manifest.json' if percussion else 'benchmark-research-manifest.json'
    path=ROOT/'data'/name
    manifest=load(path)
    cases={p['id']:p for p in manifest['pieces']}
    # Validate the complete requested batch before spending any inference budget.
    for piece in ids:
        if piece not in cases:raise ValueError('Cas audio manquant')
        registered_audio(piece,ROOT/cases[piece]['audio'],ROOT)
    existing=[load(p) for p in (ROOT/'work/runs').glob('*/record.json')]
    for piece in ids:
        used=sum(r.get('piece_id')==piece and not r.get('synthetic',False) for r in existing)
        if used>=13:
            raise ValueError('Budget total atteint : baseline et 12 variantes de développement')
    profile=configs[0]
    if not isinstance(profile,dict) or not isinstance(profile.get('hypothesis'),str) or not profile['hypothesis'].strip():
        raise ValueError('Hypothèse nécessaire')
    report={'schema_version':1,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'corpus':'percussion_supplement' if percussion else 'multi_instrument_regression',
            'input_manifest_sha256':digest(path),'profile':configs[0],'reference_used':False,
            'cases':[],'best_method':None,'musical_fidelity':None}
    destination=ROOT/'work'/('benchmark-percussion-results.json' if percussion else 'benchmark-results.json')
    for piece in ids:
        record=run(ROOT/cases[piece]['audio'],configs,piece)[0]
        item={'piece_id':piece,'run_id':record['id'],'status':record['status'],
              'duration_seconds':record['duration_seconds']}
        if record['status']!='failed':
            # Artifact checks only: never pass a reference or private manifest here.
            directory=ROOT/'work/runs'/record['id']
            with (directory/'final-verification-worker.log').open('w') as log:
                subprocess.run([sys.executable,'-m','drum_lab.verify_worker',str(directory)],
                               cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
            checked=load(directory/'final-feedback.json')
            item.update(integrity=checked['integrity'],visual_review=checked['visual_review'],
                        prediction_stats=checked.get('prediction_stats'),musical_fidelity=None)
        report['cases'].append(item);write(destination,report)
    return report
