import xml.etree.ElementTree as ET
from pathlib import Path
import pretty_midi
import pytest
from types import SimpleNamespace

def fake_render(command,**kwargs):
    Path(command[command.index('-o')+1]).write_bytes(b'%PDF-test')
    return SimpleNamespace(returncode=0)
from drum_lab.engraving import engrave


def test_chords_complete_voices_and_raw_midi_preserved(tmp_path,monkeypatch):
    import drum_lab.engraving as module
    midi=pretty_midi.PrettyMIDI(initial_tempo=120)
    kit=pretty_midi.Instrument(0,is_drum=True)
    for pitch,time in [(36,0),(38,0),(42,0),(42,.25),(36,2.5)]:
        kit.notes.append(pretty_midi.Note(90,pitch,time,time+.1))
    midi.instruments.append(kit)
    source=tmp_path/'raw.mid';midi.write(str(source));before=source.read_bytes()
    monkeypatch.setattr(module,'renderer',lambda:'/fake/mscore')
    monkeypatch.setattr(module.subprocess,'run',fake_render)
    result=engrave(source,{'bpm':120,'duration_seconds':6},tmp_path/'notation')
    assert result['measures']==3
    assert source.read_bytes()==before
    xml=ET.parse(tmp_path/'notation/score.musicxml')
    assert len(xml.findall('.//note/chord'))==1
    assert len(xml.findall('.//note/unpitched'))==5
    for measure in xml.findall('.//measure'):
        for voice in ('1','2'):
            total=sum(int(n.findtext('duration')) for n in measure.findall('note')
                      if n.findtext('voice')==voice and n.find('chord') is None)
            assert total==16
    quant=pretty_midi.PrettyMIDI(str(tmp_path/'notation/quantized.mid'))
    assert len(quant.instruments[0].notes)==5


def test_invalid_grid_rejected_before_render(tmp_path):
    with pytest.raises(ValueError,match='Grille'):
        engrave('absent',{'bpm':float('nan')},tmp_path)


def test_compact_expansion_and_melodic_warning(tmp_path, monkeypatch):
    import drum_lab.engraving as module
    monkeypatch.setattr(module,'renderer',lambda:'/fake/mscore')
    monkeypatch.setattr(module.subprocess,'run',fake_render)
    midi=pretty_midi.PrettyMIDI(initial_tempo=120)
    kit=pretty_midi.Instrument(0,is_drum=True)
    for bar in range(6):
        for pitch,t in [(36,0),(42,.25),(38,1)]:
            kit.notes.append(pretty_midi.Note(90,pitch,bar*2+t,bar*2+t+.1))
    melodic=pretty_midi.Instrument(0);melodic.notes.append(pretty_midi.Note(90,60,0,.1))
    midi.instruments=[kit,melodic]; source=tmp_path/'raw.mid';midi.write(str(source))
    compact=engrave(source,{'bpm':120,'duration_seconds':12},tmp_path/'compact')
    unfolded=engrave(source,{'bpm':120,'duration_seconds':12},tmp_path/'unfolded',compact=False)
    assert compact['displayed_measures']==1
    assert compact['musicxml_audit']['valid']
    assert compact['musicxml_audit']['expanded_hits']==unfolded['notation_chord_hits']==18
    assert compact['warnings']
    assert not ET.parse(tmp_path/'compact/score.musicxml').findall('.//pitch')


def test_silent_multimeasure_rest(tmp_path, monkeypatch):
    import drum_lab.engraving as module
    monkeypatch.setattr(module,'renderer',lambda:'/fake/mscore')
    monkeypatch.setattr(module.subprocess,'run',fake_render)
    midi=pretty_midi.PrettyMIDI();kit=pretty_midi.Instrument(0,is_drum=True)
    kit.notes.append(pretty_midi.Note(90,36,0,.1));midi.instruments=[kit]
    source=tmp_path/'raw.mid';midi.write(str(source))
    result=engrave(source,{'bpm':120,'duration_seconds':8},tmp_path/'score')
    assert ET.parse(tmp_path/'score/score.musicxml').findtext('.//multiple-rest')=='3'
    assert result['musicxml_audit']['valid']


