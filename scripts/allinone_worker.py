import sys
from pathlib import Path
import allin1

audio,out=sys.argv[1:];out=Path(out);out.mkdir(parents=True,exist_ok=True)
allin1.analyze(audio,out_dir=out,device='cpu',demix_dir=out/'demix',spec_dir=out/'spec',keep_byproducts=True,multiprocess=False)
