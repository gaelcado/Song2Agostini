import numpy as np
import pretty_midi
import xml.etree.ElementTree as ET
from drum_lab.meter import infer_meter
from drum_lab.quantization import quantize_hits
from drum_lab.engraving import engrave


def grid(cycle=4):
    return {'beat_times_seconds':np.arange(40,dtype=float).tolist(),
            'downbeat_times_seconds':np.arange(0,40,cycle,dtype=float).tolist(),
            'bpm':60.,'origin_seconds':0.,'duration_seconds':39.,'time_signature':'4/4','subdivision':4}


def test_three_cycle_not_forced_four():
    g=infer_meter(grid(3),np.arange(.5,39,.5))
    assert g['time_signature']=='3/4'
    assert '6/8 at another pulse scale' in g['meter_evidence']['notation_alternatives']


def test_ternary_four_pulses_has_real_compound_quarter_coordinates():
    g=infer_meter(grid(),np.arange(1/3,39,1/3))
    assert g['time_signature']=='12/8'
    hits=[pretty_midi.Note(90,42,t,t+.1) for t in (0.,1/3,2/3,1.,4.)]
    mapped,_,_,_=quantize_hits(hits,g)
    assert [slot for _,slot,_ in mapped]==[0,2,4,6,24]
    assert [time for _,_,time in mapped]==[0.,1/3,2/3,1.,4.]
    extra,_,_,_=quantize_hits([pretty_midi.Note(90,42,1/6,1/6+.1)],g)
    assert extra[0][1]==1


def test_sparse_offbeats_abstain_subdivision():
    g=infer_meter(grid(),np.arange(39))
    assert g['meter_evidence']['status']=='abstained'
    assert g['meter_evidence']['subdivision']=='ambiguous'


def test_irregular_downbeats_abstain_grouping_but_keep_ternary_candidate():
    g=grid(); g['downbeat_times_seconds']=[0,4,8,12,14,18,22,25,29,33,36]
    g=infer_meter(g,np.arange(1/3,39,1/3))
    assert g['time_signature']=='12/8'
    assert g['meter_evidence']['status']=='abstained'


def test_meter_mode_does_not_repair_tempo_changes_as_missing_beats():
    g=grid();g['beat_times_seconds']=[0,1,2,4,6,8];g['meter_evidence']={'status':'abstained'}
    mapped,_,_,_=quantize_hits([pretty_midi.Note(90,38,4,4.1)],g)
    assert mapped[0][1]==12


def test_compound_xml_eighths_and_dotted_tempo(tmp_path, monkeypatch):
    import drum_lab.engraving as module
    import drum_lab.rendering as rendering
    monkeypatch.setattr(module,'renderer',lambda:'synthetic-renderer')
    def fake_render(command,env,out):
        (out/'score.pdf').write_bytes(b'%PDF synthetic software test')
        return []
    monkeypatch.setattr(rendering,'render',fake_render)
    midi=pretty_midi.PrettyMIDI();part=pretty_midi.Instrument(0,is_drum=True)
    part.notes=[pretty_midi.Note(90,42,t,t+.1) for t in np.arange(0,4,1/3)]
    midi.instruments.append(part);midi.write(str(tmp_path/'raw.mid'))
    g=infer_meter(grid(),np.arange(1/3,39,1/3));g['duration_seconds']=4
    record=engrave(tmp_path/'raw.mid',g,tmp_path/'out',compact=False)
    root=ET.parse(tmp_path/'out/score.musicxml')
    assert root.findtext('.//time/beats')=='12'
    assert root.findtext('.//time/beat-type')=='8'
    assert root.find('.//metronome/beat-unit-dot') is not None
    assert root.findtext('.//metronome/per-minute')=='60.0'
    assert record['musicxml_audit']['valid']
    assert record['quality']['musicxml_midi_max_relative_timing_error_ms']<.01


def test_meter_cache_never_chains_old_derived_signature_or_tempo():
    base=grid();derived=infer_meter(base,np.arange(1/3,39,1/3))
    derived['downbeat_times_seconds']=[0.,3.,7.,9.,14.,19.,21.,26.,32.]
    fresh=infer_meter(derived,[])
    assert fresh['time_signature']=='4/4'
    assert fresh['pulse_quarter_length']==1.
    assert fresh['bpm']==60.
