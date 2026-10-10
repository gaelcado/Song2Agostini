import numpy as np
from drum_lab.transient_audit import band_flux, transient_evidence, audit_candidates


def test_silence_abstains_and_empty_band_abstains():
    t,f=band_flux(np.zeros(44100),44100)
    assert not transient_evidence(t,f,.5)['supported']
    t,f=band_flux(np.zeros(8000),8000)
    assert not transient_evidence(t,f,.5)['supported']


def test_local_burst_has_transient_evidence():
    rng=np.random.default_rng(123)
    x=np.zeros(44100);x[22050:22491]=rng.normal(size=441)*np.exp(-np.arange(441)/80)
    t,f=band_flux(x,44100)
    assert transient_evidence(t,f,.5)['supported']
    assert not transient_evidence(t,f,.8)['supported']


def test_cymbal_ambiguity_abstains_and_never_duplicates_existing_hat():
    t=np.arange(0,1,.005);f=np.zeros(len(t));f[100]=1
    hat={'class':'hi-hat','pitch':42,'time':.5}
    cymbal={'class':'cymbals','pitch':49,'time':.53}
    rows=audit_candidates([cymbal],[hat,cymbal],t,f)
    assert rows[0]['supported'] and rows[0]['cymbal_ambiguous'] and not rows[0]['accepted']
    assert audit_candidates([hat],[hat],t,f)==[]
    assert audit_candidates([],[hat],t,f)[0]['accepted']


def test_steady_high_frequency_tone_is_not_a_repeated_attack():
    t=np.arange(44100)/44100
    times,flux=band_flux(np.sin(2*np.pi*8000*t),44100)
    assert not transient_evidence(times,flux,.5)['supported']


def test_gain_scaling_preserves_evidence_and_handles_audio_boundary():
    rng=np.random.default_rng(54);x=np.zeros(44100)
    x[0:441]=rng.normal(size=441)*np.exp(-np.arange(441)/80)
    x[22050:22491]=rng.normal(size=441)*np.exp(-np.arange(441)/80)
    for gain in (1., .01):
        t,f=band_flux(x*gain,44100)
        assert transient_evidence(t,f,0)['supported']
        assert transient_evidence(t,f,.5)['supported']
        assert not transient_evidence(t,f,2)['supported']


def test_close_attacks_have_distinct_local_peaks_without_flams_inference():
    rng=np.random.default_rng(87);x=np.zeros(44100)
    for onset in (.45,.51):
        start=round(onset*44100)
        x[start:start+220]=rng.normal(size=220)*np.exp(-np.arange(220)/40)
    t,f=band_flux(x,44100)
    a=transient_evidence(t,f,.45,tolerance=.012)
    b=transient_evidence(t,f,.51,tolerance=.012)
    assert a['supported'] and b['supported'] and b['peak_time']-a['peak_time']>.04


def test_stationary_noise_without_local_burst_abstains():
    rng=np.random.default_rng(9)
    t,f=band_flux(rng.normal(size=44100),44100)
    assert not transient_evidence(t,f,.5)['supported']


def test_integer_and_float_audio_have_equivalent_flux():
    rng=np.random.default_rng(4);x=rng.integers(-10000,10000,44100,dtype=np.int16)
    ta,fa=band_flux(x,44100);tb,fb=band_flux(x.astype(float)/32768,44100)
    np.testing.assert_array_equal(ta,tb);np.testing.assert_allclose(fa,fb)


def test_invalid_inputs_and_duplicate_candidates():
    import pytest
    for rate,x in ((float('nan'),np.zeros(2048)),(44100,np.zeros((2048,0)))):
        with pytest.raises(ValueError):band_flux(x,rate)
    for t,f in (([0],[1,2]),([float('nan')],[1])):
        with pytest.raises(ValueError):transient_evidence(t,f,0)
    t=np.arange(0,1,.005);f=np.zeros(len(t));f[100]=1
    hat={'class':'hi-hat','pitch':42,'time':.5}
    assert len(audit_candidates([],[hat,hat],t,f))==1


def test_additions_preserve_detector_files_and_original_midi_ticks(tmp_path,monkeypatch):
    import json
    import pretty_midi
    from scipy.io import wavfile
    import drum_lab.transient_audit as module
    from drum_lab import adapters
    midi=pretty_midi.PrettyMIDI(initial_tempo=123,resolution=960)
    drums=pretty_midi.Instrument(0,is_drum=True)
    drums.notes.append(pretty_midi.Note(67,38,.231,.271));midi.instruments.append(drums)
    midi.write(str(tmp_path/'raw.mid'));raw=(tmp_path/'raw.mid').read_bytes()
    prediction={'events':[{'class':'snare','pitch':38,'time':.231}]}
    (tmp_path/'events.json').write_text(json.dumps(prediction));events=(tmp_path/'events.json').read_bytes()
    hat={'class':'hi-hat','pitch':42,'time':.5}
    monkeypatch.setattr(adapters,'adtof',lambda *a,**k:{'events':[hat,hat]})
    monkeypatch.setattr(module,'band_flux',lambda *a:(np.arange(0,1,.005),np.eye(1,200,100).ravel()))
    wavfile.write(tmp_path/'audio.wav',44100,np.zeros(44100,dtype=np.float32))
    result=module.apply_hat_candidates(tmp_path/'audio.wav',tmp_path,'synthetic',[.22,.24,.32,.22,.3],prediction,synthetic=True)
    assert result['events']==prediction['events']+[hat]
    assert (tmp_path/'detector-raw.mid').read_bytes()==raw
    assert (tmp_path/'detector-events.json').read_bytes()==events
    original=pretty_midi.PrettyMIDI(str(tmp_path/'detector-raw.mid'))
    updated=pretty_midi.PrettyMIDI(str(tmp_path/'raw.mid'))
    before=original.instruments[0].notes[0];after=next(n for n in updated.instruments[0].notes if n.pitch==38)
    assert before.velocity==after.velocity==67
    assert original.time_to_tick(before.start)==updated.time_to_tick(after.start)
    assert original.time_to_tick(before.end)==updated.time_to_tick(after.end)


def test_a_support_peak_cannot_explain_two_candidates_or_duplicate_baseline():
    t=np.arange(0,1,.005);f=np.zeros(len(t));f[100]=1
    a={'class':'hi-hat','pitch':42,'time':.49}
    b={'class':'hi-hat','pitch':42,'time':.51}
    rows=audit_candidates([],[b,a],t,f)
    assert sum(r['accepted'] for r in rows)==1
    assert rows[1]['transient_already_used']
    rows=audit_candidates([a],[b],t,f)
    assert rows[0]['transient_already_used'] and not rows[0]['accepted']
