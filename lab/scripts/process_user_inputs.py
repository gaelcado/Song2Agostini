#!/usr/bin/env python3
"""One bounded, fixed product baseline on one to ten local audios only."""
import argparse
import datetime
import json
import os
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

from drum_lab.files import ROOT, digest, load, write
from drum_lab.pieces import USER_IDS, registered_audio
from drum_lab.pipeline import probe_audio

PROFILE = {
    'hypothesis': 'Baseline nouveaux audios, profil produit figé : Demucs/ADTOF et grille Beat This audio seule, sans réglage musical.',
    'engine': 'adtof', 'grid_engine': 'beat_this', 'separate_drums': True,
    'compact': True, 'thresholds': [.22, .24, .32, .22, .30],
}
MANIFEST = 'new-input-research-manifest.json'
MAX_AUDIO_SECONDS = 7200
CASE_TIMEOUT_SECONDS = 1800


def bounded_case(command, root, log):
    """On POSIX, stop the whole local worker group when its budget expires."""
    process = subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=(os.name == 'posix'))
    try:
        return process.wait(timeout=CASE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()
        raise


def preflight(root=ROOT, only=None, replacement_run=None):
    root = Path(root).resolve()
    path = root / 'data' / MANIFEST
    manifest = load(path)
    rows = manifest.get('pieces')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10:
        raise ValueError('Un à dix audios enregistrés requis')
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('Entrées audio invalides')
    ids = [row.get('id') for row in rows]
    if any(piece not in USER_IDS for piece in ids) or len(set(ids)) != len(ids):
        raise ValueError('Identifiants user_01 à user_10 uniques requis')
    selected = list(only) if only is not None else ids
    if not selected or len(set(selected)) != len(selected) or any(piece not in ids for piece in selected):
        raise ValueError('Sélection audio invalide')
    if replacement_run and (len(selected) != 1 or only is None or
                            Path(replacement_run).name != replacement_run):
        raise ValueError('La correction d’entrée exige un seul identifiant explicite et un run valide')
    allowed = {'id', 'audio', 'audio_sha256', 'title', 'original_filename',
               'audio_duration_seconds', 'source', 'source_email_id', 'source_attachment_id'}
    prepared = []
    for row in rows:
        if set(row) - allowed:
            raise ValueError('Le manifeste audio contient des champs non autorisés')
        if not isinstance(row.get('title'), str) or not row['title'].strip():
            raise ValueError('Titre audio requis')
        if row['id'] not in selected:
            continue
        audio = root / row['audio']
        registered_audio(row['id'], audio, root)
        duration = float(probe_audio(audio)['format']['duration'])
        prepared.append({**row, 'audio_duration_seconds': duration})
    if sum(row['audio_duration_seconds'] for row in prepared) > MAX_AUDIO_SECONDS:
        raise ValueError('Budget total audio supérieur à deux heures')
    prior = [(path, load(path)) for path in (root / 'work/runs').glob('*/record.json')]
    existing = [(path, record) for path, record in prior if record.get('piece_id') in selected]
    if replacement_run:
        if len(existing) != 1:
            raise ValueError('Une unique tentative antérieure requise pour correction d’entrée')
        path, record = existing[0]
        if (path.parent.name != replacement_run or record.get('status') != 'failed' or
                record.get('config') != PROFILE or record.get('audio_sha256') == prepared[0]['audio_sha256']):
            raise ValueError('Correction réservée à un échec, nouvel audio et même profil figé')
    elif existing:
        raise ValueError('Baseline déjà entamée : reprendre les sorties conservées séparément')
    return sorted(prepared, key=lambda row: row['id'])


def process(root=ROOT, dry_run=False, only=None, replacement_run=None):
    root = Path(root).resolve()
    cases = preflight(root, only=only, replacement_run=replacement_run)
    report = {'schema_version': 1, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'reference_used': False, 'musical_fidelity': None, 'profile': PROFILE,
              'manifest_sha256': digest(root / 'data' / MANIFEST),
              'script_sha256': digest(Path(__file__)),
              'budget': {'profiles_per_audio': 1, 'audio_seconds': sum(row['audio_duration_seconds'] for row in cases),
                         'case_timeout_seconds': CASE_TIMEOUT_SECONDS, 'max_cases': 10},
              'cases': [], 'status': 'preflight_passed'}
    if replacement_run:
        report['input_replacement'] = {'prior_failed_run': replacement_run,
                                     'reason': 'Audio fourni corrigé ; profil musical inchangé',
                                     'prior_outputs_preserved': True}
    if dry_run:
        report['inputs'] = cases
        return report
    batch = root / 'work' / ('new-inputs-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S'))
    batch.mkdir(parents=True, exist_ok=False)
    shutil.copy2(Path(__file__), batch / 'process_user_inputs.py')
    shutil.copy2(root / 'data' / MANIFEST, batch / 'input-manifest.json')
    if digest(batch / 'process_user_inputs.py') != report['script_sha256'] or digest(batch / 'input-manifest.json') != report['manifest_sha256']:
        raise ValueError('Source ou manifeste modifié pendant le précontrôle ; aucun calcul lancé')
    config_path = batch / 'config.json'
    write(config_path, [PROFILE])
    report_path = batch / 'report.json'
    report.update(status='running', report_path=str(report_path))
    write(report_path, report)
    started = time.monotonic()
    for row in cases:
        piece = row['id']
        prior = {path.parent.name for path in (root / 'work/runs').glob('*/record.json')}
        command = [sys.executable, '-m', 'drum_lab.cli', 'run', str(root / row['audio']), str(config_path), '--piece', piece]
        item = {**row, 'command': command, 'status': 'running', 'log': str(batch / f'{piece}.log')}
        case_started = time.monotonic()
        try:
            with Path(item['log']).open('w') as log:
                item['returncode'] = bounded_case(command, root, log)
        except subprocess.TimeoutExpired:
            item['error'] = 'Limite de calcul par audio atteinte'
        records = [load(path) for path in (root / 'work/runs').glob('*/record.json')
                   if path.parent.name not in prior and load(path).get('piece_id') == piece]
        if len(records) == 1:
            record = records[0]
            item.update(run_id=record['id'], run_directory=str(root / 'work/runs' / record['id']),
                        status=record['status'], artifacts=record.get('artifacts'), error=record.get('error', item.get('error')))
            if record['status'] == 'running':
                item['status'] = 'failed_timeout'
        else:
            item.update(status='failed', error=item.get('error', 'Run unique absent ; consulter le log'))
        item['duration_seconds'] = time.monotonic() - case_started
        report['cases'].append(item)
        report['duration_seconds'] = time.monotonic() - started
        write(report_path, report)
        print(json.dumps({'piece_id': piece, 'title': row['title'], 'status': item['status'],
                          'duration_seconds': item['duration_seconds'], 'run_id': item.get('run_id')}, ensure_ascii=False), flush=True)
    report['status'] = 'completed' if all(item['status'] == 'awaiting_verification' for item in report['cases']) else 'completed_with_failures'
    write(report_path, report)
    destination = 'new-inputs-replacement-results.json' if replacement_run else 'new-inputs-results.json'
    write(root / 'work' / destination, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--only', nargs='+', choices=USER_IDS)
    parser.add_argument('--replace-input-run', help='Run échoué conservé lors d’une correction de l’audio fourni')
    args = parser.parse_args()
    print(json.dumps(process(dry_run=args.dry_run, only=args.only,
                             replacement_run=args.replace_input_run), ensure_ascii=False, indent=2))
