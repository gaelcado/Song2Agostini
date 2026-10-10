import pretty_midi
import pytest
from drum_lab.quantization import quantize_hits


def hit(t,p=36): return pretty_midi.Note(90,p,t,t+.1)


def test_origin_keeps_tracked_phase_no_fictitious_zero():
    mapped,to_beat,to_seconds,q=quantize_hits([hit(1.2),hit(1.45)],{'bpm':120,'origin_seconds':1.2,'beat_times_seconds':[1.2,1.7,2.2]})
    assert [slot for n,slot,t in mapped]==[0,2]
    assert mapped[0][2]==pytest.approx(1.2)
    assert q['max_shift_ms']==pytest.approx(0)


def test_collision_and_shift_are_reported_without_deleting_hits():
    mapped,_,_,q=quantize_hits([hit(.061),hit(.062)],{'bpm':120})
    assert len(mapped)==2 and q['collision_count']==1
    assert q['large_shift_count']==2
    assert q['max_shift_ms']==pytest.approx(62)


def test_pickup_retains_phase_and_positive_audio():
    mapped,_,_,q=quantize_hits([hit(.95),hit(1.2)],{'bpm':120,'origin_seconds':1.2,'beat_times_seconds':[1.2,1.7,2.2]})
    assert q['pickup_prepend_measures']==1
    assert mapped[0][1]==14 and mapped[1][1]==16
    assert mapped[0][2]==pytest.approx(.95)


def test_silence_gap_does_not_slow_grid():
    mapped,to_beat,_,q=quantize_hits([hit(3.)],{'bpm':120,'origin_seconds':0,'beat_times_seconds':[0,.5,1,3,3.5]})
    assert to_beat(3.)==6
    assert mapped[0][1]==24 and q['max_shift_ms']==0


def test_pickup_before_sparse_first_gap_uses_quarter_interval():
    mapped,to_beat,to_seconds,q=quantize_hits([hit(.75),hit(1)],
        {'bpm':120,'origin_seconds':1,'beat_times_seconds':[1,3,3.5,4,4.5]})
    assert [slot for _,slot,_ in mapped]==[14,16]
    assert to_beat(.75)==pytest.approx(3.5)
    assert to_seconds(3.5)==pytest.approx(.75)
    assert q['max_shift_ms']==pytest.approx(0)


def test_trailing_extrapolation_uses_local_edge_tempo():
    mapped,_,to_seconds,q=quantize_hits([hit(2.85)],
        {'bpm':120,'beat_times_seconds':[0,.5,1,1.5,2.1,2.7]})
    assert mapped[0][1]==21
    assert to_seconds(5.25)==pytest.approx(2.85)
    assert q['max_shift_ms']==pytest.approx(0)


@pytest.mark.parametrize('grid',[{'bpm':0},{'bpm':float('nan')},{'bpm':120,'origin_seconds':-1}])
def test_invalid_grid_rejected(grid):
    with pytest.raises(ValueError,match='Grille'): quantize_hits([hit(1)],grid)


def test_empty_hits_rejected_explicitly():
    with pytest.raises(ValueError,match='Aucun coup'): quantize_hits([],{'bpm':120})
