"""Package an already tested macOS app without changing its signed resources."""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from build_desktop import ROOT, link_or_copy


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke-report', required=True, type=Path)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('La DMG exige macOS natif')
    report = json.loads(args.smoke_report.read_text())
    if report.get('status') != 'passed' or report.get('frozen') is not True:
        parser.error('Un test complet réussi de l’application figée est requis')
    generated = report['result']
    if generated.get('status') != 'completed' or generated.get('reference_used') is not False:
        parser.error('Génération complète audio seule requise')
    for key in ('pdf', 'musicxml', 'midi', 'raw_midi'):
        artifact = Path(generated['artifacts'][key])
        if not artifact.is_file() or not artifact.stat().st_size:
            parser.error(f'Sortie absente : {key}')
        if sha256(artifact) != generated.get('artifact_sha256', {}).get(key):
            parser.error(f'Hash de sortie invalide : {key}')
    app = ROOT / 'dist/Song2Agostini.app'
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    metadata_path = ROOT / 'dist/Song2Agostini-build.json'
    metadata = json.loads(metadata_path.read_text())
    metadata.update(offline_smoke_test_passed=True, self_contained_inference=True,
                    verification_scope='external evidence for unchanged signed candidate app',
                    smoke_report_sha256=sha256(args.smoke_report),
                    app_executable_sha256=sha256(app / 'Contents/MacOS/Song2Agostini'),
                    embedded_runtime_manifest_sha256=sha256(app / 'Contents/Resources/runtime/distribution-manifest.json'))
    metadata_path.write_text(json.dumps(metadata, indent=2))
    stage = ROOT / 'work/desktop-build/verified-dmg-stage'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    shutil.copytree(app, stage / app.name, symlinks=True, copy_function=link_or_copy)
    (stage / 'Applications').symlink_to('/Applications')
    shutil.copy2(metadata_path, stage)
    shutil.copy2(args.smoke_report, stage / 'desktop-smoke.json')
    (stage / 'LISEZ-MOI.txt').write_text(
        'Song2Agostini — application privée autonome Apple Silicon.\n'
        'Génération audio → PDF/MusicXML/MIDI vérifiée depuis /tmp avec un dossier utilisateur neuf, '
        'PATH système et les moteurs/outils embarqués. Pas de certification de fidélité musicale.\n'
        'La preuve externe valide le bundle signé inchangé ; son manifeste interne reste celui du candidat avant test.\n'
        'Signature locale ad hoc, sans notarisation. Redistribution publique NON autorisée : voir notices du runtime.\n')
    dmg = ROOT / f'dist/Song2Agostini-macos-{platform.machine()}.dmg'
    subprocess.run(['hdiutil', 'create', '-volname', 'Song2Agostini', '-srcfolder', str(stage),
                    '-ov', '-format', 'UDZO', str(dmg)], check=True)
    subprocess.run(['hdiutil', 'verify', str(dmg)], check=True)
    metadata['dmg_sha256'] = sha256(dmg)
    metadata['dmg_size_bytes'] = dmg.stat().st_size
    metadata_path.write_text(json.dumps(metadata, indent=2))
    shutil.rmtree(stage)


if __name__ == '__main__':
    main()
