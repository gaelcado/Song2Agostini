"""Synthetic checks for audio-only user registration and preflight budget."""
import importlib.util
import json
from pathlib import Path
import pytest
from drum_lab.files import digest
from drum_lab.pieces import USER_IDS, RUN_IDS, registered_audio

spec = importlib.util.spec_from_file_location('process_user_inputs', Path(__file__).resolve().parents[1] / 'lab/scripts/process_user_inputs.py')
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


def make_manifest(root, count=5):
    rows = []
    for piece in USER_IDS[:count]:
        audio = root / 'data/raw/audio' / (piece + '.wav')
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(piece.encode())
        rows.append({'id': piece, 'audio': str(audio.relative_to(root)),
                     'audio_sha256': digest(audio), 'title': 'Titre ' + piece})
    manifest = root / 'data/new-input-research-manifest.json'
    manifest.write_text(json.dumps({'pieces': rows}))
    return rows, manifest


def test_user_registration_checks_identity_and_hash(tmp_path):
    rows, _ = make_manifest(tmp_path)
    audio = tmp_path / rows[0]['audio']
    assert set(USER_IDS).issubset(RUN_IDS)
    assert registered_audio('user_01', audio, tmp_path)['title'] == 'Titre user_01'
    with pytest.raises(ValueError, match='différent'):
        registered_audio('user_01', tmp_path / rows[1]['audio'], tmp_path)
    audio.write_bytes(b'changed')
    with pytest.raises(ValueError, match='modifié'):
        registered_audio('user_01', audio, tmp_path)


def test_batch_rejects_reference_fields_and_repeated_baseline(tmp_path, monkeypatch):
    rows, manifest = make_manifest(tmp_path)
    monkeypatch.setattr(batch, 'probe_audio', lambda _: {'format': {'duration': '100'}})
    assert len(batch.preflight(tmp_path)) == 5
    rows[0]['score'] = 'forbidden.pdf'
    manifest.write_text(json.dumps({'pieces': rows}))
    with pytest.raises(ValueError, match='non autorisés'):
        batch.preflight(tmp_path)
    rows[0].pop('score')
    manifest.write_text(json.dumps({'pieces': rows}))
    record = tmp_path / 'work/runs/old/record.json'
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({'piece_id': 'user_05'}))
    with pytest.raises(ValueError, match='déjà entamée'):
        batch.preflight(tmp_path)


def test_batch_checks_cumulative_audio_budget_and_all_hashes(tmp_path, monkeypatch):
    rows, _ = make_manifest(tmp_path)
    monkeypatch.setattr(batch, 'probe_audio', lambda _: {'format': {'duration': '1500'}})
    with pytest.raises(ValueError, match='Budget'):
        batch.preflight(tmp_path)
    monkeypatch.setattr(batch, 'probe_audio', lambda _: {'format': {'duration': '100'}})
    (tmp_path / rows[-1]['audio']).write_bytes(b'changed last audio')
    with pytest.raises(ValueError, match='modifié'):
        batch.preflight(tmp_path)


@pytest.mark.parametrize('count', [1, 10])
def test_batch_accepts_bounded_subset(tmp_path, monkeypatch, count):
    make_manifest(tmp_path, count=count)
    monkeypatch.setattr(batch, 'probe_audio', lambda _: {'format': {'duration': '100'}})
    assert len(batch.preflight(tmp_path)) == count


def test_batch_rejects_empty_duplicate_and_unknown_ids(tmp_path, monkeypatch):
    rows, manifest = make_manifest(tmp_path)
    monkeypatch.setattr(batch, 'probe_audio', lambda _: pytest.fail('No probing before ID validation'))
    for invalid in ([], [rows[0], rows[0]], [{**rows[0], 'id': 'piece_01'}]):
        manifest.write_text(json.dumps({'pieces': invalid}))
        with pytest.raises(ValueError):
            batch.preflight(tmp_path)


def test_user_title_matches_audio_hash(tmp_path, monkeypatch):
    import drum_lab.titles as titles
    rows, _ = make_manifest(tmp_path)
    monkeypatch.setattr(titles, 'ROOT', tmp_path)
    audio = tmp_path / rows[0]['audio']
    assert titles.audio_title(audio) == 'Titre user_01'
    unrelated = audio.with_name('other.wav')
    unrelated.write_bytes(b'unrelated audio')
    assert titles.audio_title(unrelated, filename='Part 1.mp3') == 'Part 1'


def previous_failed(root, row):
    record = root / 'work/runs/failed-old/record.json'
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({'id': 'failed-old', 'piece_id': row['id'],
                                 'status': 'failed', 'audio_sha256': 'old-audio-hash',
                                 'config': batch.PROFILE}))
    return record


def test_input_replacement_requires_failed_same_piece_new_hash_and_profile(tmp_path, monkeypatch):
    rows, _ = make_manifest(tmp_path)
    monkeypatch.setattr(batch, 'probe_audio', lambda _: {'format': {'duration': '100'}})
    path = previous_failed(tmp_path, rows[0])
    record = json.loads(path.read_text())
    assert len(batch.preflight(tmp_path, only=['user_01'], replacement_run='failed-old')) == 1
    for changed in ({'status': 'completed'}, {'piece_id': 'user_02'},
                    {'audio_sha256': rows[0]['audio_sha256']},
                    {'config': {**batch.PROFILE, 'compact': False}}):
        path.write_text(json.dumps({**record, **changed}))
        with pytest.raises(ValueError):
            batch.preflight(tmp_path, only=['user_01'], replacement_run='failed-old')
    path.write_text(json.dumps(record))
    second = path.parent.with_name('second') / 'record.json'
    second.parent.mkdir()
    second.write_text(json.dumps({**record, 'id': 'second'}))
    with pytest.raises(ValueError, match='unique'):
        batch.preflight(tmp_path, only=['user_01'], replacement_run='failed-old')


def test_input_replacement_requires_single_explicit_safe_selection(tmp_path, monkeypatch):
    rows, _ = make_manifest(tmp_path)
    previous_failed(tmp_path, rows[0])
    monkeypatch.setattr(batch, 'probe_audio', lambda _: {'format': {'duration': '100'}})
    for selected, run_id in ((None, 'failed-old'), (['user_01', 'user_02'], 'failed-old'),
                             (['user_01'], '../failed-old'), (['user_01'], 'missing')):
        with pytest.raises(ValueError):
            batch.preflight(tmp_path, only=selected, replacement_run=run_id)
