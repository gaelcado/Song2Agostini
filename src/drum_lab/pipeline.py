"""Production chain, audio-only: separation -> transcription -> score -> checks."""
import datetime
import math
import shutil
import subprocess
from .processes import run_external
import time
from pathlib import Path

import pretty_midi

from . import adapters
from .engraving import engrave, estimate_grid, KIT
from .files import ROOT, digest, load, write, resource_path, RESOURCE_ROOT, find_tool, runtime_identity
from .grid import clean_model_grid
from .meter import infer_audio_meter

DEFAULT_CONFIG={'separate_drums':True,'compact':True,'thresholds':[.22,.24,.32,.22,.30]}


def cached_model_grid(audio, cache_path, out):
    """Reuse frozen audio-only model output, checking audio and checkpoint."""
    cache_path=Path(cache_path).resolve()
    runs=(ROOT/'work/runs').resolve()
    if cache_path.name!='grid.json' or cache_path.parent.parent!=runs:
        raise ValueError('Cache grille attendu dans un run audio')
    grid=load(cache_path)
    model=load(resource_path('configs/beat-this-model.json'))
    if grid.get('source')!='Beat This! final0 CPU, audio only' or grid.get('audio_sha256')!=digest(audio) or grid.get('checkpoint_sha256')!=model['sha256'] or grid.get('code_commit')!=model['code_commit']:
        raise ValueError('Cache de grille incompatible avec audio/modèle')
    current_runtime = runtime_identity('beat_this')
    if grid.get('runtime_identity') is None and 'manifest_sha256' in current_runtime:
        raise ValueError('Cache de grille historique sans identité de runtime : nouvelle grille requise')
    if grid.get('runtime_identity') is not None and grid['runtime_identity'] != current_runtime:
        raise ValueError('Cache de grille incompatible avec runtime actuel')
    # Reprocessing is based on original observed peaks, never chained cleanup.
    if 'raw_beat_times_seconds' in grid:
        grid['beat_times_seconds']=grid['raw_beat_times_seconds']
        grid['downbeat_times_seconds']=grid['raw_downbeat_times_seconds']
    grid=clean_model_grid(grid)
    grid['cache_provenance']={'path':str(cache_path),'sha256':digest(cache_path),
                              'inference_reused':True,
                              'runtime_status':'recorded_and_matching' if grid.get('runtime_identity') else 'historical_runtime_not_recorded',
                              'current_runtime':current_runtime}
    write(out,grid)
    return grid


def probe_audio(audio):
    audio=Path(audio).resolve()
    if audio.suffix.lower() not in ('.wav','.flac','.mp3') or not audio.is_file():
        raise ValueError('Un fichier WAV, FLAC ou MP3 est requis')
    result=run_external([find_tool('ffprobe') or 'ffprobe','-v','error','-show_format','-show_streams','-of','json',str(audio)],
                          check=True,capture_output=True,text=True,timeout=30)
    probe=__import__('json').loads(result.stdout)
    duration=float(probe['format']['duration'])
    if not math.isfinite(duration) or not 0<duration<=1800 or not any(s['codec_type']=='audio' for s in probe['streams']):
        raise ValueError('Audio invalide ou supérieur à 30 minutes')
    return probe


def drum_only_events(prediction):
    mapping={35:'kick',36:'kick',38:'snare',40:'snare',42:'hi-hat',44:'hi-hat',46:'hi-hat',
             **{p:'toms' for p in (41,43,45,47,48,50)},**{p:'cymbals' for p in (49,51,52,53,55,57,59)}}
    for event in prediction['events']:
        if event['pitch'] not in KIT or mapping[event['pitch']]!=event['class']:
            raise ValueError('Événement non conforme au kit batterie')
        if not math.isfinite(event['time']) or event['time']<0:
            raise ValueError('Temps de coup invalide')
    return prediction


