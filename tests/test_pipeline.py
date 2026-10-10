import json
from pathlib import Path
import pretty_midi
import pytest
from drum_lab.pipeline import drum_only_events,generate
from drum_lab.optimization import cycle


def test_reject_melodic_pitch_disguised_as_drum():
    with pytest.raises(ValueError):drum_only_events({'events':[{'pitch':60,'class':'snare','time':1}]})
    with pytest.raises(ValueError):drum_only_events({'events':[{'pitch':36,'class':'hi-hat','time':1}]})


def test_production_requires_no_reference_and_reports_failure(tmp_path,monkeypatch):
    import drum_lab.pipeline as module
    monkeypatch.setattr(module,'runtime_identity',lambda name:{'environment':name,'synthetic_fixture':True})
    monkeypatch.setattr(module,'probe_audio',lambda audio: (_ for _ in ()).throw(ValueError('invalid')))
    with pytest.raises(ValueError):generate(tmp_path/'audio.mp3',tmp_path/'output')
    record=json.loads((tmp_path/'output/production.json').read_text())
    assert record['status']=='failed' and record['reference_used'] is False
    assert 'reference_sha256' not in record


def test_cycle_stops_when_reference_missing(tmp_path,monkeypatch):
    import drum_lab.optimization as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    calls=[]
    def research(audio,configs,piece,synthetic):
        calls.append(configs)
        out=tmp_path/'work/runs/run1';out.mkdir(parents=True)
        return [{'id':'run1','status':'awaiting_verification'}]
    def verify(command,**kwargs):
        assert '--reference' not in command
        (tmp_path/'work/runs/run1/final-feedback.json').write_text(json.dumps({'integrity':'passed','musical_fidelity':None}))
    monkeypatch.setattr(module,'run',research);monkeypatch.setattr(module.subprocess,'run',verify)
    result=cycle('audio',[{'hypothesis':'baseline'},{'hypothesis':'variant'}],'piece_01')
    assert len(calls)==1 and result['best_run'] is None
    assert result['stop_reason'].startswith('waiting_')


def test_cycle_cannot_select_unreviewed_score(tmp_path,monkeypatch):
    import drum_lab.optimization as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    calls=[]
    def research(*args):
        calls.append(args);(tmp_path/'work/runs/run1').mkdir(parents=True)
        return [{'id':'run1','status':'awaiting_verification'}]
    def verify(*args,**kwargs):
        (tmp_path/'work/runs/run1/final-feedback.json').write_text(json.dumps({'integrity':'passed','musical_fidelity':{'tolerances':{'50':{'macro_f1':0.9}}},'visual_review':'requires_independent_review'}))
    monkeypatch.setattr(module,'run',research);monkeypatch.setattr(module.subprocess,'run',verify)
    result=cycle('audio',[{},{}],'piece_01')
    assert len(calls)==1 and result['best_run'] is None
    assert result['trials'][0]['decision']=='requires_independent_agent_review'


def test_cycle_resume_rechecks_frozen_output_without_new_run(tmp_path,monkeypatch):
    import drum_lab.optimization as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    audio=tmp_path/'audio.mp3';audio.write_bytes(b'audio')
    out=tmp_path/'work/runs/frozen';out.mkdir(parents=True)
    config={'hypothesis':'baseline'}
    (out/'record.json').write_text(json.dumps({'id':'frozen','piece_id':'piece_01','synthetic':False,'config':config,'audio_sha256':module.digest(audio),'status':'awaiting_verification'}))
    monkeypatch.setattr(module,'run',lambda *a: (_ for _ in ()).throw(AssertionError('Unexpected inference')))
    def verify(*args,**kwargs):
        (out/'final-feedback.json').write_text(json.dumps({'integrity':'passed','musical_fidelity':None,'visual_review':'accepted_as_readable_draft'}))
    monkeypatch.setattr(module.subprocess,'run',verify)
    result=cycle(audio,[config],'piece_01',resume_run='frozen')
    assert result['trials'][0]['reused_run'] is True and result['best_run'] is None
    with pytest.raises(ValueError):cycle(audio,[{'hypothesis':'changed'}],'piece_01',resume_run='frozen')


