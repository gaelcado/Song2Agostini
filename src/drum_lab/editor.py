"""Open a generated MusicXML in a locally installed MuseScore editor."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .files import find_tool


def editor_command(score):
    score = str(Path(score).resolve())
    if sys.platform == 'darwin':
        for version in (4, 3):
            for directory in (Path('/Applications'), Path.home() / 'Applications'):
                for name in (f'MuseScore {version}.app', f'MuseScore Studio {version}.app'):
                    app = directory / name
                    if app.is_dir():
                        return ['/usr/bin/open', '-a', str(app), score]
    elif sys.platform == 'win32':
        for version in (4, 3):
            for variable in ('ProgramW6432', 'ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
                base = os.environ.get(variable)
                if base:
                    for folder in (f'MuseScore {version}', f'Programs/MuseScore {version}'):
                        executable = Path(base) / folder / 'bin' / f'MuseScore{version}.exe'
                        if executable.is_file():
                            return [str(executable), score]
    for name in ('musescore4', 'MuseScore4', 'musescore3', 'MuseScore3', 'mscore'):
        executable = shutil.which(name)
        if executable:
            return [executable, score]
    # The desktop distribution may ship the full editor with its renderer.
    executable = find_tool('musescore')
    if executable:
        if sys.platform == 'darwin':
            app = next((p for p in Path(executable).parents if p.suffix == '.app'), None)
            if app:
                return ['/usr/bin/open', '-a', str(app), score]
        return [executable, score]
    raise FileNotFoundError('MuseScore 3 ou 4 est introuvable. Installez-le, ou téléchargez le MusicXML pour l’ouvrir manuellement.')


def open_score(score):
    command = editor_command(score)
    if command[0] == '/usr/bin/open':
        subprocess.run(command, check=True, capture_output=True, timeout=15)
    else:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        # Reap the editor when it exits, without holding the HTTP request open.
        import threading
        threading.Thread(target=process.wait, daemon=True).start()