def test_per_quarter_tempo_and_clock_offset(tmp_path, monkeypatch):
    import drum_lab.engraving as module
    monkeypatch.setattr(module,'renderer',lambda:'/fake/mscore')
    monkeypatch.setattr(module.subprocess,'run',fake_render)
    midi=pretty_midi.PrettyMIDI();kit=pretty_midi.Instrument(0,is_drum=True)
    for t in [.2,.45,.7,1.1,1.3]: kit.notes.append(pretty_midi.Note(90,36,t,t+.1))
    midi.instruments=[kit];source=tmp_path/'raw.mid';midi.write(str(source))
    grid={'bpm':120,'origin_seconds':.2,'beat_times_seconds':[.2,.7,1.3,1.8,2.3],'duration_seconds':2.3}
    result=engrave(source,grid,tmp_path/'score')
    xml=ET.parse(tmp_path/'score/score.musicxml')
    measure=xml.find('.//measure')
    assert [int(n.findtext('duration')) for n in measure.findall('forward')]==[4,4,4,4]
    assert len(measure.findall('./direction[@print-object="no"]/sound'))==4
    assert result['quality']['musicxml_audio_offset_seconds']==pytest.approx(.2)
    assert result['quality']['musicxml_midi_max_relative_timing_error_ms']<.001


def test_layout_balances_pages_and_never_breaks_hidden_rest_measures():
    from drum_lab.engraving import presentation_layout
    active=tuple((i,(36,) if i==0 else ()) for i in range(16))
    silent=tuple((i,()) for i in range(16))
    patterns=[active]*49+[silent]*8
    segments=[(i,1,1) for i in range(49)]+[(49,8,1)]
    breaks,sizes=presentation_layout(patterns,segments)
    assert sizes==[5,4,4]
    assert max(sizes)-min(sizes)<=1
    assert not any(number in breaks for number in range(50,57))
    assert sum(kind=='page' for kind in breaks.values())==2


def test_legend_and_short_repeat_do_not_add_events(tmp_path,monkeypatch):
    import drum_lab.engraving as module
    monkeypatch.setattr(module,'renderer',lambda:'/fake/mscore')
    monkeypatch.setattr(module.subprocess,'run',fake_render)
    midi=pretty_midi.PrettyMIDI();kit=pretty_midi.Instrument(0,is_drum=True)
    for bar in range(4):
        for pitch,time in [(35,0),(38,.5),(42,1),(47,1.25),(49,1.5)]:
            kit.notes.append(pretty_midi.Note(90,pitch,bar*2+time,bar*2+time+.1))
    midi.instruments=[kit];source=tmp_path/'raw.mid';midi.write(str(source))
    result=engrave(source,{'bpm':120,'duration_seconds':8},tmp_path/'score')
    xml=ET.parse(tmp_path/'score/score.musicxml')
    words=[w.text for w in xml.findall('.//words') if w.text]
    assert len(result['kit_legend'])==5
    assert any('Légende' in w for w in words)
    assert any('croix (x)' in w for w in words)
    assert any(w=='Jouer 4 fois' for w in words)
    assert not any(w.startswith('Mesures ') for w in words)
    assert result['musicxml_audit']['valid']
    assert result['musicxml_audit']['expanded_hits']==20

@pytest.mark.parametrize('system_count',[1,5,6,12,13,16,18,29,40])
@pytest.mark.parametrize('legend_lines',[1,5,8])
def test_layout_reserves_first_page_space_and_preserves_all_systems(system_count,legend_lines):
    import math
    from drum_lab.engraving import presentation_layout
    active=tuple((i,(36,38,42) if i%2==0 else ()) for i in range(16))
    patterns=[active]*(system_count*4)
    breaks,sizes=presentation_layout(patterns,[(i,1,1) for i in range(len(patterns))],legend_lines=legend_lines)
    capacity=max(1,6-math.ceil(30*(legend_lines+1)/180))
    assert sizes[0]<=capacity
    assert all(0<size<=6 for size in sizes)
    assert sum(sizes)==system_count
    assert len(breaks)==system_count
    assert set(breaks)==set(range(0,len(patterns),4))
    assert sum(kind=='page' for kind in breaks.values())==len(sizes)-1
    if len(sizes)>1:
        assert max(sizes[1:])-min(sizes[1:])<=1
    if system_count>=8 and legend_lines<=5:
        assert min(sizes)>=2


def test_layout_long_silence_is_one_visible_unit_and_no_hidden_page_breaks():
    from drum_lab.engraving import presentation_layout
    active=tuple((i,(36,42) if i%2==0 else ()) for i in range(16))
    silent=tuple((i,()) for i in range(16))
    patterns=[active]*24+[silent]*100+[active]*40
    segments=[(i,1,1) for i in range(24)]+[(24,100,1)]+[(i,1,1) for i in range(124,164)]
    breaks,sizes=presentation_layout(patterns,segments)
    assert sum(sizes)==17
    assert sizes==[5,6,6]
    assert not set(breaks).intersection(range(25,124))


