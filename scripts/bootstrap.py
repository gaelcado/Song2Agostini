#!/usr/bin/env python3
"""Installation source isolée. Aucun audio, référence, ni installation globale."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import tempfile
import zipfile
import urllib.request

SOURCE = Path(__file__).resolve().parents[1]

def configure_output():
    # Windows shells may default to cp1252; all diagnostic files are UTF-8.
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf-8',errors='backslashreplace')

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def python_at(runtime, name):
    return runtime / 'envs' / name / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')

def execute(command, log):
    print('→ ' + subprocess.list2cmdline(list(map(str, command))), flush=True)
    with log.open('a', encoding='utf-8') as stream:
        subprocess.run(list(map(str, command)), check=True, stdout=stream, stderr=subprocess.STDOUT)

def download(url, target, expected):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(target) != expected:
            raise RuntimeError(f'Hash invalide : {target}; fichier conservé pour diagnostic')
        return
    partial = target.with_suffix(target.suffix + '.download')
    try:
        urllib.request.urlretrieve(url, partial)
        if sha256(partial) != expected:
            raise RuntimeError(f'Hash du téléchargement invalide : {target}')
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)

def find_tool(runtime, name):
    candidates = [runtime/'tools'/name, runtime/'tools'/(name+'.exe')]
    if name == 'musescore':
        candidates += [runtime/'tools/MuseScore4.exe', runtime/'tools/MuseScore 4/bin/MuseScore4.exe',
                       runtime/'tools/MuseScore 4.app/Contents/MacOS/mscore']
        for command in ('MuseScore4.exe','mscore','musescore','musescore4'):
            path = shutil.which(command)
            if path:
                return path
    return next((str(p) for p in candidates if p.is_file()), shutil.which(name))

def doctor(source, runtime, engines, config, desktop=False):
    report = {'schema_version':1,'platform':platform.platform(),'python':platform.python_version(),
              'runtime_root':str(runtime),'engines':{},'tools':{}}
    for engine in engines:
        py = python_at(runtime, engine)
        lock_name = 'beat-this' if engine == 'beat_this' else engine
        status = {'python':str(py),'installed':py.is_file(),
                  'lock_sha256':sha256(source/'configs/install'/f'{lock_name}.txt')}
        if py.is_file():
            module = {'app':'drum_lab','adtof':'adtof_pytorch','demucs':'demucs','beat_this':'beat_this'}[engine]
            imports=f'import {module}; print("ok")'
            if engine=='app' and desktop:
                imports+='; import PySide6.QtCore; import PySide6.QtWidgets; import drum_lab.desktop'
            check = subprocess.run([str(py),'-c',imports], capture_output=True, text=True, timeout=120)
            status.update(import_ok=check.returncode == 0, error=check.stderr[-2000:] if check.returncode else None)
            uv=shutil.which('uv')
            pipcheck=subprocess.run([uv,'pip','check','--python',str(py)] if uv else [str(py),'-m','pip','check'],capture_output=True,text=True,timeout=120)
            status.update(dependencies_ok=pipcheck.returncode==0,dependency_diagnostic=(pipcheck.stdout+pipcheck.stderr)[-3000:])
            status['import_ok']=status['import_ok'] and status['dependencies_ok']
            metadata_code="import importlib.metadata as m,json; print(json.dumps([{'name':d.metadata.get('Name'),'version':d.version,'license_expression':d.metadata.get('License-Expression'),'license_declaration':d.metadata.get('License'),'license_files':[str(f) for f in (d.files or []) if 'license' in str(f).lower() or 'copying' in str(f).lower()],'status':'metadata_declaration_only'} for d in m.distributions()]))"
            metadata=subprocess.run([str(py),'-c',metadata_code],capture_output=True,text=True,timeout=120)
            status['distributions']=json.loads(metadata.stdout) if metadata.returncode==0 else []
        report['engines'][engine] = status
    for tool in ('ffmpeg','musescore'):
        path = find_tool(runtime, tool)
        report['tools'][tool] = {'path':path,'available':bool(path)}
    report['models'] = {}
    if 'adtof' in engines:
        entry=config['repositories']['adtof']; p=runtime/'vendor/adtof'/entry['weights_path']
        actual=sha256(p) if p.is_file() else None
        report['models']['adtof']={'verified':actual==entry['weights_sha256'],'sha256':actual,'expected_sha256':entry['weights_sha256']}
    for engine, entry in config['weights'].items():
        if engine in engines:
            spec=json.loads((source/entry['config']).read_text()); p=runtime/entry['target']
            actual=sha256(p) if p.is_file() else None
            report['models'][engine]={'verified':actual==spec['sha256'],'sha256':actual,'expected_sha256':spec['sha256'],'url':spec['url']}
    report['ready'] = all(x.get('import_ok',False) for x in report['engines'].values())
    if len(engines)>1:
        report['ready'] = report['ready'] and all(x['verified'] for x in report['models'].values()) and all(x['available'] for x in report['tools'].values())
    return report

def main():
    configure_output()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=SOURCE)
    parser.add_argument('--runtime-root',type=Path)
    parser.add_argument('--only',choices=['app','all'],default='all')
    parser.add_argument('--desktop',action='store_true',help='Installe également la fenêtre native PySide6 dans envs/app')
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--allow-missing-tools',action='store_true',help='Installation CI moteurs seule; rendu indisponible reste explicite')
    args=parser.parse_args()
    source=args.source_root.resolve(); runtime=(args.runtime_root or source/'work').resolve()
    config=json.loads((source/'configs/install/runtime.json').read_text())
    engines=['app'] if args.only=='app' else config['environments']
    if args.check:
        result=doctor(source,runtime,engines,config,args.desktop); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['ready'] or (args.allow_missing_tools and all(e.get('import_ok') for e in result['engines'].values()) and all(m['verified'] for m in result['models'].values())) else 1
    if args.dry_run:
        print(json.dumps({'source_root':str(source),'runtime_root':str(runtime),'engines':engines,
                         'downloads':config['repositories'] if args.only=='all' else {},
                         'weights':config['weights'] if args.only=='all' else {},'licenses':config['licenses'],'desktop':args.desktop,
                         'policy':config['dependencies_policy'],'global_changes':False},ensure_ascii=False,indent=2)); return 0
    if sys.version_info[:2]!=(3,11):
        parser.error('Python 3.11 requis. Avec uv : uv run --python 3.11 --no-project scripts/bootstrap.py')
    uv=shutil.which('uv')
    if args.only=='all' and not shutil.which('git'):
        parser.error('Git requis pour récupérer et vérifier les deux commits moteurs.')
    runtime.mkdir(parents=True,exist_ok=True); log=runtime/'bootstrap.log'
    started=time.monotonic()
    for engine in engines:
        py=python_at(runtime,engine); env=py.parent.parent
        if not py.exists():
            execute([uv,'venv','--python',sys.executable,str(env)] if uv else [sys.executable,'-m','venv',str(env)],log)
        lock=source/'configs/install'/('beat-this.txt' if engine=='beat_this' else f'{engine}.txt')
        base=[uv,'pip','install','--python',str(py)] if uv else [str(py),'-m','pip','install']
        # Complete pinned closure; no resolver upgrades hidden behind engine metadata.
        if engine != 'app' and sys.platform in ('linux','win32'):
            # Official CPU wheels avoid unnecessary CUDA downloads on Linux.
            wheels=['torch==2.11.0+cpu']
            if engine in ('demucs','beat_this'):
                wheels.append('torchaudio==2.11.0+cpu')
            execute(base+['--no-deps','--index-url','https://download.pytorch.org/whl/cpu']+wheels,log)
        execute(base+['--no-deps','-r',str(lock)],log)
        if engine=='app':
            if args.desktop:
                execute(base+['--no-deps','-r',str(source/'configs/install/desktop.txt')],log)
            execute(base+['--no-deps',str(source)],log)
        elif engine in config['repositories']:
            repository=config['repositories'][engine]; target=runtime/'vendor'/engine
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                execute(['git','clone','--no-checkout',repository['url'],str(target)],log)
                execute(['git','-C',str(target),'checkout','--detach',repository['commit']],log)
            actual=subprocess.check_output(['git','-C',str(target),'rev-parse','HEAD'],text=True).strip()
            if actual!=repository['commit']:
                raise RuntimeError(f'Commit incorrect dans {target}; aucune remise à zéro automatique')
            changed=subprocess.check_output(['git','-C',str(target),'status','--porcelain'],text=True).splitlines()
            # Setuptools upstream tracks generated egg-info; never package it from the working tree.
            changed=[line for line in changed if '.egg-info/' not in line[3:] and not line[3:].startswith('build/')]
            if changed:
                raise RuntimeError(f'Checkout moteur modifié : {target}')
            if engine=='adtof' and sha256(target/repository['weights_path'])!=repository['weights_sha256']:
                raise RuntimeError('Hash des poids ADTOF invalide')
            with tempfile.TemporaryDirectory(prefix=engine+'-build-',dir=runtime) as directory:
                staging=Path(directory); archive=staging/'source.zip'
                execute(['git','-C',str(target),'archive','--format=zip','--output',str(archive),repository['commit']],log)
                with zipfile.ZipFile(archive) as stream:
                    stream.extractall(staging/'source')
                execute(base+['--no-deps',str(staging/'source')],log)
    if args.only=='all':
        for entry in config['weights'].values():
            spec=json.loads((source/entry['config']).read_text())
            download(spec['url'],runtime/entry['target'],spec['sha256'])
    report=doctor(source,runtime,engines,config,args.desktop)
    report['source_files_sha256']={str(p.relative_to(source)):sha256(p) for folder in ('src','scripts','configs/install') for p in sorted((source/folder).rglob('*')) if p.is_file() and p.suffix in ('.py','.json','.txt')}
    report['command']=sys.argv
    report['desktop']=args.desktop
    report['repositories']=config['repositories']
    report.update(created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                  duration_seconds=time.monotonic()-started,licenses=config['licenses'],
                  dependencies_policy=config['dependencies_policy'])
    try:
        if not (source/'.git').exists():
            raise subprocess.CalledProcessError(1, 'source sans .git')
        report['source_commit']=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        report['source_commit']=None
    (runtime/'runtime-install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.only=='all' and not report['ready']:
        print('Dépendance manquante : consulter bootstrap.log et installer FFmpeg/MuseScore selon docs/installation-technique.md.',file=sys.stderr)
    return 0 if report['ready'] or (args.allow_missing_tools and all(e.get('import_ok') for e in report['engines'].values()) and all(m['verified'] for m in report['models'].values())) else 1

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError,RuntimeError,OSError) as error:
        print(f'Installation interrompue : {error}. Voir runtime/bootstrap.log.',file=sys.stderr)
        raise SystemExit(1)