def frozen_run(tmp_path,module,piece='piece_01',status='awaiting_verification'):
    audio=tmp_path/'audio.mp3';audio.write_bytes(b'audio')
    config={'hypothesis':'baseline'}
    out=tmp_path/'work/runs/frozen';out.mkdir(parents=True)
    record={'id':'frozen','piece_id':piece,'synthetic':False,'config':config,
            'audio_sha256':module.digest(audio),'status':status}
    (out/'record.json').write_text(json.dumps(record))
    return audio,config,out,record


@pytest.mark.parametrize('field,value',[('id','another'),('piece_id','piece_02'),
                                       ('synthetic',True),('audio_sha256','wrong')])
def test_resume_rejects_mismatched_identity(tmp_path,monkeypatch,field,value):
    import drum_lab.optimization as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    audio,config,out,record=frozen_run(tmp_path,module)
    record[field]=value;(out/'record.json').write_text(json.dumps(record))
    monkeypatch.setattr(module,'run',lambda *a: pytest.fail('Unexpected inference'))
    with pytest.raises(ValueError,match='correspond'):cycle(audio,[config],'piece_01',resume_run='frozen')


def test_resume_rejects_unfinished_run(tmp_path,monkeypatch):
    import drum_lab.optimization as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    audio,config,out,record=frozen_run(tmp_path,module,status='running')
    with pytest.raises(ValueError,match='figé'):cycle(audio,[config],'piece_01',resume_run='frozen')


def test_control_resume_requires_current_frozen_parameters(tmp_path,monkeypatch):
    import drum_lab.optimization as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    audio,config,out,record=frozen_run(tmp_path,module,piece='piece_02')
    monkeypatch.setattr(module,'run',lambda *a: pytest.fail('Unexpected inference'))
    with pytest.raises(ValueError,match='gelée'):cycle(audio,[config],'piece_02',resume_run='frozen')
    (tmp_path/'configs').mkdir();(tmp_path/'configs/frozen.json').write_text(json.dumps(config))
    def verify(*args,**kwargs):
        (out/'final-feedback.json').write_text(json.dumps({'integrity':'passed','musical_fidelity':None}))
    monkeypatch.setattr(module.subprocess,'run',verify)
    assert cycle(audio,[config],'piece_02',resume_run='frozen')['control_parameters_frozen'] is True


def test_resume_rechecks_at_budget_but_cannot_add_trial(tmp_path,monkeypatch):
    import drum_lab.optimization as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    audio,config,out,record=frozen_run(tmp_path,module)
    for i in range(12):
        folder=tmp_path/f'work/runs/old-{i}';folder.mkdir()
        (folder/'record.json').write_text(json.dumps({'piece_id':'piece_01','synthetic':False}))
    monkeypatch.setattr(module,'run',lambda *a: pytest.fail('Unexpected inference'))
    def verify(*args,**kwargs):
        (out/'final-feedback.json').write_text(json.dumps({'integrity':'passed','musical_fidelity':None}))
    monkeypatch.setattr(module.subprocess,'run',verify)
    assert len(cycle(audio,[config],'piece_01',resume_run='frozen')['trials'])==1
    with pytest.raises(ValueError,match='Budget'):cycle(audio,[config,config],'piece_01',resume_run='frozen')


def test_cycle_does_not_select_invalidated_scored_run(tmp_path,monkeypatch):
    import drum_lab.optimization as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    audio,config,out,record=frozen_run(tmp_path,module)
    def verify(*args,**kwargs):
        (out/'final-feedback.json').write_text(json.dumps({'integrity':'failed',
            'musical_fidelity':{'tolerances':{'50':{'macro_f1':1}}},
            'visual_review':'accepted_as_readable_draft'}))
    monkeypatch.setattr(module.subprocess,'run',verify)
    result=cycle(audio,[config],'piece_01',resume_run='frozen')
    assert result['best_run'] is None and result['trials'][0]['decision']=='rejected_integrity'
    assert result['trials'][0]['macro_f1_50ms'] is None
    assert result['stop_reason']=='failed_artifact_integrity'


