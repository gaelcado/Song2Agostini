"""Notation automatique issue du MIDI seulement ; aucune référence accessible ici."""
import hashlib
import json
import math
import os
import shutil
import subprocess
from .processes import run_external
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pretty_midi
import numpy as np

from .files import ROOT, env_python, worker_path, worker_environment, find_tool, source_file, runtime_identity, write
from .quantization import quantize_hits

# French percussion positions, independently documented in docs/notation.md.
# GM pitch remains unchanged; display-step is an unpitched staff coordinate.
KIT = {
    35: ('Grosse caisse', 'D', 4, 'normal', 2), 36: ('Grosse caisse', 'D', 4, 'normal', 2),
    38: ('Caisse claire', 'B', 4, 'normal', 2), 40: ('Caisse claire', 'B', 4, 'normal', 2),
    42: ('Charleston fermé', 'G', 5, 'x', 1), 44: ('Charleston pédale', 'B', 3, 'x', 2),
    46: ('Charleston ouvert', 'G', 5, 'circle-x', 1),
    41: ('Tom grave', 'A', 4, 'normal', 2), 43: ('Tom grave', 'A', 4, 'normal', 2),
    45: ('Tom médium', 'D', 5, 'normal', 2), 47: ('Tom médium', 'D', 5, 'normal', 2),
    48: ('Tom aigu', 'E', 5, 'normal', 2), 50: ('Tom aigu', 'E', 5, 'normal', 2),
    49: ('Crash', 'A', 5, 'x', 1), 57: ('Crash', 'A', 5, 'x', 1),
    51: ('Ride', 'B', 5, 'x', 1), 53: ('Ride cloche', 'B', 5, 'diamond', 1),
    52: ('China', 'A', 5, 'x', 1), 55: ('Splash', 'A', 5, 'x', 1), 59: ('Ride', 'B', 5, 'x', 1),
}


def add(parent, tag, value=None, **attributes):
    element = ET.SubElement(parent, tag, {key:str(value) for key,value in attributes.items()})
    if value is not None:
        element.text = str(value)
    return element


def renderer():
    return find_tool('musescore')


def estimate_grid(audio, out, engine='librosa'):
    if engine not in ('librosa','beat_this'): raise ValueError('Moteur de grille inconnu')
    out = Path(out)
    env='beat_this' if engine=='beat_this' else 'adtof'
    run_external([str(env_python(env)),
                    str(worker_path('estimate_grid.py')), str(Path(audio).resolve()), str(out.resolve()),'--engine',engine],
                   env=worker_environment(), check=True, timeout=300, capture_output=True, text=True)
    grid = json.loads(out.read_text(encoding='utf-8'))
    grid['runtime_identity'] = runtime_identity(env)
    write(out, grid)
    return grid


