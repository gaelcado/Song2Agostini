"""Writable application paths and immutable resources, for source and desktop builds."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def application_home(*, frozen=None, platform=None, environ=None):
    environ = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    frozen = getattr(sys, 'frozen', False) if frozen is None else frozen
    if environ.get('DRUM_LAB_HOME'):
        return Path(environ['DRUM_LAB_HOME']).expanduser().resolve()
    source = Path(__file__).resolve().parents[2]
    if not frozen and (source/'pyproject.toml').is_file():
        return source
    home = Path(environ.get('HOME') or environ.get('USERPROFILE') or Path.home())
    if platform == 'win32':
        return Path(environ.get('LOCALAPPDATA', home/'AppData/Local'))/'DrumLab'
    if platform == 'darwin':
        return home/'Library/Application Support/DrumLab'
    return Path(environ.get('XDG_DATA_HOME', home/'.local/share'))/'drum-lab'


ROOT = application_home()
def resource_home():
    if os.environ.get('DRUM_LAB_RESOURCE_ROOT'):
        return Path(os.environ['DRUM_LAB_RESOURCE_ROOT'])
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    source = Path(__file__).resolve().parents[2]
    if (source/'pyproject.toml').is_file():
        return source
    return Path(sys.prefix)/'share/drum-lab'


RESOURCE_ROOT = resource_home()


def resource_path(relative):
    return RESOURCE_ROOT/relative


def source_file(module_file):
    path = Path(module_file)
    return path if path.is_file() else resource_path('src/drum_lab')/path.with_suffix('.py').name


def runtime_root():
    if os.environ.get('DRUM_LAB_RUNTIME_ROOT'):
        return Path(os.environ['DRUM_LAB_RUNTIME_ROOT'])
    # bootstrap installs a wheel in <runtime>/envs/app; launchers need no shell setup.
    prefix = Path(sys.prefix)
    if prefix.name == 'app' and prefix.parent.name == 'envs':
        return prefix.parent.parent
    return ROOT/'work'


def env_python(name, *, platform=None):
    platform = sys.platform if platform is None else platform
    executable = runtime_root()/'workers'/name/(name+'.exe' if platform == 'win32' else name)
    if executable.is_file():
        return executable
    base = runtime_root()/'envs'/name
    return base/('Scripts/python.exe' if platform == 'win32' else 'bin/python')


def worker_path(name):
    return resource_path('scripts')/name


def find_tool(name):
    override = os.environ.get('DRUM_LAB_'+name.upper()) or (os.environ.get('MUSESCORE_EXECUTABLE') if name == 'musescore' else None)
    if override:
        path = Path(override)
        return str(path) if path.is_file() else None
    tools = runtime_root()/'tools'
    names = [name, name+'.exe']
    if name == 'musescore':
        names += ['mscore', 'musescore3', 'musescore4', 'MuseScore4.exe', 'MuseScore 4/bin/MuseScore4.exe',
                  'MuseScore 4.app/Contents/MacOS/mscore']
    candidates = [tools/n for n in names]
    if name == 'musescore' and sys.platform == 'darwin':
        candidates += [Path('/Applications/MuseScore 4.app/Contents/MacOS/mscore')]
    return next((str(p) for p in candidates if p.is_file()), None) or next(
        (found for n in names if '/' not in n and (found := shutil.which(n))), None)


def worker_environment():
    env = dict(os.environ, DRUM_LAB_HOME=str(ROOT), DRUM_LAB_RESOURCE_ROOT=str(RESOURCE_ROOT),
               DRUM_LAB_RUNTIME_ROOT=str(runtime_root()))
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(resource_path('src')), env.get('PYTHONPATH')]))
    env['PATH'] = str(runtime_root()/'tools') + os.pathsep + env.get('PATH', '')
    for name in ('ffmpeg', 'ffprobe'):
        tool = find_tool(name)
        if tool:
            env['DRUM_LAB_'+name.upper()] = tool
    return env


def installed_package_path(environment, package, *, weights=False):
    """Ask the isolated interpreter; wheels/editable installs differ across platforms."""
    code = (f'import {package} as package; print(package.get_default_weights_path())' if weights else
            f'import importlib.util; print(next(iter(importlib.util.find_spec({package!r}).submodule_search_locations)))')
    result = subprocess.run([str(env_python(environment)), '-c', code], check=True,
                            capture_output=True, text=True, timeout=60, env=worker_environment())
    return Path(result.stdout.strip().splitlines()[-1])


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
