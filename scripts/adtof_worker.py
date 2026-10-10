import sys,json
from pathlib import Path
import numpy as np
import torch
import adtof_pytorch as a

audio, cache, out, piece, thresholds, synthetic=sys.argv[1:]
out=Path(out); cache=Path(cache)
weights=Path(a.get_default_weights_path())
if not weights.is_file(): raise RuntimeError('Poids ADTOF absents : refus du modèle aléatoire')
if cache.exists():
    activations=np.load(cache,allow_pickle=False)
else:
    model=a.create_frame_rnn_model(a.calculate_n_bins())
    model=a.load_pytorch_weights(model,str(weights),strict=True).eval()
    with torch.no_grad(): activations=model(a.load_audio_for_model(audio)).cpu().numpy()
    with cache.with_suffix('.tmp').open('wb') as f: np.save(f,activations)
    cache.with_suffix('.tmp').replace(cache)
thresholds=json.loads(thresholds) or a.FRAME_RNN_THRESHOLDS
peaks=a.PeakPicker(thresholds=thresholds,fps=100).pick(activations,labels=a.LABELS_5)[0]
a.activations_to_pretty_midi(peaks).write(str(out/'raw.mid'))
mapping={35:'kick',38:'snare',47:'toms',42:'hi-hat',49:'cymbals'}
events=sorted([{'time':float(t),'class':mapping[p],'pitch':p} for p,times in peaks.items() for t in times],key=lambda e:e['time'])
(out/'events.json').write_text(json.dumps({'schema_version':1,'kind':'prediction','piece_id':piece,'synthetic':synthetic=='True','events':events},indent=2))
print('CPU, activations',activations.shape,'events',len(events),'cache',str(cache))
