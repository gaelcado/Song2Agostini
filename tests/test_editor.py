from pathlib import Path
import pytest
from drum_lab import editor


def test_macos_prefers_installed_four_then_three(monkeypatch, tmp_path):
    monkeypatch.setattr(editor.sys, 'platform', 'darwin')
    monkeypatch.setattr(Path, 'is_dir', lambda p: str(p) in {'/Applications/MuseScore 3.app', '/Applications/MuseScore 4.app'})
    assert editor.editor_command(tmp_path/'score.musicxml')[2] == '/Applications/MuseScore 4.app'
    monkeypatch.setattr(Path, 'is_dir', lambda p: str(p) == '/Applications/MuseScore 3.app')
    assert editor.editor_command(tmp_path/'score.musicxml')[2] == '/Applications/MuseScore 3.app'


def test_linux_missing_editor_and_explicit_command(monkeypatch, tmp_path):
    monkeypatch.setattr(editor.sys, 'platform', 'linux')
    monkeypatch.setattr(editor.shutil, 'which', lambda name: None)
    monkeypatch.setattr(editor, 'find_tool', lambda name: None)
    with pytest.raises(FileNotFoundError, match='MuseScore 3 ou 4'):
        editor.editor_command(tmp_path/'score.musicxml')
    monkeypatch.setattr(editor.shutil, 'which', lambda name: '/usr/bin/musescore3' if name == 'musescore3' else None)
    score = tmp_path/'notes ; $(test).musicxml'
    assert editor.editor_command(score) == ['/usr/bin/musescore3', str(score)]


def test_windows_install_with_spaces(monkeypatch, tmp_path):
    monkeypatch.setattr(editor.sys, 'platform', 'win32')
    monkeypatch.setenv('ProgramW6432', str(tmp_path/'Program Files'))
    exe = tmp_path/'Program Files/MuseScore 4/bin/MuseScore4.exe'
    exe.parent.mkdir(parents=True); exe.touch()
    assert editor.editor_command(tmp_path/'score.musicxml') == [str(exe), str(tmp_path/'score.musicxml')]
