from pathlib import Path
import json,wave
import numpy as np
from drum_lab.evaluation import evaluate,ROOT
from drum_lab.runner import write
from drum_lab.engraving import engrave
import pretty_midi
out=ROOT/'work/synthetic';out.mkdir(parents=True,exist_ok=True)
r={'schema_version':1,'kind':'reference','piece_id':'synthetic','synthetic':True,'human_validated':False,'coverage':[{'start':0,'end':3,'classes':['kick','snare','hi-hat','toms','cymbals']}],'events':[{'time':.5,'class':'kick'},{'time':1,'class':'snare'}]}
p={'schema_version':1,'kind':'prediction','piece_id':'synthetic','synthetic':True,'events':[{'time':.51,'class':'kick'},{'time':1.02,'class':'snare'},{'time':1.03,'class':'snare'}]}
write(out/'reference.json',r);write(out/'prediction.json',p);write(out/'metrics.json',evaluate(r,p))
midi=pretty_midi.PrettyMIDI(initial_tempo=120);kit=pretty_midi.Instrument(0,is_drum=True)
for event in p['events']:
    pitch={'kick':36,'snare':38}[event['class']]
    kit.notes.append(pretty_midi.Note(100,pitch,event['time'],event['time']+.1))
midi.instruments.append(kit);midi.write(str(out/'raw.mid'))
engrave(out/'raw.mid',{'bpm':120,'duration_seconds':3},out/'notation','Fixture synthétique')
sr=22050;t=np.arange(sr*3)/sr;y=np.zeros_like(t)
for onset in (.5,1,1.5,2):
    dt=t-onset; y+=np.where(dt>=0,.4*np.sin(2*np.pi*80*dt)*np.exp(-np.maximum(dt,0)*35),0)
with wave.open(str(out/'audio.wav'),'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((y*32767).astype('<i2').tobytes())
print('Fixtures synthétiques et exports MIDI/MusicXML créés ; aucun benchmark musical.')
