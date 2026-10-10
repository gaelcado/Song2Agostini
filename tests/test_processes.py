import subprocess
from types import SimpleNamespace
import pytest
from drum_lab import processes


class Kernel:
    def __init__(self): self.calls=[]
    def GetDllDirectoryW(self, size, buffer):
        if buffer is not None: buffer.value = 'C:/frozen/internal'
        return 20
    def SetDllDirectoryW(self, path): self.calls.append(path);return 1


def test_dll_search_restored_on_spawn_failure(monkeypatch):
    kernel=Kernel();monkeypatch.setattr(processes,'_windows_dll_api',lambda:kernel)
    with pytest.raises(OSError):
        with processes.external_dll_search():
            assert kernel.calls == [None]
            raise OSError('spawn failed')
    assert kernel.calls == [None,'C:/frozen/internal']


def test_windows_restores_search_before_waiting(monkeypatch):
    kernel=Kernel();monkeypatch.setattr(processes,'_windows_dll_api',lambda:kernel)
    monkeypatch.setattr(processes.sys,'platform','win32')
    monkeypatch.setattr(processes.sys,'frozen',True,raising=False)
    class Process:
        args=['tool']
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def communicate(self,*args,**kwargs):
            assert kernel.calls == [None,'C:/frozen/internal']
            return b'ok',b''
        def poll(self):return 0
    def spawn(*args,**kwargs):
        assert kernel.calls == [None]
        assert kwargs['stdout'] == subprocess.PIPE
        assert 'QT_PLUGIN_PATH' not in kwargs['env']
        return Process()
    monkeypatch.setattr(processes.subprocess,'Popen',spawn)
    result=processes.run_external(['tool'],capture_output=True,env={'QT_PLUGIN_PATH':'bundled'},check=True)
    assert result.stdout == b'ok'


def test_source_launch_keeps_run_contract(monkeypatch):
    monkeypatch.setattr(processes.sys,'frozen',False,raising=False)
    calls=[]
    monkeypatch.setattr(processes.subprocess,'run',lambda *a,**k:calls.append((a,k)))
    processes.run_external(['ffprobe'],timeout=30,capture_output=True,text=True,check=True)
    assert calls[0][1]['check'] and calls[0][1]['text']
