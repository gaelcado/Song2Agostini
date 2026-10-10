import hashlib
import json
import pytest
from drum_lab import kit_detection as kit


def test_provenance_rejects_altered_weights(tmp_path, monkeypatch):
    monkeypatch.setattr(kit, 'ROOT', tmp_path)
    monkeypatch.setattr(kit, 'runtime_identity', lambda name:{'environment':name})
    monkeypatch.setattr(kit, 'resource_path', lambda name: tmp_path/name)
    monkeypatch.setattr(kit, 'worker_path', lambda name: tmp_path/'scripts'/name)
    monkeypatch.setattr(kit, 'runtime_root', lambda: tmp_path/'work')
    (tmp_path/'configs').mkdir(); (tmp_path/'work/models/kit').mkdir(parents=True)
    model = tmp_path/'work/models/kit/kick.onnx'; model.write_bytes(b'pinned')
    sha = hashlib.sha256(b'pinned').hexdigest()
    (tmp_path/'configs/kit-model.json').write_text(json.dumps({'models': {'kick': {'filename':'kick.onnx','sha256':sha}}}))
    (tmp_path/'configs/kit.lock.txt').write_text('fixed runtime')
    (tmp_path/'scripts').mkdir(); (tmp_path/'scripts/kit_worker.py').write_text('worker')
    audio = tmp_path/'audio.wav'; audio.write_bytes(b'audio')
    before = kit.kit_identity(audio)
    audio.write_bytes(b'different audio')
    assert kit.kit_identity(audio)['audio'] != before['audio']
    model.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='Poids kit'): kit.kit_identity(audio)


def test_composition_retains_only_corresponding_stem_class(tmp_path, monkeypatch):
    from drum_lab import adapters
    def event(time, instrument, pitch): return {'time':time,'class':instrument,'pitch':pitch}
    def fake_adtof(audio, out, piece_id, thresholds, synthetic):
        name = str(audio)
        events = {'original':[event(1,'kick',35),event(2,'snare',38),event(3,'hi-hat',42)],
          'kick':[event(4,'kick',35),event(5,'snare',38)],
          'snare':[event(6,'snare',38),event(7,'toms',47)]}[name]
        return {'schema_version':1,'kind':'prediction','piece_id':piece_id,'synthetic':synthetic,'events':events}
    monkeypatch.setattr(kit,'separate_kit',lambda audio,out: {'kick':'kick','snare':'snare'})
    monkeypatch.setattr(adapters,'adtof',fake_adtof)
    result = kit.adtof_kit('original', tmp_path, 'synthetic', [.2]*5, True)
    assert [(e['time'],e['class']) for e in result['events']] == [(3,'hi-hat'),(4,'kick'),(6,'snare')]
    assert (tmp_path/'raw.mid').is_file()
