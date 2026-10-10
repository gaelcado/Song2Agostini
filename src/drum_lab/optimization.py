"""Coordinator: research audio-only, separate verifier process, bounded feedback loop."""
import subprocess
import sys
from pathlib import Path
from .files import ROOT,load,write,digest
from .runner import run
from .pieces import registered_audio, BENCHMARK_IDS, PERCUSSION_IDS


def cycle(audio,configs,piece,reference=None,synthetic=False,resume_run=None):
    if not 1<=len(configs)<=13:raise ValueError('Une baseline et au plus 12 variantes')
    if piece=='piece_02' and len(configs)!=1:raise ValueError('Un seul contrôle après gel')
    registered_audio(piece,audio,ROOT)
    # Reverification does not consume an inference trial; further candidates do.
    if piece in ('piece_01',)+BENCHMARK_IDS+PERCUSSION_IDS and not synthetic:
        existing=[load(p) for p in (ROOT/'work/runs').glob('*/record.json')]
        used=sum(r.get('piece_id')==piece and not r.get('synthetic',False) for r in existing)
        if used+len(configs)-bool(resume_run)>13:
            raise ValueError('Budget total atteint : baseline et 12 variantes de développement')
    completed=[];best=None;best_score=None;reason='planned_variants_exhausted'
    for index,config in enumerate(configs):
        if index==0 and resume_run:
            directory=(ROOT/'work/runs'/resume_run).resolve()
            if directory.parent!=(ROOT/'work/runs').resolve():raise ValueError('Identifiant de reprise invalide')
            record=load(directory/'record.json')
            if (record['id']!=resume_run or record['piece_id']!=piece or record['synthetic']!=synthetic
                or record['config']!=config or record['audio_sha256']!=digest(audio)):
                raise ValueError('Le run à reprendre ne correspond pas à l’audio et aux paramètres')
            if record['status'] not in ('awaiting_verification','failed'):
                raise ValueError('Le run à reprendre n’est pas figé')
            if piece=='piece_02':
                freeze=ROOT/'configs/frozen.json'
                if not freeze.exists() or load(freeze)!=config:
                    raise ValueError('Configuration de contrôle non gelée')
        else:
            record=run(audio,[config],piece,synthetic)[0]
        if record['status']=='failed':
            completed.append({'id':record['id'],'decision':'rejected_pipeline_failure'})
            continue
        directory=ROOT/'work/runs'/record['id']
        cmd=[sys.executable,'-m','drum_lab.verify_worker',str(directory)]
        if reference:cmd.extend(['--reference',str(Path(reference).resolve())])
        private=ROOT/'work/verification'/record['id'];private.mkdir(parents=True,exist_ok=True)
        with (private/'worker.log').open('w') as log:
            subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=300,cwd=ROOT)
        feedback=load(directory/'final-feedback.json')
        metrics=feedback.get('musical_fidelity')
        score=metrics['tolerances']['50']['macro_f1'] if metrics else None
        decision='requires_reference_validation'
        if feedback['integrity']!='passed':
            decision='rejected_integrity';score=None
        elif score is not None:
            if feedback.get('visual_review')!='accepted_as_readable_draft':
                decision='requires_independent_agent_review'
            else:
                decision='retained' if best_score is None or score>best_score else 'rejected_no_improvement'
                if decision=='retained':best=record['id'];best_score=score
        completed.append({'id':record['id'],'decision':decision,'macro_f1_50ms':score,
                          'reused_run':bool(index==0 and resume_run)})
        if decision=='rejected_integrity':
            reason='failed_artifact_integrity'
            break
        # No parameter search can be justified without an evaluable reference.
        if score is None:
            reason='waiting_for_validated_reference_or_evaluable_absence_coverage'
            break
        if decision=='requires_independent_agent_review':
            reason='waiting_for_independent_agent_review_of_frozen_artifacts'
            break
    result={'piece_id':piece,'trials':completed,'best_run':best,'best_macro_f1_50ms':best_score,
            'stop_reason':reason,'independent_agent_review_required':True,
            'control_parameters_frozen':piece=='piece_02'}
    write(ROOT/'work'/('cycle-'+piece+'.json'),result)
    return result
