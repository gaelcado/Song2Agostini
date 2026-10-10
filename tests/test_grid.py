import copy
import json
import pytest
from drum_lab.grid import clean_model_grid


def grid(beats, downbeats):
    return {'bpm':120, 'beat_times_seconds':beats, 'downbeat_times_seconds':downbeats,
            'origin_seconds':downbeats[0]}


def test_duplicate_peaks_do_not_add_beats_or_bars():
    original=grid([0,.5,1,1.42,1.5,2,2.5,3,3.5,4], [0,2,3.92,4])
    before=copy.deepcopy(original)
    result=clean_model_grid(original)
    assert original==before
    assert result['beat_times_seconds']==[0,.5,1,1.5,2,2.5,3,3.5,4]
    assert result['downbeat_times_seconds']==[0,2,4]
    assert result['raw_beat_times_seconds']==before['beat_times_seconds']
    assert result['phase_evidence']['downbeat_beat_index_gaps']==[4,4]
    assert result['phase_evidence']['local_downbeats_agree_with_fixed_four_beats']
    assert clean_model_grid(result)==result


def test_no_forced_four_four_phase_on_meter_disagreement():
    result=clean_model_grid(grid([n*.5 for n in range(13)],[0,1.5,3,4.5,6]))
    assert result['downbeat_times_seconds']==[0,1.5,3,4.5,6]
    assert result['phase_evidence']['four_beat_bar_fraction']==0
    assert not result['phase_evidence']['local_downbeats_agree_with_fixed_four_beats']


@pytest.mark.parametrize('beats', [
    [n*.1 for n in range(41)], # Uniform fast tempo must retain all beats.
    [0,.5,1,1.5,1.75,2,2.5,3,3.5,4], # A true eighth-like interval is retained.
    [0,.5,1,1.5,2,2.25,2.5,2.75,3,3.25,3.5,3.75,4],
])
def test_fast_tempo_and_half_quarter_intervals_retained(beats):
    result=clean_model_grid(grid(beats,[0,2,4]))
    assert result['beat_times_seconds']==beats
    assert result['grid_postprocessing']['removed_beat_peaks']==0


@pytest.mark.parametrize('beats', [[0], [0,0,.5], [0,float('nan'),1], [-.1,.5]])
def test_invalid_peaks_rejected(beats):
    with pytest.raises(ValueError): clean_model_grid(grid(beats,[0]))


def test_grid_cache_checks_audio_and_never_reads_reference_path(tmp_path,monkeypatch):
    import drum_lab.pipeline as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'resource_path',lambda relative:tmp_path/relative)
    audio=tmp_path/'audio.mp3';audio.write_bytes(b'audio')
    private=tmp_path/'data/reference/grid.json'
    with pytest.raises(ValueError,match='run audio'):
        module.cached_model_grid(audio,private,tmp_path/'out.json')
    configs=tmp_path/'configs';configs.mkdir()
    (configs/'beat-this-model.json').write_text(json.dumps({'sha256':'weights','code_commit':'code'}))
    cache=tmp_path/'work/runs/frozen/grid.json';cache.parent.mkdir(parents=True)
    value={**grid([0,.5,1,1.5,2],[0,2]),'source':'Beat This! final0 CPU, audio only',
           'audio_sha256':'wrong','checkpoint_sha256':'weights','code_commit':'code'}
    cache.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='incompatible'):
        module.cached_model_grid(audio,cache,tmp_path/'out.json')
    value['audio_sha256']=module.digest(audio);cache.write_text(json.dumps(value))
    result=module.cached_model_grid(audio,cache,tmp_path/'out.json')
    assert result['cache_provenance']['sha256']==module.digest(cache)
    assert result['cache_provenance']['inference_reused'] is True