def generate(audio,out,config=None,piece_id='piece_01',title='Partition de batterie',progress=None,synthetic=False):
    config={**DEFAULT_CONFIG,**(config or {})}
    engine=config.get('engine','adtof')
    if engine not in ('adtof','drumscript','adtof_kit'): raise ValueError('Moteur inconnu')
    if config.get('hat_transient_candidates') and (engine != 'adtof' or not config['separate_drums']):
        raise ValueError('Candidats transitoires réservés à ADTOF sur batterie isolée')
    grid_engine=config.get('grid_engine','librosa')
    if grid_engine not in ('librosa','beat_this'): raise ValueError('Moteur de grille inconnu')
    if engine=='adtof_kit' and not config['separate_drums']:
        raise ValueError('ADTOF kit requiert une batterie isolée')
    if type(config['separate_drums']) is not bool or type(config['compact']) is not bool:
        raise ValueError('Options de séparation/présentation invalides')
    audio=Path(audio).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();progress=progress or (lambda percent,label:None)
    record={'schema_version':1,'piece_id':piece_id,'title':title,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'running','config':config,'synthetic':synthetic,'reference_used':False,
            'source_sha256':{str(p.relative_to(RESOURCE_ROOT)):digest(p) for folder in ('src','scripts') for p in (RESOURCE_ROOT/folder).rglob('*.py')}}
    write(out/'production.json',record)
    try:
        record['runtime_identity'] = runtime_identity('adtof' if engine=='adtof_kit' else engine)
        progress(3,'Lecture et contrôle de l’audio')
        probe=probe_audio(audio);record['audio_sha256']=digest(audio);record['audio_duration_seconds']=float(probe['format']['duration'])
        source=audio
        if config['separate_drums']:
            progress(10,'Isolation locale de la batterie — cette étape peut durer plusieurs minutes')
            source=adapters.demucs(audio,out/'separation')
            record['separation_sha256']=digest(source)
        progress(52,'Transcription de la batterie')
        if engine=='adtof_kit':
            from .kit_detection import adtof_kit
            prediction=drum_only_events(adtof_kit(source,out,piece_id,config['thresholds'],synthetic))
        else: prediction=drum_only_events(
            adapters.adtof(source,out,piece_id,config['thresholds'],synthetic)
            if engine=='adtof' else adapters.drumscript(source,out,piece_id,synthetic=synthetic))
        if config.get('absolute_peak_classes'):
            if engine != 'adtof': raise ValueError('Sélection absolue réservée à ADTOF')
            from .picking import repick
            key=load(out/'cache.json')['key']
            prediction=drum_only_events(repick(out, ROOT/'work/cache'/key/'activations.npy',
                                                config.get('absolute_thresholds', config['thresholds']),
                                                config['absolute_peak_classes']))
        if config.get('hat_transient_candidates'):
            from .transient_audit import apply_hat_candidates
            prediction = apply_hat_candidates(source, out, piece_id, config['thresholds'], prediction, synthetic=synthetic)
        raw=pretty_midi.PrettyMIDI(str(out/'raw.mid'))
        if any(not part.is_drum for part in raw.instruments): raise ValueError('Le MIDI contient une piste mélodique')
        record['event_count']=len(prediction['events']);record['percussion_only']=True
        progress(68,'Estimation de la pulsation depuis l’audio')
        # Musical timing from complete mix, not from a manual sheet.
        if config.get('grid_cache'):
            if grid_engine!='beat_this': raise ValueError('Cache grille réservé au modèle Beat This')
            grid=cached_model_grid(audio,ROOT/config['grid_cache'],out/'grid.json')
        else:
            grid=estimate_grid(audio,out/'grid.json',engine=grid_engine)
        grid=infer_audio_meter(audio,grid)
        if config.get('variable_meter') and grid_engine=='beat_this':
            from .bars import apply_variable_bars
            grid=apply_variable_bars(grid, events=prediction['events'] if config.get('drum_downbeat_cues') else None)
        if config.get('local_tuplets'):
            grid['local_tuplets'] = True
        write(out/'grid.json',grid)
        record['meter_policy']=grid.get('meter_evidence',{})
        record['grid_engine']=grid_engine
        record['grid_sha256']=digest(out/'grid.json')
        if grid_engine=='beat_this':
            record['grid_dependencies']=(resource_path('configs/beat-this.lock.txt')).read_text()
            record['grid_model_sha256']=digest(resource_path('configs/beat-this-model.json'))
        progress(80,'Quantification et mise en page de la partition')
        notation=engrave(out/'raw.mid',grid,out/'notation',title,compact=config['compact'],
                         cymbal_streams_as_ride=bool(config.get('cymbal_streams_as_ride')))
        progress(94,'Contrôle des fichiers et préparation des téléchargements')
        for name in ('score.pdf','score.musicxml','quantized.mid'):
            shutil.copy2(out/'notation'/name,out/name)
        warnings=[('La partition commence à la première pulsation estimée ; le MIDI brut conserve la position dans l’audio.'
                   if warning.startswith('MusicXML relatif') else warning)
                  for warning in notation.get('warnings',[])]
        if config.get('hat_transient_candidates'):
            warnings.append('Ajouts de charleston expérimentaux : transitoires détectés, identité instrumentale non validée.')
        warnings.extend(['La signature et le premier temps sont des hypothèses audio à vérifier.',
                         'La fidélité musicale n’est pas validée automatiquement face à une référence humaine.'])
        if grid_engine=='beat_this':
            warnings.append('Premiers temps prédits par un modèle audio expérimental ; brouillon non validé.')
            if grid.get('bar_evidence',{}).get('status')=='inferred_hypothesis':
                warnings.append('Mesures découpées sur les premiers temps estimés ; changements de signature possibles, à vérifier à l’écoute.')
            elif grid.get('meter_evidence',{}).get('status')=='abstained':
                warnings.append('Regroupement des mesures incertain : candidate dominante ; changements locaux non représentés.')
            warnings.append('La confiance métrique est un diagnostic non calibré ; les alternatives de tempo restent ouvertes.')
        if config['separate_drums']:
            warnings.append('La séparation de batterie peut conserver des artefacts ou omettre certains coups.')
        artifacts={'pdf':str(out/'score.pdf'),'musicxml':str(out/'score.musicxml'),'midi':str(out/'quantized.mid'),'raw_midi':str(out/'raw.mid')}
        record.update(status='completed',artifacts=artifacts,warnings=list(dict.fromkeys(warnings)),notation_status=notation['status'],
                      quality=notation.get('quality',{}),duration_seconds=time.monotonic()-started)
        record['artifact_sha256']={key:digest(path) for key,path in artifacts.items()}
        write(out/'production.json',record);progress(100,'Partition générée — brouillon à vérifier')
        return record
    except Exception as error:
        record.update(status='failed',duration_seconds=time.monotonic()-started,
                      error={'type':type(error).__name__, 'message':str(error)})
        write(out/'production.json',record)
        raise
