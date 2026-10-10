"""Assemble a private macOS payload; does not approve redistribution."""
from __future__ import annotations
import hashlib,json,os,platform,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'work/desktop-runtime'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def link_or_copy(source,target):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    try: os.link(source,target)
    except OSError: shutil.copy2(source,target)

def textfile(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')

def download(url,target):
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen(url,timeout=60) as response:
            target.write_bytes(response.read())

def hashes(paths):
    result={}
    for path in paths:
        candidates=sorted(path.rglob('*')) if path.is_dir() else [path]
        for p in candidates:
            if p.is_file():
                resolved=p.resolve()
                if not resolved.is_relative_to(RUNTIME.resolve()):
                    raise RuntimeError(f'Lien externe au runtime: {p}')
                result[str(p.relative_to(RUNTIME))]=digest(p)
    return result

def main():
    if sys.platform!='darwin':
        raise RuntimeError('Cet assemblage privé utilise exclusivement les outils macOS existants.')
    RUNTIME.mkdir(parents=True,exist_ok=True)
    for name,config,source,target in (
        ('demucs','demucs-model.json',ROOT/'work/models/demucs/955717e8-8726e21a.th',RUNTIME/'models/demucs/955717e8-8726e21a.th'),
        ('beat_this','beat-this-model.json',ROOT/'work/models/beat_this/final0.ckpt',RUNTIME/'models/beat_this/final0.ckpt')):
        spec=json.loads((ROOT/'configs'/config).read_text())
        if digest(source)!=spec['sha256']: raise RuntimeError(f'Modèle {name} invalide')
        if not target.exists(): link_or_copy(source,target)
        if digest(target)!=spec['sha256']: raise RuntimeError(f'Copie {name} invalide')
    original=ROOT/'work/tools/MuseScore 4.app';musescore=RUNTIME/'tools/MuseScore 4.app'
    if not musescore.exists(): shutil.copytree(original,musescore,symlinks=True)
    for name in ('adtof','demucs','beat_this'):
        worker=RUNTIME/'workers'/name/name
        if not worker.is_file(): raise RuntimeError(f'Worker absent: {name}')
    notices=RUNTIME/'licenses';sources=RUNTIME/'source-provenance'
    install=json.loads((ROOT/'configs/install/runtime.json').read_text())
    textfile(notices/'adtof/NOTICE.txt',
        'ADTOF-pytorch: commit '+install['repositories']['adtof']['commit']+'\n'
        'Aucune licence explicite séparée trouvée dans ce commit du port et pour ses poids convertis.\n'
        'Cette notice ne constitue PAS une licence ni une permission de redistribution.\n'
        'Original ADTOF: CC-BY-NC-SA-4.0; conserver ses obligations; applicability au port non résolue.\n'
        'Usage local privé seulement. Redistribution non approuvée.\n')
    download('https://raw.githubusercontent.com/MZehren/ADTOF/master/LICENSE',notices/'adtof/UPSTREAM-LICENSE')
    download('https://raw.githubusercontent.com/adefossez/demucs/main/LICENSE',notices/'demucs/LICENSE')
    (notices/'beat_this').mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'work/release-smoke/runtime/vendor/beat_this/LICENSE',notices/'beat_this/LICENSE')
    download('https://raw.githubusercontent.com/musescore/MuseScore/v4.6.5/LICENSE.txt',notices/'musescore/LICENSE.txt')
    shutil.copy2(original/'Contents/Resources/sound/MS Basic_License.md',notices/'musescore/MS Basic_License.md')
    ffmpeg_source=Path('/opt/homebrew/Cellar/ffmpeg/8.0.1_2')
    (notices/'ffmpeg').mkdir(parents=True,exist_ok=True)
    for name in ('COPYING.GPLv2','COPYING.GPLv3','COPYING.LGPLv2.1','COPYING.LGPLv3','LICENSE.md'):
        shutil.copy2(ffmpeg_source/name,notices/'ffmpeg'/name)
    textfile(notices/'ffmpeg/NOTICE.txt',
        'FFmpeg et ffprobe 8.0.1: build Homebrew 8.0.1_2 avec --enable-gpl --enable-version3.\n'
        'Les bibliothèques tierces embarquées demandent aussi leurs notices/sources propres.\n'
        'Les textes FFmpeg seuls ne constituent pas un audit complet du bundle de dépendances.\n')
    provenance={
      'adtof':('https://github.com/xavriley/ADTOF-pytorch',install['repositories']['adtof']['commit'],
                'Licence port/poids non explicitée; permission de redistribution non établie.'),
      'demucs':('https://github.com/adefossez/demucs','version PyPI 4.0.1',
                 'Déclaration MIT générale; pas de licence des poids séparée identifiée.'),
      'beat_this':('https://github.com/CPJKU/beat_this',install['repositories']['beat_this']['commit'],
                   'README commit déclare code et checkpoints MIT.'),
      'ffmpeg':('https://ffmpeg.org/releases/ffmpeg-8.0.1.tar.xz','Homebrew ffmpeg 8.0.1_2',
                'Sources correspondantes complètes du build et bibliothèques tierces non assemblées.'),
      'ffprobe':('https://ffmpeg.org/releases/ffmpeg-8.0.1.tar.xz','Homebrew ffmpeg 8.0.1_2',
                 'Sources correspondantes complètes du build et bibliothèques tierces non assemblées.'),
      'musescore':('https://github.com/musescore/MuseScore/tree/v4.6.5','4.6.5.253511702',
                   'Source amont liée; correspondance exacte build, patches et dépendances non reconstituée.')}
    for name,(url,revision,note) in provenance.items():
        textfile(sources/name/'README.txt',f'Composant : {name}\nSource amont : {url}\nRévision : {revision}\n{note}\n'
          'PROVENANCE SEULEMENT : ce fichier ne constitue pas une offre GPL de source correspondante complète.\n'
          'Redistribution non approuvée; payload privé de validation.\n')
    recipes=sources/'build-recipes';recipes.mkdir(parents=True,exist_ok=True)
    for name in ('freeze_workers.py','worker_entry.py','bundle_macos_tool.py','assemble_private_runtime.py'):
        shutil.copy2(ROOT/'packaging'/name,recipes/name)
    shutil.copy2(ffmpeg_source/'INSTALL_RECEIPT.json',sources/'ffmpeg/INSTALL_RECEIPT.json')
    # Preserve declarations separately from actual license texts.
    (notices/'installed-distribution-declarations.json').unlink(missing_ok=True)
    metadata=ROOT/'work/release-smoke/runtime/runtime-install.json'
    if metadata.exists():
        textfile(notices/'source-bootstrap-declarations.json',json.dumps({'scope':'separate_source_installation_not_frozen_worker_environment','data':json.loads(metadata.read_text())},ensure_ascii=False,indent=2))
    metadata_code="import importlib.metadata as m,json; print(json.dumps([{'name':d.metadata.get('Name'),'version':d.version,'license_expression':d.metadata.get('License-Expression'),'license_declaration':d.metadata.get('License'),'license_files':[str(d.locate_file(f)) for f in (d.files or []) if 'license' in str(f).lower() or 'copying' in str(f).lower()],'status':'metadata_declaration_only'} for d in m.distributions()]))"
    for engine in ('adtof','demucs','beat_this'):
        buildfile=RUNTIME/'workers'/engine/'build.json'
        environment_python=Path(json.loads(buildfile.read_text())['command'][0]) if buildfile.exists() else ROOT/'work/envs'/engine/'bin/python'
        declarations=json.loads(subprocess.check_output([str(environment_python),'-c',metadata_code],text=True))
        copied=[]
        for distribution in declarations:
            name=distribution['name'] or 'unknown'
            for index,source_file in enumerate(distribution['license_files']):
                notice_source=Path(source_file)
                if notice_source.is_file():
                    destination=notices/engine/'dependencies'/name/(str(index)+'-'+notice_source.name)
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(notice_source,destination)
                    copied.append(str(destination.relative_to(RUNTIME)))
        textfile(notices/engine/'build-environment-declarations.json',json.dumps({'scope':'actual_frozen_worker_build_environment','python':str(environment_python),'declarations':declarations,'copied_notice_files':copied,'redistribution_approved':False},ensure_ascii=False,indent=2))
    main_environment=ROOT/'.venv/bin/python'
    main_declarations=json.loads(subprocess.check_output([str(main_environment),'-c',metadata_code],text=True))
    application_notices=notices/'application-runtime';application_notices.mkdir(parents=True,exist_ok=True)
    selected={'pyside6','pyside6-addons','pyside6-essentials','shiboken6','pyinstaller','pyinstaller-hooks-contrib'}
    for distribution in main_declarations:
        name=(distribution['name'] or '').lower().replace('_','-')
        if name in selected:
            for index,source_file in enumerate(distribution['license_files']):
                notice_source=Path(source_file)
                if notice_source.is_file():
                    destination=application_notices/name/(str(index)+'-'+notice_source.name)
                    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(notice_source,destination)
    qt_notice=ROOT/'.venv/lib/python3.11/site-packages/PySide6/Qt/lib/QtWebEngineCore.framework/Resources/qtwebengine_licenses.html'
    if qt_notice.exists():shutil.copy2(qt_notice,application_notices/'qtwebengine_licenses.html')
    python_license=Path(subprocess.check_output([str(main_environment),'-c','import sys;print(sys.base_prefix)'],text=True).strip())/'LICENSE.txt'
    if python_license.exists():shutil.copy2(python_license,application_notices/'Python-LICENSE.txt')
    download('https://code.qt.io/cgit/pyside/pyside-setup.git/plain/LICENSES/LGPL-3.0-only.txt?h=v6.8.3',application_notices/'PySide6-upstream-LGPL-3.0-only.txt')
    download('https://code.qt.io/cgit/pyside/pyside-setup.git/plain/LICENSES/GPL-3.0-only.txt?h=v6.8.3',application_notices/'PySide6-upstream-GPL-3.0-only.txt')
    textfile(application_notices/'NOTICE.txt',
      'Qt for Python/PySide6 6.8.3: licence déclarée dans métadonnées des roues; textes LGPL/GPL pris à la source amont v6.8.3.\n'
      'Les RECORD des roues PySide installées ne répertorient pas de notices licence; qtwebengine_licenses.html non trouvé dans ce bundle.\n'
      'Ces textes amont ne remplacent pas toutes les notices Chromium/Qt tierces, ni les sources correspondantes et obligations de relinking.\n'
      'Redistribution non approuvée; audit des notices tierces incomplet.\n')
    textfile(application_notices/'build-environment-declarations.json',json.dumps({'scope':'application_build_environment_not_final_frozen_app_file_inventory','declarations':main_declarations,'redistribution_approved':False},ensure_ascii=False,indent=2))
    textfile(sources/'application_runtime/README.txt',
      'Python source: https://www.python.org/downloads/source/\n'
      'Qt/PySide source: https://download.qt.io/official_releases/QtForPython/pyside6/\n'
      'QtWebEngine Chromium third-party notices included where present in installed bundle.\n'
      'PyInstaller source: https://github.com/pyinstaller/pyinstaller/tree/v6.16.0\n'
      'PROVENANCE ONLY: no complete corresponding-source offer or legal redistribution approval.\n'
      'Actual main app asset inventory must be obtained after its final freeze.\n')
    entries={}
    for name in ('adtof','demucs','beat_this','ffmpeg','ffprobe','musescore'):
        if name in ('adtof','demucs','beat_this'):
            component=RUNTIME/'workers'/name/name;roots=[component.parent]
            if name!='adtof': roots.append(RUNTIME/'models'/name)
            else:
                # ADTOF learned checkpoint lives inside the collected worker package.
                weights=list(component.parent.rglob('adtof_frame_rnn_pytorch_weights.pth'))
                if not weights or any(digest(p)!=install['repositories']['adtof']['weights_sha256'] for p in weights):
                    raise RuntimeError('Poids ADTOF collectés absents ou incorrects')
        elif name=='musescore': component=musescore/'Contents/MacOS/mscore';roots=[musescore]
        else: component=RUNTIME/'tools'/name;roots=[component,RUNTIME/'tools/lib']
        license_root=notices/('ffmpeg' if name=='ffprobe' else name)
        source_root=sources/name
        entries[name]={'path':str(component.relative_to(RUNTIME)),
          'license_path':str(license_root.relative_to(RUNTIME)),
          'source_offer_path':str((source_root/'README.txt').relative_to(RUNTIME)),
          'source_offer_status':'provenance_only_not_complete_corresponding_source',
          'redistribution_approved':False,'sha256':hashes(roots+[license_root,source_root])}
    entries['application_runtime']={'path':'licenses/application-runtime','license_path':'licenses/application-runtime','source_offer_path':'source-provenance/application_runtime/README.txt','source_offer_status':'provenance_only_not_complete_corresponding_source','redistribution_approved':False,'sha256':hashes([application_notices,sources/'application_runtime'])}
    manifest={'schema_version':1,'platform':sys.platform,'architecture':platform.machine(),
      'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'self_contained':True,
      'self_contained_status':'assembled_candidate_pending_complete_offline_pipeline',
      'offline_smoke_test_passed':False,'redistribution_approved':False,'private_validation_only':True,
      'redistribution_blockers':['ADTOF port and converted checkpoint licensing not explicit',
         'Full corresponding-source obligations and third-party notices for native components not completed'],
      'components':entries,'notice':'Licence paths may contain uncertainty notices. Source offer paths contain provenance, not a legal source offer.'}
    (RUNTIME/'distribution-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'manifest':str(RUNTIME/'distribution-manifest.json'),'components':{k:len(v['sha256']) for k,v in entries.items()},'redistribution_approved':False}))

if __name__=='__main__':main()
