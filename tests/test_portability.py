"""Path contracts only: these tests do not claim a native Windows engine run."""
from pathlib import Path
import importlib.util
import sys
from types import SimpleNamespace

from drum_lab import files


def test_windows_writable_home_is_separate_from_bundle():
    result = files.application_home(frozen=True, platform='win32',
                                    environ={'LOCALAPPDATA':'C:/Users/Learner/AppData/Local'})
    assert result == Path('C:/Users/Learner/AppData/Local/DrumLab')


def test_mac_writable_home():
    assert files.application_home(frozen=True, platform='darwin', environ={'HOME':'/Users/learner'}) == Path('/Users/learner/Library/Application Support/DrumLab')


def test_home_override(tmp_path):
    assert files.application_home(frozen=True, environ={'DRUM_LAB_HOME':str(tmp_path)}) == tmp_path.resolve()


def test_runtime_interpreters(tmp_path, monkeypatch):
    monkeypatch.setenv('DRUM_LAB_RUNTIME_ROOT', str(tmp_path))
    assert files.env_python('adtof', platform='win32') == tmp_path/'envs/adtof/Scripts/python.exe'
    assert files.env_python('beat_this', platform='darwin') == tmp_path/'envs/beat_this/bin/python'


def test_bundled_tools_take_priority(tmp_path, monkeypatch):
    monkeypatch.setenv('DRUM_LAB_RUNTIME_ROOT', str(tmp_path))
    (tmp_path/'tools').mkdir()
    tool = tmp_path/'tools/MuseScore4.exe'; tool.touch()
    monkeypatch.delenv('DRUM_LAB_MUSESCORE', raising=False)
    monkeypatch.delenv('MUSESCORE_EXECUTABLE', raising=False)
    assert files.find_tool('musescore') == str(tool)


def test_utf8_roundtrip(tmp_path):
    target = tmp_path/'écriture.json'
    files.write(target, {'titre':'Élève — batterie 🥁'})
    assert files.load(target)['titre'] == 'Élève — batterie 🥁'


def test_package_weights_queried_in_engine_interpreter(tmp_path, monkeypatch):
    monkeypatch.setenv('DRUM_LAB_RUNTIME_ROOT', str(tmp_path))
    calls=[]
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout=str(tmp_path/'poids.pth')+'\n')
    monkeypatch.setattr(files.subprocess, 'run', run)
    assert files.installed_package_path('adtof','adtof_pytorch',weights=True) == tmp_path/'poids.pth'
    assert calls[0][0][0] == str(files.env_python('adtof'))
    assert 'get_default_weights_path()' in calls[0][0][2]


def test_windows_lock_protocol(tmp_path, monkeypatch):
    import drum_lab.rendering as rendering
    calls=[]
    fake = SimpleNamespace(LK_NBLCK=1,LK_UNLCK=2,locking=lambda fd, mode, count:calls.append((mode,count)))
    # Replace only rendering's os binding, without changing pathlib's host platform.
    monkeypatch.setattr(rendering, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setitem(sys.modules, 'msvcrt', fake)
    with rendering.exclusive_lock(tmp_path/'render.lock'):
        assert calls == [(1,1)]
    assert calls == [(1,1),(2,1)]


def test_frozen_worker_discovered(tmp_path, monkeypatch):
    monkeypatch.setenv('DRUM_LAB_RUNTIME_ROOT',str(tmp_path))
    worker=tmp_path/'workers/adtof/adtof.exe';worker.parent.mkdir(parents=True);worker.touch()
    assert files.env_python('adtof',platform='win32') == worker


def test_installed_wheel_uses_shared_resources_and_user_home(tmp_path, monkeypatch):
    monkeypatch.setattr(files, '__file__', str(tmp_path/'lib/site-packages/drum_lab/files.py'))
    monkeypatch.setattr(files.sys, 'prefix', str(tmp_path/'prefix'))
    monkeypatch.delenv('DRUM_LAB_RESOURCE_ROOT', raising=False)
    monkeypatch.delattr(files.sys, '_MEIPASS', raising=False)
    assert files.resource_home() == tmp_path/'prefix/share/drum-lab'
    assert files.application_home(frozen=False, platform='darwin', environ={'HOME':'/Users/learner'}) == Path('/Users/learner/Library/Application Support/DrumLab')
