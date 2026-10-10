from types import SimpleNamespace
from pathlib import Path
import pytest
from drum_lab.rendering import render


def test_abort_retry_is_bounded_and_logged(tmp_path,monkeypatch):
    import drum_lab.rendering as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    results=iter([-6,0]);calls=[]
    def command(*args,**kwargs):
        calls.append(args);return SimpleNamespace(returncode=next(results))
    monkeypatch.setattr(module.subprocess,'run',command)
    assert render(['mscore'],{},tmp_path)==2
    assert len(calls)==2 and (tmp_path/'engraving-attempt-1.log').exists()


def test_does_not_retry_input_error(tmp_path,monkeypatch):
    import drum_lab.rendering as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1))
    with pytest.raises(module.subprocess.CalledProcessError):render(['mscore'],{},tmp_path)
    assert not (tmp_path/'engraving-attempt-2.log').exists()
