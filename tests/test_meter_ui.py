import json
from drum_lab.ui import summarize


def test_compound_tempo_is_displayed_in_dotted_quarters(tmp_path):
    (tmp_path / 'grid.json').write_text(json.dumps({
        'bpm': 120, 'pulse_quarter_length': 1.5, 'time_signature': '12/8',
        'meter_evidence': {'status': 'abstained', 'private_detail': '/not/public'},
    }))
    detail = summarize(tmp_path, {})
    assert detail['tempo_bpm'] == 80
    assert detail['tempo_unit'] == 'noire pointée'
    assert detail['time_signature'] == '12/8'
    assert detail['meter_status'] == 'incertain'
    assert 'private_detail' not in detail
