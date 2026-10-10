"""Copie locale vérifiée des deux paires, sans toucher aux fichiers déposés."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAIRS = {
    'piece_01': ('musique/Deluxe Michael.MP3', 'musique/Michael-Deluxe.pdf', 'artisanale'),
    'piece_02': ('musique IA/Bacalao con pan Mp3.MP3', 'musique IA/Bacalao con pan 02.pdf', 'Suno'),
}
TITLES = {'piece_01': 'Deluxe Michael', 'piece_02': 'Bacalao con pan'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest_path = ROOT / 'data/manifest.json'
    manifest = json.loads((manifest_path if manifest_path.exists() else ROOT / 'data/manifest.example.json').read_text())
    # Preflight all sources and existing targets before copying anything.
    copies = []
    if len(manifest['pieces']) != 2 or {p['id'] for p in manifest['pieces']} != set(PAIRS):
        raise ValueError('Deux identifiants distincts piece_01 et piece_02 requis')
    for piece in manifest['pieces']:
        audio, score, provenance = PAIRS[piece['id']]
        for kind, source, suffix in (('audio', audio, '.mp3'), ('score', score, '.pdf')):
            source_path = ROOT / source
            target = ROOT / 'data/raw' / ('audio' if kind == 'audio' else 'scores') / (piece['id'] + suffix)
            source_hash = digest(source_path)
            if target.exists() and digest(target) != source_hash:
                raise ValueError(f'Copie existante différente, conservée : {target}')
            if piece.get(kind) and piece[kind] != str(target.relative_to(ROOT)):
                raise ValueError(f'Chemin déjà renseigné différent, conservé : {piece[kind]}')
            copies.append((piece, kind, source, source_path, target, source_hash, provenance))
    for piece, kind, source, source_path, target, source_hash, provenance in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source_path, target)
        if digest(target) != source_hash:
            raise ValueError(f'Copie non conforme : {target}')
        piece[kind] = str(target.relative_to(ROOT))
        piece.setdefault('sources', {})[kind] = {'path': source, 'sha256': source_hash, 'bytes': target.stat().st_size}
        piece['score_format'] = 'pdf'
        piece.setdefault('metadata', {})['provenance'] = provenance
        piece['metadata']['title'] = TITLES[piece['id']]
        piece['metadata']['provenance_source'] = 'déclaration utilisateur, 10 octobre 2026'
        if kind == 'audio':
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(target)], check=True, capture_output=True, text=True)
            piece['metadata']['audio_probe'] = json.loads(probe.stdout)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    # La recherche reçoit une projection audio seule, sans chemin de partition,
    # mapping, annotation, alignement ou empreinte de référence.
    research = {'schema_version': 1, 'pieces': [
        {'id': piece['id'], 'title': TITLES[piece['id']], 'role': piece['role'], 'audio': piece['audio'],
         'audio_sha256': piece['sources']['audio']['sha256']}
        for piece in manifest['pieces']
    ]}
    (ROOT / 'data/research-manifest.json').write_text(json.dumps(research, indent=2) + '\n')
    print(json.dumps({'manifest': str(manifest_path), 'copied_and_hash_verified': len(copies), 'human_validation': 'pending'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
