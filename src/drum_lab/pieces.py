"""Identifiers and audio-only registration for external regression cases."""
from pathlib import Path
from .files import ROOT, load, digest

BENCHMARK_IDS=tuple(f'bench_{index:02}' for index in range(1,11))
PERCUSSION_IDS=tuple(f'tech_{index:02}' for index in range(1,11))
PIECE_IDS=('piece_01','piece_02')+BENCHMARK_IDS+PERCUSSION_IDS
RUN_IDS=PIECE_IDS+('synthetic',)


def registered_audio(piece,audio,root=None):
    root=Path(root or ROOT).resolve()
    if piece not in RUN_IDS:raise ValueError('Identifiant de morceau non pris en charge')
    if piece not in BENCHMARK_IDS+PERCUSSION_IDS:return
    name='benchmark-percussion-research-manifest.json' if piece in PERCUSSION_IDS else 'benchmark-research-manifest.json'
    manifest=load(root/'data'/name)
    matches=[row for row in manifest['pieces'] if row['id']==piece]
    if len(matches)!=1:raise ValueError('Cas externe absent ou dupliqué dans le manifeste audio')
    row=matches[0];expected=(root/row['audio']).resolve();actual=Path(audio).resolve()
    if not expected.is_relative_to(root/'data/raw/audio') or expected!=actual:
        raise ValueError('Audio différent de la copie enregistrée pour ce cas')
    if digest(actual)!=row['audio_sha256']:raise ValueError('Audio enregistré modifié')
    return row
