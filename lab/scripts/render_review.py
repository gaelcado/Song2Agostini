#!/usr/bin/env python3
"""Build private notation and source crops, independent of all predictions."""
import hashlib,json,shutil,subprocess
from pathlib import Path
from fractions import Fraction
import xml.etree.ElementTree as ET
import verovio
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'work/verification/reference-preparation-v3'
OUT=ROOT/'work/verification/ui'

def add(p,t,v=None,**a):
 e=ET.SubElement(p,t,a)
 if v is not None:e.text=str(v)
 return e

def notation(measures,symbols):
 root=ET.Element('score-partwise',version='4.0');lst=add(root,'part-list');sp=add(lst,'score-part',id='P1');add(sp,'part-name','')
 part=add(root,'part',id='P1');warnings=[]
 for idx,m in measures:
  bar=add(part,'measure',number=str(idx+1));attrs=add(bar,'attributes');add(attrs,'divisions',16)
  if idx==measures[0][0]:
   ts=add(attrs,'time');add(ts,'beats',m['signature_candidate'][0]);add(ts,'beat-type',m['signature_candidate'][1])
   clef=add(attrs,'clef');add(clef,'sign','percussion');add(clef,'line',2)
  total=Fraction(m['signature_candidate'][0]*4,m['signature_candidate'][1])
  groups=[[],[],[]]
  for e in m['events']:
   groups[0 if symbols[e['symbol_id']]['staff_step_from_bottom_line']>=9 else 1 if e['symbol_id']=='K' else 2].append(e)
  if not any(groups):groups[0]=[]
  for voice,events in enumerate(groups,1):
   if voice>1:
    back=add(bar,'backup');add(back,'duration',int(total*16))
   cursor=Fraction(0)
   def gap(duration,start):
    # Every musical value stays exact; spacers are invisible, never invented audible rests.
    f=add(bar,'forward');add(f,'duration',int(duration*16));add(f,'voice',voice)
   ordered=sorted(events,key=lambda e:Fraction(e['onset_quarters']))
   for event_index,e in enumerate(ordered):
    onset=Fraction(e['onset_quarters']);dur=Fraction(e['duration_quarters'])
    chord=event_index>0 and onset==Fraction(ordered[event_index-1]['onset_quarters']) and dur==Fraction(ordered[event_index-1]['duration_quarters'])
    if (onset<cursor and not chord) or onset<0 or onset+dur>total or (onset*16).denominator!=1 or (dur*16).denominator!=1:
     warnings.append('Position ou durée non représentable: '+e['id']);continue
    if onset>cursor:gap(onset-cursor,cursor)
    n=add(bar,'note')
    if chord:add(n,'chord')
    up=add(n,'unpitched');step=symbols[e['symbol_id']]['staff_step_from_bottom_line']
    pitch=2+step;add(up,'display-step','CDEFGAB'[pitch%7]);add(up,'display-octave',4+pitch//7)
    add(n,'duration',int(dur*16));add(n,'voice',voice)
    values={Fraction(4):('whole',0),Fraction(2):('half',0),Fraction(1):('quarter',0),Fraction(1,2):('eighth',0),Fraction(1,4):('16th',0),Fraction(3,4):('eighth',1)}
    if dur in values:
     value,dot=values[dur];add(n,'type',value)
     if dot:add(n,'dot')
    else:warnings.append('Valeur atypique conservée: '+e['id'])
    add(n,'stem','up' if voice==1 else 'down')
    if not chord and dur in {Fraction(1,2),Fraction(1,4)}:
     for level in range(1,2 if dur==Fraction(1,2) else 3):
      previous=ordered[event_index-1] if event_index else None;following=ordered[event_index+1] if event_index+1<len(ordered) else None
      linked_previous=previous is not None and Fraction(previous['onset_quarters'])+Fraction(previous['duration_quarters'])==onset and Fraction(previous['duration_quarters'])==dur and int(Fraction(previous['onset_quarters']))==int(onset)
      linked_following=following is not None and onset+dur==Fraction(following['onset_quarters']) and Fraction(following['duration_quarters'])==dur and int(Fraction(following['onset_quarters']))==int(onset)
      if linked_previous or linked_following:add(n,'beam','continue' if linked_previous and linked_following else 'end' if linked_previous else 'begin',number=str(level))
    head=symbols[e['symbol_id']]['head'];add(n,'notehead',{'filled':'normal','cross':'x','circled_cross':'circle-x'}[head])
    cursor=onset+dur
   if cursor<total:gap(total-cursor,cursor)
  # Explicit source rests are shown in a separate layer, at their original rational positions.
  if m.get('rests'):
   back=add(bar,'backup');add(back,'duration',int(total*16));cursor=Fraction(0)
   for r in m['rests']:
    pos=Fraction(r['onset_quarters']);dur=Fraction(r['duration_quarters'])
    if pos<cursor or pos+dur>total:warnings.append('Silence hors mesure: '+m['id']);continue
    if pos>cursor:
     f=add(bar,'forward');add(f,'duration',int((pos-cursor)*16))
    n=add(bar,'note');add(n,'rest');add(n,'duration',int(dur*16));add(n,'voice',4);add(n,'stem','none')
    add(n,'type',{Fraction(4):'whole',Fraction(2):'half',Fraction(1):'quarter',Fraction(1,2):'eighth',Fraction(1,4):'16th'}.get(dur,'quarter'));cursor=pos+dur
 return ET.tostring(root,encoding='unicode'),warnings

def main():
 OUT.mkdir(parents=True,exist_ok=True);candidate=SOURCE/'piece_01.symbolic-candidate.json';raw=candidate.read_bytes();data=json.loads(raw)
 shutil.copyfile(candidate,OUT/'candidate.json');files={};measure_info=[];warnings=[]
 for page in range(1,4):
  prefix=OUT/f'source-{page}'
  subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','2400','-png','-singlefile',str(ROOT/'data/raw/scores/piece_01.pdf'),str(prefix)],check=True,capture_output=True)
  files[f'source-{page}']={'path':prefix.name+'.png','mime':'image/png'}
 im=Image.open(OUT/'source-1.png');w,h=im.size
 # Private crop geometry comes from visual page inspection; no temporal alignment.
 row_bounds=[(.065,.17),(.168,.269),(.281,.38),(.402,.502),(.52,.622),(.641,.744),(.763,.863),(.885,.995)]
 for row,(top,bottom) in enumerate(row_bounds,1):
  image=OUT/f'system-{row}.png';im.crop((int(.085*w),int(top*h),int(.91*w),int(bottom*h))).save(image)
  files[f'system-{row}']={'path':image.name,'mime':'image/png'}
  pair=list(enumerate(data['measures']))[(row-1)*2:row*2];xml,errs=notation(pair,data['symbols']);warnings+=errs
  (OUT/f'system-{row}.musicxml').write_text(xml)
  tk=verovio.toolkit();tk.setOptions({'pageWidth':1800,'pageHeight':500,'scale':60,'adjustPageHeight':True,'breaks':'none','header':'none','footer':'none','spacingLinear':.6})
  if not tk.loadData(xml):raise RuntimeError('Notation render failed')
  # Verovio MusicXML circle-x importer issue #4314: preserve the intended head via MEI SMuFL glyph.
  mei=tk.getMEI().replace('head.shape="slash"', 'head.shape="U+E0B3" head.auth="smufl"')
  (OUT/f'system-{row}.mei').write_text(mei)
  if not tk.loadData(mei):raise RuntimeError('MEI render failed')
  svg=tk.renderToSVG(1);(OUT/f'notation-{row}.svg').write_text(svg)
  files[f'notation-{row}']={'path':f'notation-{row}.svg','mime':'image/svg+xml'}
  for idx,m in pair:
   measure_info.append({'id':m['id'],'number':idx+1,'system':row,'page':1,'issues':m.get('issues',[]),'rational_values':sorted(set(e['duration_quarters'] for e in m['events']),key=Fraction)})
 shutil.copyfile(SOURCE/'audio-first40.wav',OUT/'audio-first40.wav');files['audio']={'path':'audio-first40.wav','mime':'audio/wav'}
 shutil.copyfile(ROOT/'data/raw/scores/piece_01.pdf',OUT/'original-source.pdf');files['original-source']={'path':'original-source.pdf','mime':'application/pdf'}
 for entry in files.values():entry['sha256']=hashlib.sha256((OUT/entry['path']).read_bytes()).hexdigest()
 manifest={'piece_id':'piece_01','candidate':'candidate.json','candidate_sha256':hashlib.sha256(raw).hexdigest(),'source_sha256':data['sources']['data/raw/scores/piece_01.pdf'],
 'source_pages':3,'digitized_pages':[1],'measures':measure_info,'files':files,'warnings':warnings,'renderer':'verovio 6.3.0','notation_policy':'Positions et durées rationnelles originales; espaces invisibles pour les voix absentes. Aucun roulement développé. Les reprises et signes non résolus se lisent dans la source.'}
 (OUT/'assets.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print('Private review assets ready; systems=8, source pages=3; renderer warnings=',len(warnings))
if __name__=='__main__':main()
