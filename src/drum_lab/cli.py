import argparse
import json
import platform
import shutil
from pathlib import Path
from .files import ROOT, load, env_python
from .runner import run
from .pieces import PIECE_IDS, RUN_IDS
from .files import write
from .adapters import adtof

def validate_manifest(path):
    doc=load(path); pieces=doc.get('pieces',[])
    if doc.get('schema_version')!=1 or {p.get('id') for p in pieces}!={'piece_01','piece_02'} or len(pieces)!=2: raise ValueError('Deux identifiants piece_01 et piece_02 requis')
    errors=[]
    for p in pieces:
        if p['role']!=('development' if p['id']=='piece_01' else 'control'): errors.append(f"{p['id']}: rôle incorrect")
        for k in ('audio','score','reference'):
            if not p.get(k) or not (ROOT/p[k]).is_file(): errors.append(f"{p['id']}: {k} absent ({p.get(k)})")
        if not p.get('annotation',{}).get('human_validated') or not p.get('annotation',{}).get('alignment_fixed'): errors.append(f"{p['id']}: référence ou alignement non validés")
    if errors: raise ValueError('\n'.join(errors))
    return {'valid':True,'pieces':2}

def main():
    parser=argparse.ArgumentParser(description='Laboratoire local de batterie')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    p=sub.add_parser('benchmark'); p.add_argument('configs'); p.add_argument('--only',nargs='+'); p.add_argument('--percussion',action='store_true')
    p=sub.add_parser('verify-final'); p.add_argument('directory'); p.add_argument('--reference')
    p=sub.add_parser('cycle'); p.add_argument('audio'); p.add_argument('configs'); p.add_argument('--piece',choices=RUN_IDS,required=True); p.add_argument('--reference'); p.add_argument('--synthetic',action='store_true'); p.add_argument('--resume-run')
    p=sub.add_parser('serve'); p.add_argument('--port',type=int,default=8765)
    p=sub.add_parser('validate-manifest'); p.add_argument('path')
    p=sub.add_parser('evaluate'); p.add_argument('reference'); p.add_argument('prediction'); p.add_argument('--out')
    p=sub.add_parser('verify-run'); p.add_argument('reference'); p.add_argument('run_directory')
    p=sub.add_parser('run'); p.add_argument('audio'); p.add_argument('configs'); p.add_argument('--piece',choices=RUN_IDS,required=True); p.add_argument('--synthetic',action='store_true')
    p=sub.add_parser('transcribe'); p.add_argument('audio'); p.add_argument('--out',required=True); p.add_argument('--piece',choices=PIECE_IDS,required=True)
    p=sub.add_parser('engrave'); p.add_argument('midi'); p.add_argument('--grid',required=True); p.add_argument('--out',required=True); p.add_argument('--title',default='Batterie - transcription automatique')
    args=parser.parse_args()
    try:
        if args.command=='serve':
            from .ui import serve
            serve(args.port)
            return
        if args.command=='doctor':
            from .engraving import renderer
            result={'python':platform.python_version(),'machine':platform.machine(),'project':str(ROOT),'musescore':renderer(),'environments':{n:env_python(n).exists() for n in ('adtof','demucs','allinone','drumscript')},'real_benchmark':'pending_validated_references'}
        elif args.command=='benchmark':
            from .benchmark import benchmark
            result=benchmark(load(args.configs),args.only,args.percussion)
        elif args.command=='transcribe':
            from .pipeline import generate
            from .titles import audio_title
            result=generate(args.audio,args.out,piece_id=args.piece,title=audio_title(args.audio))
        elif args.command=='verify-final':
            from .final_verification import verify_final
            result=verify_final(args.directory,args.reference)
        elif args.command=='cycle':
            from .optimization import cycle
            result=cycle(args.audio,load(args.configs),args.piece,args.reference,args.synthetic,args.resume_run)
        elif args.command=='engrave':
            from .engraving import engrave
            result=engrave(args.midi,load(args.grid),args.out,args.title)
        elif args.command=='validate-manifest': result=validate_manifest(args.path)
        elif args.command=='verify-run':
            from .verification import verify_run
            result=verify_run(args.reference,args.run_directory)
        elif args.command=='evaluate':
            from .verification import evaluate_files
            result=evaluate_files(args.reference,args.prediction)
            if args.out: write(args.out,result)
        else: result=run(args.audio,load(args.configs),args.piece,args.synthetic)
        print(json.dumps(result,indent=2,allow_nan=False))
    except Exception as e:
        if args.command in ('verify-run','verify-final','cycle','evaluate','validate-manifest'):
            # Une erreur de schéma peut inclure des notes de référence.
            import traceback
            import uuid
            private=ROOT/'work/verification/errors'
            private.mkdir(parents=True,exist_ok=True)
            (private/(uuid.uuid4().hex+'.log')).write_text(traceback.format_exc())
            parser.exit(2,'Erreur de vérification : détails réservés au vérificateur dans work/verification/errors.\n')
        parser.exit(2,f'Erreur : {e}\n')
if __name__=='__main__': main()
