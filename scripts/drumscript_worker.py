"""Local DrumScript DSP inference, retaining raw events before any notation."""
import json
import sys
from pathlib import Path

import drumscript as ds
import pretty_midi
from drumscript.notation_generator.constants import SAMPLE_RATE, DRUM_NOTATION_MAP

audio, cache, out, piece, synthetic = sys.argv[1:]
cache = Path(cache); out = Path(out)
inference_path = cache/'inference.json'
if inference_path.exists():
    inference = json.loads(inference_path.read_text())
else:
    y, sr = ds.load_audio(audio, sr=SAMPLE_RATE)
    y = ds.normalise_audio(y)
    onsets = ds.detect_onsets(y, sr)
    classified = ds.classify_events(y, sr, onsets)
    inference = {'engine':'drumscript', 'version':ds.__version__, 'sample_rate':sr,
                 'onsets_seconds':[float(t) for t in onsets], 'classified_events':classified,
                 'learned_weights':None, 'separation_in_worker':False}
    temporary = inference_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(inference, default=lambda x: x.tolist(), indent=2))
    temporary.replace(inference_path)
    inference = json.loads(inference_path.read_text())

mapping = {36:'kick',38:'snare',41:'toms',45:'toms',48:'toms',42:'hi-hat',46:'hi-hat',49:'cymbals',51:'cymbals'}
events=[]; unknown={}
for event in inference['classified_events']:
    for instrument in event['instruments']:
        if instrument not in DRUM_NOTATION_MAP:
            unknown[instrument]=unknown.get(instrument,0)+1
            continue
        pitch = DRUM_NOTATION_MAP[instrument]['midi_program']
        events.append({'time':float(event['time_sec']), 'pitch':pitch, 'class':mapping[pitch]})
events.sort(key=lambda e:e['time'])
midi = pretty_midi.PrettyMIDI(resolution=10000)
track = pretty_midi.Instrument(0,is_drum=True,name='DrumScript raw onsets')
for event in events:
    track.notes.append(pretty_midi.Note(100,event['pitch'],event['time'],event['time']+0.1))
midi.instruments.append(track); midi.write(str(out/'raw.mid'))
(out/'events.json').write_text(json.dumps({'schema_version':1,'kind':'prediction','piece_id':piece,
                                        'synthetic':synthetic=='True','events':events},indent=2))
(out/'original-result.json').write_text(json.dumps(inference,indent=2))
(out/'drumscript-diagnostics.json').write_text(json.dumps({'unknown_instruments_skipped':unknown,
    'onsets':len(inference['onsets_seconds']),'event_count':len(events),'version':ds.__version__},indent=2))
print('DrumScript',ds.__version__,'events',len(events),'cache',str(inference_path),'unknown',unknown)
