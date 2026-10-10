"""Synthetic contract checks, never musical benchmarks."""
import json
import runpy
import sys
import types
from pathlib import Path

import pretty_midi
import pytest


def test_worker_preserves_raw_seconds_unknowns_and_cache(tmp_path, monkeypatch):
    cache=tmp_path/'cache'; cache.mkdir()
    out=tmp_path/'out'; out.mkdir()
    calls=[]
    ds=types.ModuleType('drumscript'); ds.__version__='fixture'
    ds.load_audio=lambda *args,**kwargs: (calls.append('load') or [1],44100)
    ds.normalise_audio=lambda y:y
    ds.detect_onsets=lambda y,sr:[0.123456]
    ds.classify_events=lambda *args:[{'time_sec':0.123456,'instruments':['kick','unknown'],'debug_features':{}}]
    constants=types.ModuleType('drumscript.notation_generator.constants')
    constants.SAMPLE_RATE=44100; constants.DRUM_NOTATION_MAP={'kick':{'midi_program':36}}
    monkeypatch.setitem(sys.modules,'drumscript',ds)
    monkeypatch.setitem(sys.modules,'drumscript.notation_generator.constants',constants)
    worker=Path(__file__).parents[1]/'scripts/drumscript_worker.py'
    monkeypatch.setattr(sys,'argv',[str(worker),'fixture.wav',str(cache),str(out),'synthetic','True'])
    runpy.run_path(str(worker),run_name='__main__')
    runpy.run_path(str(worker),run_name='__main__')
    prediction=json.loads((out/'events.json').read_text())
    assert prediction['synthetic'] is True
    assert prediction['events']==[{'time':0.123456,'pitch':36,'class':'kick'}]
    assert calls==['load']
    midi=pretty_midi.PrettyMIDI(str(out/'raw.mid'))
    assert midi.instruments[0].is_drum
    assert abs(midi.instruments[0].notes[0].start-0.123456)<0.00005
    assert json.loads((out/'drumscript-diagnostics.json').read_text())['unknown_instruments_skipped']=={'unknown':1}


def test_unknown_engine_fails_before_audio_read(tmp_path, monkeypatch):
    import drum_lab.pipeline as module
    monkeypatch.setattr(module,'probe_audio',lambda audio:pytest.fail('unexpected audio read'))
    with pytest.raises(ValueError,match='Moteur inconnu'):
        module.generate(tmp_path/'audio.mp3',tmp_path/'out',{'engine':'unknown'})
