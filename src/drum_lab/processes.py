"""Launch external tools without inheriting a frozen application's DLL search path."""
from contextlib import contextmanager
import ctypes
import os
import subprocess
import sys
import threading

_DLL_LOCK = threading.RLock()


def _windows_dll_api():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetDllDirectoryW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p]
    kernel.GetDllDirectoryW.restype = ctypes.c_uint32
    kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
    kernel.SetDllDirectoryW.restype = ctypes.c_int
    return kernel


@contextmanager
def external_dll_search():
    """Restore the parent immediately after process creation, including failures."""
    with _DLL_LOCK:
        api = _windows_dll_api()
        size = api.GetDllDirectoryW(0, None)
        buffer = ctypes.create_unicode_buffer(size + 1)
        api.GetDllDirectoryW(len(buffer), buffer)
        previous = buffer.value or None
        if not api.SetDllDirectoryW(None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            if not api.SetDllDirectoryW(previous):
                raise ctypes.WinError(ctypes.get_last_error())


def run_external(*args, input=None, capture_output=False, timeout=None, check=False, **kwargs):
    """subprocess.run contract; Windows frozen DLL isolation lasts only for Popen."""
    env = dict(kwargs.get('env') or os.environ)
    if getattr(sys, 'frozen', False):
        for key in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QTWEBENGINEPROCESS_PATH',
                    'QTWEBENGINE_RESOURCES_PATH', 'QTWEBENGINE_LOCALES_PATH',
                    'QML2_IMPORT_PATH', 'QML_IMPORT_PATH'):
            env.pop(key, None)
        if 'LD_LIBRARY_PATH_ORIG' in env:
            env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
        else:
            env.pop('LD_LIBRARY_PATH', None)
    kwargs['env'] = env
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return subprocess.run(*args, input=input, capture_output=capture_output,
                              timeout=timeout, check=check, **kwargs)
    if input is not None:
        if kwargs.get('stdin') is not None:
            raise ValueError('stdin and input arguments may not both be used')
        kwargs['stdin'] = subprocess.PIPE
    if capture_output:
        if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:
            raise ValueError('stdout and stderr arguments may not be used with capture_output')
        kwargs['stdout'] = kwargs['stderr'] = subprocess.PIPE
    with external_dll_search():
        process = subprocess.Popen(*args, **kwargs)
    with process:
        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            process.kill()
            error.stdout, error.stderr = process.communicate()
            raise
        except BaseException:
            process.kill()
            process.wait()
            raise
        code = process.poll()
        if check and code:
            raise subprocess.CalledProcessError(code, process.args, output=stdout, stderr=stderr)
        return subprocess.CompletedProcess(process.args, code, stdout, stderr)
