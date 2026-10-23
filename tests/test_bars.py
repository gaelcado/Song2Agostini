import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pretty_midi

from drum_lab.bars import apply_variable_bars, bar_lengths, dominant_length, drum_downbeat_evidence, segment_bars
from drum_lab.engraving import engrave


def activation_for(lengths, high=.9, low=.05):
    values = []
    for n in lengths:
        values += [high] + [low] * (n - 1)
    return values


def test_segmentation_follows_local_five_beat_bar():
    lengths = [4, 4, 4, 5, 4, 4, 5, 4, 4, 4]
    starts = segment_bars(activation_for(lengths))
    assert bar_lengths(starts, sum(lengths)) == lengths


def test_isolated_spurious_peak_inside_bar_is_ignored():
    a = activation_for([4] * 8)
    a[10] = .55  # weak extra peak, not a confident downbeat
    starts = segment_bars(a)
    assert set(np.diff(starts)) == {4}


def test_dominant_length_learned_from_peaks():
    assert dominant_length(activation_for([3] * 10)) == 3
    assert dominant_length(activation_for([2] * 10)) == 2
    assert dominant_length([.1] * 20) == 4


def grid_for(lengths, beat=.5):
    beats = [i * beat for i in range(sum(lengths))]
    return {'bpm': 60 / beat, 'beat_times_seconds': beats, 'beat_downbeat_activation': activation_for(lengths),
            'time_signature': '4/4', 'pulse_quarter_length': 1., 'duration_seconds': beats[-1] + beat}


def test_apply_variable_bars_sets_origin_and_lengths():
    grid = apply_variable_bars(grid_for([4, 5, 4, 4]))
    assert grid['bar_beats'] == [4, 5, 4, 4]
    assert grid['variable_meter'] and grid['bar_evidence']['status'] == 'inferred_hypothesis'
    assert grid['origin_seconds'] == 0


def test_compound_and_missing_activation_abstain():
    grid = grid_for([4, 4, 4])
    assert apply_variable_bars({**grid, 'pulse_quarter_length': 1.5})['bar_evidence']['status'] == 'abstained'
    grid.pop('beat_downbeat_activation')
    assert 'bar_beats' not in apply_variable_bars(grid)


def test_drum_cues_are_bounded_shifts():
    events = [{'time': 0., 'class': 'cymbals'}, {'time': 0., 'class': 'kick'}, {'time': .5, 'class': 'snare'}]
    cues = drum_downbeat_evidence([0., .5, 1.], events)
    assert cues[0] > 0 > cues[1] and cues[2] == 0


def fake_render(command, **kwargs):
    Path(command[command.index('-o') + 1]).write_bytes(b'%PDF-test')
    return SimpleNamespace(returncode=0)


def test_engraving_writes_signature_changes_and_full_voices(tmp_path, monkeypatch):
    import drum_lab.engraving as module
    monkeypatch.setattr(module, 'renderer', lambda: '/fake/mscore')
    monkeypatch.setattr(module.subprocess, 'run', fake_render)
    lengths = [4, 5, 4, 5, 4]
    grid = apply_variable_bars(grid_for(lengths))
    midi = pretty_midi.PrettyMIDI(initial_tempo=120)
    kit = pretty_midi.Instrument(0, is_drum=True)
    t = 0.
    for n in lengths:
        kit.notes.append(pretty_midi.Note(90, 49, t, t + .1))
        for beat in range(n):
            kit.notes.append(pretty_midi.Note(90, 42, t + beat * .5, t + beat * .5 + .1))
            kit.notes.append(pretty_midi.Note(90, 38 if beat % 2 else 36, t + beat * .5, t + beat * .5 + .1))
        t += n * .5
    midi.instruments.append(kit)
    source = tmp_path / 'raw.mid'
    midi.write(str(source))
    result = engrave(source, grid, tmp_path / 'notation', compact=False)
    assert result['musicxml_audit']['valid']
    assert result['measure_signatures'][:5] == ['4/4', '5/4', '4/4', '5/4', '4/4']
    xml = ET.parse(tmp_path / 'notation/score.musicxml')
    measures = xml.findall('.//measure')
    assert [m.findtext('attributes/time/beats') for m in measures[:5]] == ['4', '5', '4', '5', '4']
    for measure, n in zip(measures, lengths):
        for voice in ('1', '2'):
            total = sum(int(x.findtext('duration')) for x in measure.findall('note')
                        if x.findtext('voice') == voice and x.find('chord') is None)
            assert total == 4 * n


def test_absolute_picking_recovers_peaks_on_sustained_activation(tmp_path):
    import json
    from drum_lab.picking import absolute_peaks, repick
    curve = np.full(200, .3)
    for f in range(10, 200, 30):
        curve[f] = .55  # strokes over a sustained wash: relative picking would reject them
    assert len(absolute_peaks(curve, .22)) == 7
    acts = np.zeros((200, 5)); acts[:, 3] = curve; acts[50, 0] = .9
    np.save(tmp_path / 'a.npy', acts)
    (tmp_path / 'events.json').write_text(json.dumps({'events': [{'time': .5, 'class': 'kick', 'pitch': 35}]}))
    doc = repick(tmp_path, tmp_path / 'a.npy', [.22, .24, .32, .22, .30], ['hi-hat'])
    assert sum(e['class'] == 'hi-hat' for e in doc['events']) == 7
    assert [e for e in doc['events'] if e['class'] == 'kick'] == [{'time': .5, 'class': 'kick', 'pitch': 35}]
    assert (tmp_path / 'detector-events.json').is_file() and (tmp_path / 'raw.mid').is_file()


def test_steady_cymbal_stream_drawn_as_ride_keeping_accent():
    from drum_lab.engraving import ride_streams
    hits = [pretty_midi.Note(90, 49, t, t + .1) for t in (0, .3, .6, .9, 1.2)] + [pretty_midi.Note(90, 49, 5, 5.1)]
    assert ride_streams(hits) == 4
    assert [n.pitch for n in hits] == [49, 51, 51, 51, 51, 49]
