import copy
import inspect
import json
import pytest

from drum_lab.evaluation import evaluate
from drum_lab.runner import run
from drum_lab.verification import feedback, verify_run
from test_evaluation import doc


def test_research_entry_has_no_reference():
    assert 'reference' not in inspect.signature(run).parameters
    source = inspect.getsource(run)
    assert 'evaluate(' not in source
    assert 'reference_sha256' not in source


def test_feedback_does_not_return_reference_events():
    report = evaluate(doc('reference', [(1.12345, 'kick'), (3.87654, 'snare')]),
                      doc('prediction', [(1.12, 'kick'), (6.11111, 'toms')]))
    original = copy.deepcopy(report)
    # Unexpected data in a private report must not leak via a copy operation.
    report['reference_secret'] = 'do not return'
    report['tolerances']['50']['per_class']['kick']['expected_notes'] = [1.12345]
    public = feedback(report)
    encoded = json.dumps(public)
    for forbidden in ('false_negative', 'false_positive', 'matched_distances_ms',
                      'reference_secret', 'expected_notes', '1.12345', '3.87654'):
        assert forbidden not in encoded
    assert public['tolerances']['50']['per_class']['snare']['fn'] == 1
    assert report['tolerances']['25'] == original['tolerances']['25']


def test_verification_keeps_detailed_report_private(tmp_path, monkeypatch):
    import drum_lab.verification as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    (tmp_path / 'configs').mkdir()
    (tmp_path / 'configs/evaluation.v2.json').write_text('{}')
    out = tmp_path / 'research/trial'
    out.mkdir(parents=True)
    reference = tmp_path / 'reference.json'
    reference.write_text(json.dumps(doc('reference', [(1.23456, 'kick')])))
    (out / 'events.json').write_text(json.dumps(doc('prediction', [])))
    (out / 'record.json').write_text(json.dumps({'piece_id': 'synthetic'}))
    before = (out / 'events.json').read_bytes()
    result = verify_run(reference, out)
    assert (out / 'events.json').read_bytes() == before
    assert not (out / 'metrics.json').exists()
    assert '1.23456' not in json.dumps(result)
    private = json.loads((tmp_path / 'work/verification/trial/metrics.json').read_text())
    assert private['tolerances']['50']['errors']['kick']['false_negative'][0]['time'] == 1.23456
    assert json.loads((out / 'feedback.json').read_text()) == result


def test_cli_verification_error_does_not_print_reference(tmp_path, monkeypatch, capsys):
    import drum_lab.cli as cli
    import sys
    reference = tmp_path / 'reference.json'
    reference.write_text(json.dumps(doc('reference', [(-1.987654, 'kick')])))
    prediction = tmp_path / 'prediction.json'
    prediction.write_text(json.dumps(doc('prediction', [])))
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['drum-lab', 'evaluate', str(reference), str(prediction)])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    output = capsys.readouterr()
    assert '1.987654' not in output.err + output.out
    logs = list((tmp_path / 'work/verification/errors').glob('*.log'))
    assert len(logs) == 1 and '1.987654' in logs[0].read_text()
