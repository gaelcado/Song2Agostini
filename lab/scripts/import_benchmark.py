#!/usr/bin/env python3
"""Verifier-only import of CC BY original audio/MIDI pairs; no prediction input."""
import argparse
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import wave
import zipfile

ROOT = Path(__file__).resolve().parents[2]

def sha(data):
    return hashlib.sha256(data).hexdigest()

class RangeArchive(io.RawIOBase):
    """Seekable HTTP object: request only ZIP directory and selected members."""
    def __init__(self, url, size, generation, budget):
        self.url = url + '?generation=' + generation
        self.size, self.pos, self.downloaded, self.budget = size, 0, 0, budget
        self.cache = {}
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        if self.pos < 0: raise ValueError('Negative ZIP seek')
        return self.pos
    def read(self, n=-1):
        n = min(self.size-self.pos, self.size if n < 0 else n)
        if n <= 0: return b''
        start, end = self.pos, self.pos+n-1
        key = (start,end)
        if key not in self.cache:
            if self.downloaded+n > self.budget: raise RuntimeError('Download budget exceeded')
            req = urllib.request.Request(self.url, headers={'Range':f'bytes={start}-{end}'})
            with urllib.request.urlopen(req, timeout=120) as res:
                if res.status != 206 or res.headers.get('Content-Range') != f'bytes {start}-{end}/{self.size}':
                    raise RuntimeError('Server did not honor pinned HTTP Range')
                data = res.read()
            if len(data) != n: raise RuntimeError('Truncated HTTP range')
            self.cache[key] = data
            self.downloaded += n
        self.pos += n
        return self.cache[key]

def import_gmd(config):
    src=config['source']
    with urllib.request.urlopen(src['midi_archive_url'],timeout=120) as res: midi_zip=res.read()
    if sha(midi_zip) != src['midi_archive_sha256']: raise RuntimeError('MIDI archive checksum mismatch')
    mz=zipfile.ZipFile(io.BytesIO(midi_zip))
    license_text=mz.read('groove/LICENSE').decode()
    if 'Creative Commons Attribution 4.0 International' not in license_text: raise RuntimeError('Unexpected license')
    rows={r['midi_filename']:r for r in csv.DictReader(io.StringIO(mz.read('groove/info.csv').decode()))}
    remote=RangeArchive(src['audio_archive_url'],src['audio_archive_bytes'],src['audio_object_generation'],config['download_budget_bytes'])
    az=zipfile.ZipFile(remote)
    private=[];research=[]
    for selected in config['selection']:
        ident=selected['id'];row=rows[selected['midi_member']]
        wav=az.read('groove/'+row['audio_filename']);midi=mz.read('groove/'+row['midi_filename'])
        # ZIP member CRC is checked by ZipFile; copy byte-for-byte, never regenerate originals.
        audio_path=Path('data/raw/audio')/(ident+'.wav')
        score_path=Path('data/raw/scores')/(ident+'.original.mid')
        for path,data in [(audio_path,wav),(score_path,midi)]:
            target=ROOT/path;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.read_bytes()!=data: raise RuntimeError(f'Conflicting original: {path}')
            target.write_bytes(data)
        with wave.open(io.BytesIO(wav)) as w:
            audio_meta={'duration_seconds':w.getnframes()/w.getframerate(),'sample_rate':w.getframerate(),'channels':w.getnchannels(),'sample_width_bytes':w.getsampwidth()}
        public={'id':ident,'audio':str(audio_path),'audio_sha256':sha(wav),'audio_metadata':audio_meta,'source_dataset':src['name'],'source_version':src['version'],'license':src['license'],'audio_kind':'human_performed_electronic_drums_synthesized_audio','case_description':selected['description']}
        research.append(public)
        private.append({**public,'score':str(score_path),'score_sha256':sha(midi),'source_metadata':row,'reference_kind':'dataset_original_performance_midi','human_validated':False,'evaluation_ready':False,'coverage':'dataset_performance; musical completeness and mapping require verifier audit','alignment_status':'dataset alignment claim; not independently validated locally','annotation_policy_status':'pending_verifier_audit','original_unchanged':True})
        print(f'{ident}: imported audio and original MIDI ({len(wav)} audio bytes)',flush=True)
    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    shared={'schema_version':1,'corpus_id':config['corpus_id'],'created_at':timestamp,'license':src['license'],'attribution':src['attribution'],'source_url':src['page_url'],'count':len(private)}
    (ROOT/'data/benchmark-percussion-manifest.json').write_text(json.dumps({**shared,'role':'verification_only','source':src,'source_license_text':license_text,'downloaded_bytes':remote.downloaded+len(midi_zip),'pieces':private},ensure_ascii=False,indent=2)+'\n')
    (ROOT/'data/benchmark-percussion-research-manifest.json').write_text(json.dumps({**shared,'role':'research_audio_only','reference_access':'prohibited_by_docs_separation','pieces':research},ensure_ascii=False,indent=2)+'\n')
    print(f'Complete: {len(private)} pairs; {remote.downloaded+len(midi_zip)} bytes transferred. Evaluation remains pending verifier validation.')