def compact_segments(patterns, tempo_patterns=None):
    """Greedy exact consecutive blocks, never similarities or reference motifs."""
    segments=[]; start=0
    while start < len(patterns):
        if not any(pitches for position,pitches in patterns[start]):
            stop=start+1
            while stop<len(patterns) and not any(pitches for position,pitches in patterns[stop]): stop+=1
            segments.append((start,stop-start,1)); start=stop; continue
        best=(1,1); savings=0
        for length in range(1, min(16,(len(patterns)-start)//2)+1):
            count=1
            while (patterns[start:start+length] == patterns[start+count*length:start+(count+1)*length]
                   and (tempo_patterns is None or tempo_patterns[start:start+length] == tempo_patterns[start+count*length:start+(count+1)*length])):
                count+=1
            gain=length*(count-1)
            if gain>savings: best=(length,count); savings=gain
        length,count=best
        segments.append((start,length,count)); start+=length*count
    return segments


def audit_musicxml(root, segments, slots, measures):
    """Read actual XML durations/instruments, expand repeats and compare events."""
    parsed=[]; errors=[]
    for measure in root.findall('./part/measure'):
        cursor=0; last=0; events=[]; durations={1:0,2:0}
        for node in measure:
            if node.tag=='backup': cursor-=int(node.findtext('duration'))
            if node.tag=='forward': cursor+=int(node.findtext('duration'))
            if node.tag!='note': continue
            duration=int(node.findtext('duration')); voice=int(node.findtext('voice'))
            if node.find('chord') is None:
                last=cursor; cursor+=duration; durations[voice]+=duration
            if node.find('pitch') is not None: errors.append('pitched note')
            if node.find('unpitched') is not None:
                pitch=int(node.find('instrument').get('id')[1:])
                if pitch not in KIT: errors.append('unknown percussion')
                events.append((last,pitch))
        if durations!={1:16,2:16}: errors.append('incomplete voice')
        parsed.append(events)
    expanded=[]; index=0
    for start,length,count in segments:
        block=parsed[index:index+length]; index+=length
        # Audit the XML repeat attributes as well as the expansion plan.
        xml_measures=root.findall('./part/measure')[index-length:index]
        if count>1:
            forward=xml_measures[0].find('./barline/repeat[@direction="forward"]')
            backward=xml_measures[-1].find('./barline/repeat[@direction="backward"]')
            if forward is None or backward is None or int(backward.get('times','2'))!=count:
                errors.append('repeat inconsistent')
        for repetition in range(count):
            for offset, events in enumerate(block):
                original=start+repetition*length+offset
                expanded.extend((original*16+position,pitch) for position,pitch in events)
    expected=sorted((slot,pitch) for slot,pitches in slots.items() for pitch in pitches)
    if sorted(expanded)!=expected: errors.append('expanded events differ')
    return {'valid':not errors,'errors':errors,'expanded_hits':len(expanded),
            'expanded_measures':sum(b*c for a,b,c in segments),'percussion_only':not root.findall('.//pitch'),
            'voices_complete': 'incomplete voice' not in errors}


PRESENTATION_VERSION = 'french-agostini-beat-beams-v5'


def presentation_layout(patterns, segments, systems_per_page=6, legend_lines=5):
    """Balance explicit page breaks using rendered units, including multi-rests.

    Hidden measures under a multi-rest stay in the MusicXML, but must not
    consume layout slots or receive breaks inside that rest.
    """
    visible=[]
    for start,length,repeats in segments:
        silent=length>1 and not any(p for _,p in patterns[start])
        visible.extend([start] if silent else range(start,start+length))
    systems=[visible[i:i+4] for i in range(0,len(visible),4)]
    if systems_per_page < 2 or legend_lines < 0:
        raise ValueError('Capacité de page ou légende invalide')
    if not systems:
        return {}, []
    # The title/draft/legend block reserves vertical space only on page one.
    # One system budget is 180 MusicXML tenths; six lines occupy 180 tenths.
    reserved_systems = math.ceil(30 * (legend_lines + 1) / 180)
    first_capacity = max(1, systems_per_page - reserved_systems)
    pages = 1 + math.ceil(max(0, len(systems) - first_capacity) / systems_per_page)
    base, extra = divmod(len(systems), pages)
    page_sizes = [base + (i < extra) for i in range(pages)]
    overflow = max(0, page_sizes[0] - first_capacity)
    page_sizes[0] -= overflow
    # Reassign first-page overflow before emitting forced page breaks. This
    # prevents automatic overflow followed by a forced one-system orphan.
    while overflow:
        target = min(range(1, pages), key=lambda i: (page_sizes[i], i))
        page_sizes[target] += 1
        overflow -= 1
    boundaries=set();cursor=0
    for size in page_sizes[:-1]:
        cursor+=size;boundaries.add(cursor)
    breaks={system[0]:('page' if i in boundaries else 'system')
            for i,system in enumerate(systems)}
    return breaks,page_sizes


def kit_legend(pitches):
    """Position names and notehead symbols describe the fixed GM kit mapping."""
    positions={('D',4):'sous la portée',('B',4):'ligne centrale',
               ('G',5):'au-dessus de la portée',('B',3):'sous la portée, position pédale',
               ('A',4):'premier interligne',('D',5):'quatrième ligne',
               ('E',5):'dernier interligne',('A',5):'ligne supplémentaire supérieure',
               ('B',5):'au-dessus de la ligne supplémentaire'}
    heads={'normal':'tête pleine','x':'croix (x)',
           'circle-x':'croix encerclée (ox)','diamond':'losange (<>)'}
    return [f'{KIT[p][0]} : {heads[KIT[p][3]]}, {positions[KIT[p][1:3]]}'
            for p in sorted(set(pitches))]



def beam_voice_by_beat(measure, voice):
    """Explicit beams on main chord notes, including intervening rests.

    Durations are already split at quarter boundaries. A quarter/rest breaks
    the group. Secondary beams join adjacent sixteenths; an isolated
    sixteenth uses a hook towards its neighbour in the primary beam.
    """
    position = 0
    groups = {}
    for note in measure.findall('note'):
        if int(note.findtext('voice')) != voice or note.find('chord') is not None:
            continue
        duration = int(note.findtext('duration'))
        if duration < 4:
            groups.setdefault(position // 4, []).append((note, duration))
        position += duration
    for group in groups.values():
        if len(group) < 2 or not any(n.find('unpitched') is not None for n, _ in group):
            continue
        for i, (note, duration) in enumerate(group):
            add(note, 'beam', 'begin' if i == 0 else 'end' if i == len(group)-1 else 'continue', number=1)
            if duration != 1:
                continue
            previous = i > 0 and group[i-1][1] == 1
            following = i + 1 < len(group) and group[i+1][1] == 1
            secondary = ('continue' if previous and following else 'end' if previous
                         else 'begin' if following else 'forward hook' if i+1 < len(group)
                         else 'backward hook')
            add(note, 'beam', secondary, number=2)


def engrave(midi_path, grid, out, title='Batterie - transcription automatique', compact=True):
    started = time.monotonic()
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    # Prevent a failed rerender from leaving an apparently current PDF/report.
    for stale in ('score.pdf','notation.json'):
        (out/stale).unlink(missing_ok=True)
    bpm = float(grid['bpm']); origin = float(grid.get('origin_seconds', 0))
    duration = float(grid.get('duration_seconds', 0))
    if not math.isfinite(bpm) or bpm <= 0 or not math.isfinite(origin) or origin < 0:
        raise ValueError('Grille de notation invalide')
    if not math.isfinite(duration) or duration < 0:
        raise ValueError('Durée invalide')
    if grid.get('time_signature', '4/4') != '4/4' or grid.get('subdivision', 4) != 4:
        raise ValueError('Export actuel : 4/4 et doubles croches seulement')
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    hits = [n for part in midi.instruments if part.is_drum for n in part.notes]
    if not hits:
        raise ValueError('MIDI sans événement de batterie')
    if any(n.pitch not in KIT for n in hits):
        raise ValueError('Pitch de percussion non pris en charge')
    warnings = []
    if any(not p.is_drum and p.notes for p in midi.instruments):
        warnings.append('Pistes mélodiques ignorées : seule la batterie est gravée')
    beats = list(grid.get('beat_times_seconds', []))
    mapped, to_beat, to_seconds, quality = quantize_hits(hits, grid)
    if quality['large_shift_count']:
        warnings.append('Déplacements supérieurs à 50 ms : grille à vérifier')
    if quality['collision_count']:
        warnings.append('Collisions même instrument : regroupées dans la notation uniquement')
    slots = {}
    quant = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    kit = pretty_midi.Instrument(0, is_drum=True)
    for hit, slot, start in mapped:
        slots.setdefault(slot, set()).add(hit.pitch)
        kit.notes.append(pretty_midi.Note(hit.velocity, hit.pitch, start, start + .1))
    quant.instruments.append(kit); quant.write(str(out / 'quantized.mid'))
    total_slots = max(max(slots) + 1, math.ceil(to_beat(duration) * 4))
    measures = max(1, math.ceil(total_slots / 16))
    root = ET.Element('score-partwise', version='4.0')
    work = add(root, 'work'); add(work, 'work-title', title)
    identification = add(root, 'identification')
    add(identification, 'creator', 'Drum Transcription Lab', type='composer')
    defaults = add(root, 'defaults'); scaling = add(defaults, 'scaling')
    add(scaling, 'millimeters', 7); add(scaling, 'tenths', 40)
    page = add(defaults, 'page-layout'); add(page, 'page-height', 1697); add(page, 'page-width', 1200)
    margins = add(page, 'page-margins', type='both')
    for side in ('left', 'right', 'top', 'bottom'): add(margins, side + '-margin', 70)
    part_list = add(root, 'part-list'); score_part = add(part_list, 'score-part', id='P1')
    add(score_part, 'part-name', 'Batterie'); add(score_part, 'part-abbreviation', 'Batt.')
    for pitch in sorted({hit.pitch for hit in hits}):
        ident = f'I{pitch}'
        instr = add(score_part, 'score-instrument', id=ident); add(instr, 'instrument-name', KIT[pitch][0])
        mi = add(score_part, 'midi-instrument', id=ident); add(mi, 'midi-channel', 10); add(mi, 'midi-unpitched', pitch + 1)
    part = add(root, 'part', id='P1')
    patterns = [tuple((i, tuple(sorted(slots.get(number*16+i, ())))) for i in range(16)) for number in range(measures)]
    tempo_patterns = [tuple(round(60/(to_seconds(number*4+i+1)-to_seconds(number*4+i)),6) for i in range(4)) for number in range(measures)]
    segments = compact_segments(patterns, tempo_patterns) if compact else [(i,1,1) for i in range(measures)]
    legend = kit_legend(hit.pitch for hit in hits)
    layout_breaks,page_sizes = presentation_layout(patterns,segments,legend_lines=len(legend))
    expanded_order = []
    displayed = 0
    for segment_start, block_length, repeats in segments:
      for number in range(segment_start, segment_start + block_length):
        expanded_order.append(number)

        measure = add(part, 'measure', number=number + 1)
        if number in layout_breaks:
            attributes=({'new-page':'yes'} if layout_breaks[number]=='page' else
                        ({'new-system':'yes'} if displayed else {}))
            printing = add(measure, 'print', **attributes)
            layout = add(printing, 'system-layout')
            add(layout, 'system-distance', 80)
            if not displayed:
                add(layout, 'top-system-distance', 100 + 30*(len(legend)+1))
        if number == 0:
            attrs = add(measure, 'attributes'); add(attrs, 'divisions', 4)
            ts = add(attrs, 'time'); add(ts, 'beats', 4); add(ts, 'beat-type', 4)
            clef = add(attrs, 'clef'); add(clef, 'sign', 'percussion')
            direction = add(measure, 'direction', placement='above'); dt = add(direction, 'direction-type')
            add(dt, 'words', 'Brouillon - 4/4, doubles croches ; premiers temps à vérifier',
                **{'default-y':str(60+30*len(legend)), 'font-size':'9'})
            for index,line in enumerate(legend):
                direction=add(measure,'direction',placement='above')
                dt=add(direction,'direction-type')
                add(dt,'words',('Légende : ' if index==0 else '')+line,
                    **{'default-y':str(25+30*(len(legend)-index)), 'font-size':'9'})
            direction = add(measure, 'direction', placement='above'); dt = add(direction, 'direction-type')
            mark = add(dt, 'metronome'); add(mark, 'beat-unit', 'quarter'); add(mark, 'per-minute', round(bpm, 2))
            add(direction, 'sound', tempo=round(bpm, 6))
        if compact and number == segment_start and block_length > 1 and not any(pitches for position,pitches in patterns[number]):
            attrs=measure.find('attributes')
            if attrs is None: attrs=add(measure,'attributes')
            add(add(attrs,'measure-style'),'multiple-rest',block_length)
        for beat_index, local_bpm in enumerate(tempo_patterns[number]):
            direction=add(measure,'direction',**{'print-object':'no'})
            add(add(direction,'direction-type'),'words','')
            add(direction,'sound',tempo=local_bpm)
            add(add(measure,'forward'),'duration',4)
        add(add(measure,'backup'),'duration',16)
        for voice in (1, 2):
            if voice == 2: add(add(measure, 'backup'), 'duration', 16)
            if not any(KIT[p][4]==voice for i in range(16) for p in slots.get(number*16+i,())):
                n=add(measure,'note');add(n,'rest',measure='yes');add(n,'duration',16);add(n,'voice',voice)
                continue
            position = 0
            while position < 16:
                absolute = number * 16 + position
                pitches = sorted(p for p in slots.get(absolute, ()) if KIT[p][4] == voice)
                next_position = next((i for i in range(position + 1, 16)
                    if any(KIT[p][4] == voice for p in slots.get(number * 16 + i, ()))), 16)
                length = min(next_position - position, 4 - position % 4)
                # Keep notation within each beat, preserving simultaneous hits as chords.
                for index, pitch in enumerate(pitches or [None]):
                    n = add(measure, 'note')
                    if index: add(n, 'chord')
                    if pitch is None:
                        add(n, 'rest')
                    else:
                        _, step, octave, head, _ = KIT[pitch]
                        unpitched = add(n, 'unpitched'); add(unpitched, 'display-step', step); add(unpitched, 'display-octave', octave)
                    add(n, 'duration', length)
                    if pitch is not None: add(n, 'instrument', id=f'I{pitch}')
                    add(n, 'voice', voice)
                    add(n, 'type', {1: '16th', 2: 'eighth', 3: 'eighth', 4: 'quarter'}[length])
                    if length == 3: add(n, 'dot')
                    if pitch is not None:
                        add(n, 'stem', 'up' if voice == 1 else 'down')
                        add(n, 'notehead', KIT[pitch][3])
                position += length
        for voice in (1, 2):
            beam_voice_by_beat(measure, voice)
        if repeats > 1 and number == segment_start:
            add(add(measure, 'barline', location='left'), 'repeat', direction='forward')
            direction=add(measure,'direction',placement='above')
            add(add(direction,'direction-type'),'words', f'Jouer {repeats} fois', **{'default-x':'0', 'font-size':'9'})
        if repeats > 1 and number == segment_start + block_length - 1:
            add(add(measure, 'barline', location='right'), 'repeat', direction='backward', times=repeats)
        elif number == measures - 1:
            add(add(measure, 'barline', location='right'), 'bar-style', 'light-heavy')
        displayed += 1
    xml_origin = to_seconds(0)
    quality['musicxml_audio_offset_seconds'] = xml_origin
    quality['musicxml_tempo_policy'] = 'tempo direction each quarter; exact tempo patterns required for repeats'
    quality['musicxml_midi_max_relative_timing_error_ms'] = max(abs((to_seconds(slot/4)-xml_origin)-sum(60/t for bar in tempo_patterns[:slot//16] for t in bar)-sum(60/t for t in tempo_patterns[slot//16][:slot%16//4])-(slot%4)/4*60/tempo_patterns[slot//16][slot%16//4])*1000 for slot in slots)
    quality['musicxml_midi_max_absolute_timing_error_ms'] = abs(xml_origin)*1000+quality['musicxml_midi_max_relative_timing_error_ms']
    if abs(xml_origin)>1e-6:
        warnings.append('MusicXML relatif : appliquer musicxml_audio_offset_seconds pour aligner le MIDI audio')
    audit = audit_musicxml(root, segments, slots, measures)
    if not audit['valid']: raise ValueError('Audit MusicXML échoué : ' + str(audit))
    ET.indent(root)
    xml_path = out / 'score.musicxml'
    ET.ElementTree(root).write(xml_path, encoding='utf-8', xml_declaration=True)
    engine = renderer()
    if not engine: raise RuntimeError('MuseScore absent : MusicXML créé, PDF non rendu')
    # Official Windows MuseScore ships qwindows; headless qoffscreen is Linux-only here.
    platform_plugin = {'darwin':'cocoa', 'win32':'windows'}.get(sys.platform, 'offscreen')
    env = dict(os.environ, QT_QPA_PLATFORM=platform_plugin)
    command=[engine, '-o', str((out / 'score.pdf').resolve()), str(xml_path.resolve())]
    from .rendering import render
    render_attempts=render(command,env,out)
    if not (out / 'score.pdf').is_file(): raise RuntimeError('Export PDF absent')
    record = {'status': 'draft_rendered', 'input_midi_sha256': hashlib.sha256(Path(midi_path).read_bytes()).hexdigest(),
              'grid': grid, 'presentation_version':PRESENTATION_VERSION,
              'notation_convention':'french_agostini_compatible',
              'notation_mapping_version':'french-percunivers-v1',
              'beam_policy':'explicit-quarter-groups-including-rests-no-crossbeat',
              'layout_page_systems':page_sizes,'kit_legend':legend, 'measures': measures, 'displayed_measures':displayed, 'compact':compact,
              'compression_segments':[{'start_measure':a+1,'block_measures':b,'times':c} for a,b,c in segments],
              'quality':quality, 'warnings':warnings, 'musicxml_audit':audit, 'input_hits': len(hits),
              'notation_chord_hits': sum(len(p) for p in slots.values()),
              'duplicate_notation_hits_collapsed': len(hits) - sum(len(p) for p in slots.values()),
              'renderer': engine, 'duration_seconds': time.monotonic() - started,
              'command':command, 'render_attempts':render_attempts,
              'renderer_sha256':hashlib.sha256(Path(engine).read_bytes()).hexdigest() if Path(engine).is_file() else None,
              'source_sha256':hashlib.sha256(source_file(__file__).read_bytes()).hexdigest(),
              'outputs_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('quantized.mid','score.musicxml','score.pdf')},
              'files': ['quantized.mid', 'score.musicxml', 'score.pdf'],
              'outputs': {name:str((out/name).resolve()) for name in ('quantized.mid','score.musicxml','score.pdf')},
              'limitations': ['4/4 assumption', 'tempo octave assumption', '16th-note grid', 'downbeat not verified', 'no swing/triplet inference'],
              'reference_used': False}
    (out / 'notation.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return record


def from_audio_prediction(audio, prediction_dir, title):
    prediction_dir = Path(prediction_dir)
    grid = estimate_grid(audio, prediction_dir / 'grid.json')
    return engrave(prediction_dir / 'raw.mid', grid, prediction_dir / 'notation', title)
