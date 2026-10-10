"""Display titles from audio-only metadata; internal identifiers stay internal."""
from pathlib import Path
from .files import ROOT, digest, load


def audio_title(audio, filename=None):
    fallback = Path(filename or audio).stem.strip()[:120] or 'Partition de batterie'
    fingerprint = digest(audio)
    for name in ('research-manifest.json', 'benchmark-research-manifest.json',
                 'benchmark-percussion-research-manifest.json', 'new-input-research-manifest.json'):
        manifest = ROOT / 'data' / name
        if not manifest.is_file():
            continue
        for row in load(manifest).get('pieces', []):
            title = row.get('title')
            if row.get('audio_sha256') == fingerprint and isinstance(title, str) and title.strip():
                return ' '.join(title.split())[:120]
    return fallback
