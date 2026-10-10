import inspect
import json
from pathlib import Path
import pytest
from drum_lab.files import digest
from drum_lab.pieces import registered_audio
from drum_lab.benchmark import benchmark


def registered(tmp_path):
    audio=tmp_path/'data/raw/audio/bench_01.wav';audio.parent.mkdir(parents=True);audio.write_bytes(b'audio')
    manifest=tmp_path/'data/benchmark-research-manifest.json'
    manifest.write_text(json.dumps({'pieces':[{'id':'bench_01','audio':'data/raw/audio/bench_01.wav','audio_sha256':digest(audio)}]}))
    return audio,manifest


def test_registered_case_checks_audio_identity_and_integrity(tmp_path):
    audio,_=registered(tmp_path)
    assert registered_audio('bench_01',audio,tmp_path)['id']=='bench_01'
    with pytest.raises(ValueError):registered_audio('bench_01',tmp_path/'other.wav',tmp_path)
    audio.write_bytes(b'changed')
    with pytest.raises(ValueError,match='modifié'):registered_audio('bench_01',audio,tmp_path)
    with pytest.raises(ValueError):registered_audio('../piece',audio,tmp_path)


def test_batch_prevalidates_before_inference_and_has_no_reference(tmp_path,monkeypatch):
    import drum_lab.benchmark as module
    audio,_=registered(tmp_path);monkeypatch.setattr(module,'ROOT',tmp_path)
    calls=[]
    monkeypatch.setattr(module,'run',lambda *a: calls.append(a))
    with pytest.raises(ValueError,match='manquant'):benchmark([{}],['bench_01','bench_02'])
    assert not calls and 'reference' not in inspect.signature(benchmark).parameters
    with pytest.raises(ValueError):benchmark([{},{}],['bench_01'])
    with pytest.raises(ValueError):benchmark([{}],['bench_01','bench_01'])


def test_batch_passes_only_audio_to_runner_and_artifacts_to_worker(tmp_path,monkeypatch):
    import drum_lab.benchmark as module
    audio,_=registered(tmp_path);monkeypatch.setattr(module,'ROOT',tmp_path)
    def research(path,configs,piece):
        assert path==audio and piece=='bench_01'
        out=tmp_path/'work/runs/run';out.mkdir(parents=True)
        return [{'id':'run','status':'awaiting_verification','duration_seconds':1}]
    def verify(cmd,**kwargs):
        assert '--reference' not in cmd and cmd[-1]==str(tmp_path/'work/runs/run')
        (tmp_path/'work/runs/run/final-feedback.json').write_text(json.dumps({'integrity':'passed','visual_review':'requires_independent_review'}))
    monkeypatch.setattr(module,'run',research);monkeypatch.setattr(module.subprocess,'run',verify)
    result=benchmark([{'hypothesis':'fixed baseline'}],['bench_01'])
    assert result['reference_used'] is False and result['musical_fidelity'] is None
    assert result['cases'][0]['visual_review']=='requires_independent_review'


def test_batch_prevalidates_all_trial_budgets_before_inference(tmp_path,monkeypatch):
    import drum_lab.benchmark as module
    audio,manifest=registered(tmp_path);monkeypatch.setattr(module,'ROOT',tmp_path)
    second=audio.with_name('bench_02.wav');second.write_bytes(b'second audio')
    data=json.loads(manifest.read_text())
    data['pieces'].append({'id':'bench_02','audio':str(second.relative_to(tmp_path)),
                           'audio_sha256':digest(second)})
    manifest.write_text(json.dumps(data))
    for index in range(13):
        folder=tmp_path/'work/runs'/str(index);folder.mkdir(parents=True)
        (folder/'record.json').write_text(json.dumps({'piece_id':'bench_02','synthetic':False}))
    monkeypatch.setattr(module,'run',lambda *a: pytest.fail('Unexpected inference before full preflight'))
    with pytest.raises(ValueError,match='Budget'):
        benchmark([{'hypothesis':'fixed baseline'}],['bench_01','bench_02'])


@pytest.mark.parametrize('profile',[None,{}, {'hypothesis':''}, {'hypothesis':42}])
def test_batch_rejects_invalid_profile_before_inference(tmp_path,monkeypatch,profile):
    import drum_lab.benchmark as module
    registered(tmp_path);monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'run',lambda *a: pytest.fail('Unexpected inference'))
    with pytest.raises(ValueError,match='Hypothèse'):
        benchmark([profile],['bench_01'])