def test_layout_empty_and_invalid_capacity():
    from drum_lab.engraving import presentation_layout
    assert presentation_layout([],[])==({},[])
    with pytest.raises(ValueError):
        presentation_layout([],[],systems_per_page=1)
    with pytest.raises(ValueError):
        presentation_layout([],[],legend_lines=-1)


def test_french_positions_and_voice_assignment():
    from drum_lab.engraving import KIT
    assert KIT[36][1:]==('D',4,'normal',2)
    assert KIT[38][1:]==('B',4,'normal',2)
    assert KIT[42][1:]==('G',5,'x',1)
    assert KIT[47][1:]==('D',5,'normal',2)
    assert KIT[49][1:]==('A',5,'x',1)
    assert KIT[51][1:]==('B',5,'x',1)
    assert KIT[44][1:]==('B',3,'x',2)


@pytest.mark.parametrize('durations,rest_indexes,secondary',[
    ([2,2],[],[]),
    ([1,1,1,1],[],['begin','continue','continue','end']),
    ([1,2,1],[1],['forward hook','backward hook']),
    ([3,1],[],['backward hook']),
    ([1,3],[],['forward hook']),
    ([1,1,2],[0],['begin','end']),
])
def test_explicit_beams_by_beat_including_rests(durations,rest_indexes,secondary):
    from drum_lab.engraving import add, beam_voice_by_beat
    measure=ET.Element('measure')
    for beat in range(4):
        for index,duration in enumerate(durations):
            note=add(measure,'note')
            add(note,'rest' if index in rest_indexes else 'unpitched')
            add(note,'duration',duration);add(note,'voice',1)
    beam_voice_by_beat(measure,1)
    primary=[n.findtext('beam[@number="1"]') for n in measure.findall('note')]
    assert primary==(['begin']+['continue']*(len(durations)-2)+['end'])*4
    assert [b.text for b in measure.findall('note/beam[@number="2"]')]==secondary*4


def test_beams_skip_chord_followers_and_silent_beats():
    from drum_lab.engraving import add, beam_voice_by_beat
    measure=ET.Element('measure')
    for position in range(4):
        note=add(measure,'note');add(note,'unpitched');add(note,'duration',1);add(note,'voice',2)
        chord=add(measure,'note');add(chord,'chord');add(chord,'unpitched');add(chord,'duration',1);add(chord,'voice',2)
    for position in range(2):
        note=add(measure,'note');add(note,'rest');add(note,'duration',2);add(note,'voice',2)
    beam_voice_by_beat(measure,2)
    assert len(measure.findall('note/beam[@number="1"]'))==4
    assert all(n.find('beam') is None for n in measure.findall('note') if n.find('chord') is not None or n.find('rest') is not None)


@pytest.mark.parametrize('platform,expected',[('win32','windows'),('darwin','cocoa'),('linux','offscreen')])
def test_export_uses_platform_supported_qt_plugin(tmp_path,monkeypatch,platform,expected):
    import drum_lab.engraving as module
    import drum_lab.rendering as rendering
    monkeypatch.setattr(module,'sys',SimpleNamespace(platform=platform))
    monkeypatch.setattr(module,'renderer',lambda:'/fake/mscore')
    monkeypatch.setattr(rendering,'ROOT',tmp_path)
    monkeypatch.setenv('QT_PLUGIN_PATH','desktop-qt-plugins')
    calls=[]
    def export(command,**kwargs):
        calls.append(kwargs['env'])
        assert kwargs['env']['QT_QPA_PLATFORM']==expected
        assert 'QT_PLUGIN_PATH' not in kwargs['env']
        return fake_render(command,**kwargs)
    monkeypatch.setattr(module.subprocess,'run',export)
    midi=pretty_midi.PrettyMIDI(initial_tempo=120)
    kit=pretty_midi.Instrument(0,is_drum=True)
    kit.notes.append(pretty_midi.Note(90,36,.1,.2));midi.instruments.append(kit)
    source=tmp_path/'raw.mid';midi.write(str(source))
    result=engrave(source,{'bpm':120,'duration_seconds':2},tmp_path/'notation')
    assert result['status']=='draft_rendered' and len(calls)==1
    assert (tmp_path/'notation/score.pdf').is_file()
