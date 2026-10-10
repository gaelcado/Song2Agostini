"""Serialize MuseScore exports and retry only its intermittent native abort."""
import os
import time
from contextlib import contextmanager
import subprocess
from .processes import run_external
from pathlib import Path
from .files import ROOT


@contextmanager
def exclusive_lock(path):
    """OS releases this lock on crash, on Windows and POSIX alike."""
    with Path(path).open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0, 2)
            if not handle.tell():
                handle.write(b'0'); handle.flush()
            while True:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    if error.errno not in (13, 36):
                        raise
                    time.sleep(.1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def render(command,env,out):
    # The desktop's Qt runtime must not replace MuseScore's own Qt plugins.
    env = dict(env)
    for key in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QTWEBENGINEPROCESS_PATH',
                'QTWEBENGINE_RESOURCES_PATH', 'QTWEBENGINE_LOCALES_PATH',
                'QML2_IMPORT_PATH', 'QML_IMPORT_PATH'):
        env.pop(key, None)
    lock=ROOT/'work/locks/musescore.lock';lock.parent.mkdir(parents=True,exist_ok=True)
    out=Path(out)
    with exclusive_lock(lock):
        for attempt in range(1,4):
            with (out/f'engraving-attempt-{attempt}.log').open('w') as log:
                result=run_external(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            (out/'engraving.log').write_bytes((out/f'engraving-attempt-{attempt}.log').read_bytes())
            if result.returncode==0:return attempt
            if result.returncode!=-6 or attempt==3:
                raise subprocess.CalledProcessError(result.returncode,command)
        raise RuntimeError('Rendu indisponible')
