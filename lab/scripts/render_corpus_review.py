#!/usr/bin/env python3
"""Private MIDI source reading projections. No predictions, no reference promotion."""
from pathlib import Path
import json,hashlib,shutil
from fractions import Fraction
import mido,verovio
from render_review import notation
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/verification/ui'
POSITIONS={35:-1,36:-1,38:5,40:5,37:3,42:9,44:9,46:9,49:11,51:9,57:11,41:1,43:1,45:4,47:4,48:7,50:7}

def main():
 manifest=json.loads((ROOT/'data/benchmark-manifest.json').read_text());catalog=[]
 for item in manifest['pieces']:
  piece=item['id'];folder=OUT/piece;folder.mkdir(parents=True,exist_ok=True)
  original=ROOT/item['score'];raw=original.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=item['score_sha256']:raise ValueError('MIDI original changed')
  shutil.copyfile(original,folder/'original.mid');midi=mido.MidiFile(original);signature=(4,4);signatures=[];tempos=[];hits=[];endtick=0
  for track in midi.tracks:
   ticks=0
   for msg in track:
    ticks+=msg.time;endtick=max(endtick,ticks)
    if msg.type=='time_signature':signatures.append((ticks,msg.numerator,msg.denominator))
    if msg.type=='set_tempo':tempos.append((ticks,msg.tempo))
    if msg.type=='note_on' and msg.channel==9 and msg.velocity>0:hits.append((ticks,msg.note))
  if signatures:signature=tuple(sorted(signatures)[0][1:])
  beats=Fraction(signature[0]*4,signature[1]);count=max(1,int(Fraction(endtick,midi.ticks_per_beat)//beats)+1)
  symbols={};measures=[{'id':f'{piece}-m{i+1}','signature_candidate':list(signature),'events':[],'issues':[],'rests':[]} for i in range(count)]
  # This is a labeled reading projection, not a normalized truth or a timing reference.
  for tick,pitch in hits:
   native=Fraction(tick,midi.ticks_per_beat);bar=int(native//beats);onset=native-bar*beats
   projected=Fraction(round(onset*4),4)
   if projected>=beats:bar+=1;projected=Fraction(0)
   if bar>=len(measures):measures.append({'id':f'{piece}-m{bar+1}','signature_candidate':list(signature),'events':[],'issues':[],'rests':[]})
   symbol=str(pitch);symbols[symbol]={'staff_step_from_bottom_line':POSITIONS.get(pitch,5),'head':'circled_cross' if pitch==46 else 'cross' if pitch in {37,42,44,49,51,57} else 'filled'}
   measures[bar]['events'].append({'id':f'{piece}-t{tick}-n{pitch}','symbol_id':symbol,'onset_quarters':str(projected),'duration_quarters':'1/4','native_tick':tick})
  # Chord/overlap-free independent glyph voices for reading; coincident MIDI hits remain explicit native file.
  for m in measures:
   unique={}
   for e in m['events']:
    key=(e['symbol_id'],e['onset_quarters']);unique[key]=e
   if len(unique)!=len(m['events']):m['issues'].append('Frappes rapprochées sur un même instrument fusionnées pour la lecture; MIDI natif inchangé.')
   m['events']=list(unique.values())
  files={'original-midi':{'path':'original.mid','mime':'audio/midi'},'audio':{'path':str((ROOT/item['audio']).resolve()),'mime':'audio/wav'}}
  # Audio link is resolved only after the manifest hash has been checked; copy avoids serving arbitrary paths.
  audio=ROOT/item['audio']
  if hashlib.sha256(audio.read_bytes()).hexdigest()!=item['audio_sha256']:raise ValueError('Audio changed')
  audio_name='audio'+audio.suffix.lower();shutil.copyfile(audio,folder/audio_name);files['audio']['path']=audio_name;files['audio']['mime']={'.wav':'audio/wav','.mp3':'audio/mpeg','.flac':'audio/flac'}.get(audio.suffix.lower(),'application/octet-stream')
  infos=[];warnings=[]
  # Assign symbols to separate voices by staff group; notation helper reserves K for kick.
  for m in measures:
   for e in m['events']:
    if int(e['symbol_id']) in {35,36}:
     symbols['K']=symbols[e['symbol_id']];e['symbol_id']='K'
  for offset in range(0,len(measures),2):
   row=offset//2+1;pair=list(enumerate(measures))[offset:offset+2];xml,errs=notation(pair,symbols);warnings+=errs
   tk=verovio.toolkit();tk.setOptions({'pageWidth':1800,'pageHeight':500,'scale':60,'adjustPageHeight':True,'breaks':'none','header':'none','footer':'none'})
   if not tk.loadData(xml):raise RuntimeError('MIDI projection render failed')
   mei=tk.getMEI().replace('head.shape="slash"','head.shape="U+E0B3" head.auth="smufl"');tk.loadData(mei)
   (folder/f'system-{row}.svg').write_text(tk.renderToSVG(1));files[f'system-{row}']={'path':f'system-{row}.svg','mime':'image/svg+xml'}
   for index,m in pair:infos.append({'id':m['id'],'number':index+1,'system':row,'page':1,'issues':m['issues']})
  if len(set(signatures))>1:warnings.append('Changements de signature MIDI présents : la lecture utilise seulement la signature initiale; vérifier le MIDI original.')
  unplaced=sorted(set(pitch for _,pitch in hits)-set(POSITIONS))
  if unplaced:warnings.append('Percussions MIDI GM sans position conventionnelle dans cette vue: '+', '.join(map(str,unplaced))+'. Leur position sur la ligne centrale est une convention de lecture, pas une identification caisse claire.')
  if not hits:warnings.append('Aucune piste au canal percussion GM 10 : aucune batterie fabriquée.')
  policy='Lecture partition MIDI source : positions projetées sur la double croche; valeurs de lecture en doubles croches, pas durées validées. Seul le canal percussion GM 10 est affiché. Le MIDI original conserve tous ses ticks, notes et pistes; aucun alignement audio n’est fixé.'
  data={'piece_id':piece,'title':item['title'],'author':item['author'],'license':item['license'],'source_url':item['source_url'],'pairing_status':item['pairing_status'],'reference_kind':item['reference_kind'],'candidate':'original.mid','candidate_sha256':item['score_sha256'],'source_sha256':item['score_sha256'],'source_pages':1,'digitized_pages':[],'measures':infos,'files':files,'warnings':warnings,'notation_policy':policy,'native_midi':True,'drum_hits':len(hits),'human_validated':False,'alignment_fixed':False}
  for entry in files.values():entry['sha256']=hashlib.sha256((folder/entry['path']).read_bytes()).hexdigest()
  (folder/'assets.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));catalog.append({k:data[k] for k in ['piece_id','title','author','license','reference_kind']})
 (OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2));print('Private source-MIDI reading views:',len(catalog))
if __name__=='__main__':main()