@pytest.mark.parametrize('feedback',[
    None,
    {'integrity':'failed','visual_review':'accepted_as_readable_draft','musical_fidelity':{'tolerances':{'50':{'macro_f1':1}}}},
    {'integrity':'passed','visual_review':'requires_independent_review','musical_fidelity':{'tolerances':{'50':{'macro_f1':1}}}},
    {'integrity':'passed','visual_review':'accepted_as_readable_draft','musical_fidelity':None},
])
def test_leaderboard_discards_stale_score(tmp_path,monkeypatch,feedback):
    from types import SimpleNamespace
    import drum_lab.runner as module
    import drum_lab.pipeline as pipeline
    monkeypatch.setattr(module,'ROOT',tmp_path)
    configs=tmp_path/'configs';configs.mkdir()
    (configs/'evaluation.v2.json').write_text('{}')
    (configs/'adtof.lock.txt').write_text('fixture')
    audio=tmp_path/'audio.wav';audio.write_bytes(b'fixture')
    for identifier,score in [('invalidated',1),('valid',0.99)]:
        folder=tmp_path/'work/runs'/identifier;folder.mkdir(parents=True)
        (folder/'record.json').write_text(json.dumps({'id':identifier,'piece_id':'piece_01',
            'synthetic':True,'status':'awaiting_verification','macro_f1_50ms':score}))
    invalidated=tmp_path/'work/runs/invalidated'
    if feedback is not None:(invalidated/'final-feedback.json').write_text(json.dumps(feedback))
    (tmp_path/'work/runs/valid/final-feedback.json').write_text(json.dumps({
        'integrity':'passed','visual_review':'accepted_as_readable_draft',
        'musical_fidelity':{'tolerances':{'50':{'macro_f1':0.4}}}}))
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k: SimpleNamespace(stdout=''))
    monkeypatch.setattr(pipeline,'generate',lambda *a,**k: (_ for _ in ()).throw(ValueError('fixture failure')))
    module.run(audio,[{'hypothesis':'fixture'}],'piece_01',synthetic=True)
    ranking=json.loads((tmp_path/'work/leaderboard-piece_01.json').read_text())
    assert ranking[0]['id']=='valid' and ranking[0]['macro_f1_50ms']==0.4
    assert 'macro_f1_50ms' not in next(r for r in ranking if r['id']=='invalidated')


def test_all_adtof_classes_keep_gm_identity():
    from drum_lab.engraving import KIT
    events=[{'pitch':p,'class':c,'time':1.} for p,c in
            [(35,'kick'),(38,'snare'),(47,'toms'),(42,'hi-hat'),(49,'cymbals')]]
    assert drum_only_events({'events':events})['events']==events
    assert KIT[35][:3]==('Grosse caisse','D',4)
    assert KIT[38][:3]==('Caisse claire','B',4)


def test_experimental_engines_do_not_change_defaults(tmp_path):
    from drum_lab.pipeline import DEFAULT_CONFIG
    assert DEFAULT_CONFIG.get('grid_engine','librosa')=='librosa'
    assert DEFAULT_CONFIG.get('engine','adtof')=='adtof'
    with pytest.raises(ValueError,match='grille'):
        generate(tmp_path/'a.wav',tmp_path/'out',{'grid_engine':'unknown'})
    with pytest.raises(ValueError,match='isolée'):
        generate(tmp_path/'a.wav',tmp_path/'out',{'engine':'adtof_kit','separate_drums':False})


def test_missing_runtime_preserves_failed_production_record(tmp_path,monkeypatch):
    import drum_lab.pipeline as module
    output=tmp_path/'output'
    def missing_runtime(name):
        initial=json.loads((output/'production.json').read_text())
        assert initial['status']=='running'
        assert initial['reference_used'] is False
        raise FileNotFoundError('ADTOF interpreter absent')
    monkeypatch.setattr(module,'runtime_identity',missing_runtime)
    monkeypatch.setattr(module,'probe_audio',lambda *a:pytest.fail('Audio must not be probed after missing runtime'))
    with pytest.raises(FileNotFoundError,match='interpreter absent'):
        generate(tmp_path/'audio.wav',output)
    failed=json.loads((output/'production.json').read_text())
    assert failed['status']=='failed'
    assert failed['error']=={'type':'FileNotFoundError','message':'ADTOF interpreter absent'}
    assert failed['duration_seconds']>=0
    assert 'runtime_identity' not in failed and 'reference_sha256' not in failed
