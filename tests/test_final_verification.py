import json
from types import SimpleNamespace
import pretty_midi
from drum_lab.files import digest
from drum_lab.final_verification import verify_final


def fixture(tmp_path, monkeypatch):
    import drum_lab.final_verification as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout='Pages: 1\n'))
    out=tmp_path/'run';out.mkdir();(out/'notation').mkdir()
    midi=pretty_midi.PrettyMIDI();part=pretty_midi.Instrument(0,is_drum=True)
    part.notes.append(pretty_midi.Note(80,36,0,0.1));midi.instruments.append(part)
    midi.write(str(out/'raw.mid'));midi.write(str(out/'quantized.mid'))
    (out/'score.pdf').write_bytes(b'pdf')
    (out/'score.musicxml').write_text('<score-partwise><part><measure><attributes><clef><sign>percussion</sign></clef></attributes></measure></part></score-partwise>')
    artifacts={k:str(out/f) for k,f in {'pdf':'score.pdf','musicxml':'score.musicxml','raw_midi':'raw.mid','midi':'quantized.mid'}.items()}
    production={'piece_id':'piece_01','status':'completed','artifacts':artifacts,'artifact_sha256':{k:digest(p) for k,p in artifacts.items()}}
    (out/'production.json').write_text(json.dumps(production))
    (out/'events.json').write_text(json.dumps({'piece_id':'piece_01','events':[{'pitch':36,'time':0,'class':'kick'}]}))
    (out/'notation/notation.json').write_text(json.dumps({'musicxml_audit':{'valid':True},'measures':1}))
    return out,production


def test_no_reference_is_na_and_only_matching_review_accepted(tmp_path,monkeypatch):
    out,production=fixture(tmp_path,monkeypatch)
    result=verify_final(out)
    assert result['integrity']=='passed' and result['musical_fidelity'] is None
    assert result['visual_review']=='requires_independent_review'
    review={'piece_id':'piece_01','artifact_sha256':production['artifact_sha256'],'status':'accepted_as_readable_draft','review_id':'isolated-review'}
    (out/'agent-feedback.json').write_text(json.dumps(review))
    assert verify_final(out)['visual_review']=='accepted_as_readable_draft'
    review['artifact_sha256']['pdf']='stale'
    (out/'agent-feedback.json').write_text(json.dumps(review))
    assert verify_final(out)['visual_review']=='requires_independent_review'


def test_modified_final_artifact_is_rejected(tmp_path,monkeypatch):
    out,_=fixture(tmp_path,monkeypatch)
    (out/'score.pdf').write_bytes(b'changed')
    result=verify_final(out)
    assert result['integrity']=='failed'
    assert 'Artefact modifié' not in result['reason']


def test_melodic_track_is_rejected_even_with_updated_hash(tmp_path,monkeypatch):
    out,production=fixture(tmp_path,monkeypatch)
    midi=pretty_midi.PrettyMIDI(str(out/'raw.mid'));midi.instruments[0].is_drum=False;midi.write(str(out/'raw.mid'))
    production['artifact_sha256']['raw_midi']=digest(out/'raw.mid')
    (out/'production.json').write_text(json.dumps(production))
    assert verify_final(out)['integrity']=='failed'


def test_record_cannot_impersonate_another_piece(tmp_path,monkeypatch):
    out,_=fixture(tmp_path,monkeypatch)
    record={'id':out.name,'piece_id':'piece_02','status':'awaiting_verification'}
    (out/'record.json').write_text(json.dumps(record))
    assert verify_final(out)['integrity']=='failed'


def test_record_binding_accepts_expanded_production_config(tmp_path,monkeypatch):
    out,production=fixture(tmp_path,monkeypatch)
    production.update(audio_sha256='fixture-hash',synthetic=True,
                      config={'hypothesis':'fixture','quantize':True})
    (out/'production.json').write_text(json.dumps(production))
    record={'id':out.name,'piece_id':'piece_01','audio_sha256':'fixture-hash',
            'synthetic':True,'status':'awaiting_verification','config':{'hypothesis':'fixture'}}
    (out/'record.json').write_text(json.dumps(record))
    assert verify_final(out)['integrity']=='passed'


def test_record_binding_rejects_changed_metadata(tmp_path,monkeypatch):
    out,production=fixture(tmp_path,monkeypatch)
    production.update(audio_sha256='fixture-hash',synthetic=True,config={'hypothesis':'fixture'})
    (out/'production.json').write_text(json.dumps(production))
    baseline={'id':out.name,'piece_id':'piece_01','audio_sha256':'fixture-hash',
              'synthetic':True,'status':'awaiting_verification','config':{'hypothesis':'fixture'}}
    for field,value in [('id','another'),('audio_sha256','different'),('synthetic',False),
                        ('status','running'),('config',{'hypothesis':'different'})]:
        record=dict(baseline);record[field]=value
        (out/'record.json').write_text(json.dumps(record))
        result=verify_final(out)
        assert result['integrity']=='failed' and result['musical_fidelity'] is None
        assert 'Registre' not in result['reason']