def import_oga(config):
    import subprocess
    try:
        import mido
    except ImportError as exc:
        raise RuntimeError('Use the isolated project environment: .venv/bin/python lab/scripts/import_benchmark.py') from exc
    private, research, downloaded = [], [], 0
    for item in config['selection']:
        assets = {}
        for kind, folder in [('audio', 'data/raw/audio/corpus-sources'), ('midi', 'data/raw/scores/corpus-sources')]:
            url = item[kind+'_source_url']
            path = ROOT/item[kind+'_source_local']
            if not path.exists():
                with urllib.request.urlopen(url, timeout=120) as response:
                    data = response.read(config['download_budget_bytes']-downloaded+1)
                downloaded += len(data)
                if downloaded > config['download_budget_bytes']: raise RuntimeError('Download budget exceeded')
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            data=path.read_bytes()
            if sha(data) != item[kind+'_source_sha256']: raise RuntimeError('Source checksum mismatch')
            assets[kind]=data
        if item.get('supplementary_source'):
            extra=item['supplementary_source'];extra_path=ROOT/extra['archive_local']
            if not extra_path.exists():
                with urllib.request.urlopen(extra['url'],timeout=120) as response: extra_bytes=response.read(config['download_budget_bytes']-downloaded+1)
                downloaded += len(extra_bytes)
                if downloaded > config['download_budget_bytes']: raise RuntimeError('Download budget exceeded')
                extra_path.write_bytes(extra_bytes)
            extra_data=extra_path.read_bytes()
            if sha(extra_data)!=extra['sha256']: raise RuntimeError('Supplementary score checksum mismatch')
            with zipfile.ZipFile(io.BytesIO(extra_data)) as archive:
                native=[name for name in archive.namelist() if name.endswith('.mscz')]
                if len(native)!=1: raise RuntimeError('Ambiguous native notation archive')
                (ROOT/extra['notation_source']).write_bytes(archive.read(native[0]))
        evidence=ROOT/item['source_page_evidence']
        if evidence.exists() and sha(evidence.read_bytes())!=item['source_page_sha256']:
            raise RuntimeError('Source license evidence was modified')
        ident=item['id'];source_audio=ROOT/item['audio_source_local']
        ext=source_audio.suffix.lower()
        # The original OGG remains untouched. WAV is an explicitly derived decoding for engine compatibility.
        audio_path=Path('data/raw/audio')/(ident+('.wav' if ext=='.ogg' else ext))
        target_audio=ROOT/audio_path
        if ext=='.ogg':
            subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(source_audio),'-c:a','pcm_s16le','-y',str(target_audio)],check=True)
            conversion='OGG decoded to PCM16 WAV with ffmpeg; original OGG preserved'
        else:
            if target_audio.exists() and target_audio.read_bytes()!=assets['audio']: raise RuntimeError('Conflicting original audio')
            target_audio.write_bytes(assets['audio']);conversion='none; original byte-for-byte copy'
        score_path=Path('data/raw/scores')/(ident+'.original.mid');target_score=ROOT/score_path
        if target_score.exists() and target_score.read_bytes()!=assets['midi']: raise RuntimeError('Conflicting original score')
        target_score.write_bytes(assets['midi'])
        midi=mido.MidiFile(file=io.BytesIO(assets['midi']))
        drum=any(msg.type=='note_on' and msg.velocity>0 and msg.channel==9 for track in midi.tracks for msg in track)
        melody=any(msg.type=='note_on' and msg.velocity>0 and msg.channel!=9 for track in midi.tracks for msg in track)
        if not (drum and melody): raise RuntimeError('Candidate is not qualified as MIDI percussion plus melodic mix')
        raw_meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(target_audio)]))
        stream=next(x for x in raw_meta['streams'] if x['codec_type']=='audio')
        meta={'duration_seconds':float(raw_meta['format']['duration']),'sample_rate':int(stream['sample_rate']),'channels':stream['channels'],'codec':stream['codec_name']}
        pub={'id':ident,'title':item['title'],'author':item['author'],'audio':str(audio_path),'audio_sha256':sha(target_audio.read_bytes()),'audio_metadata':meta,'source_url':item['page_url'],'license':item['license'],'license_url':item['license_url'],'audio_kind':item['audio_kind'],'case_description':item['case_description'],'audio_conversion':conversion}
        research.append(pub)
        private.append({**pub,'score':str(score_path),'score_sha256':sha(assets['midi']),'source_provenance':item,'reference_kind':'author_original_composition_midi','human_validated':False,'evaluation_ready':False,'pairing_status':'author_published_audio_and_MIDI_on_same_source_page; local structural qualification only','percussion_channel_present':drum,'melodic_channels_present':melody,'coverage':'candidate original full score; correspondence and exhaustive drum coverage require verifier audit','alignment_status':'not independently validated; no prediction consulted','annotation_policy_status':'pending_verifier_audit','original_midi_unchanged':True})
        print(f'{ident}: author original MIDI + multi-instrument audio imported',flush=True)
    common={'schema_version':1,'corpus_id':config['corpus_id'],'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'count':len(private),'license':'CC0-1.0','source_url':'https://opengameart.org/'}
    (ROOT/'data/benchmark-manifest.json').write_text(json.dumps({**common,'role':'verification_only','downloaded_bytes_this_replay':downloaded,'pieces':private},ensure_ascii=False,indent=2)+'\n')
    (ROOT/'data/benchmark-research-manifest.json').write_text(json.dumps({**common,'role':'research_audio_only','reference_access':'prohibited_by_docs_separation','pieces':research},ensure_ascii=False,indent=2)+'\n')
    print('Complete: ten licensed author audio/MIDI pairs; reference validation pending.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/corpus-oga-v1.json')
    args=parser.parse_args();config=json.loads((ROOT/args.config).read_text())
    if config.get('import_kind')=='opengameart_original_pairs': import_oga(config)
    else: import_gmd(config)

if __name__=='__main__':main()
