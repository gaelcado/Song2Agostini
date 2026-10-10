"""Independent evaluator. Never passed into an inference adapter."""
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from jsonschema import validate

from .files import ROOT, load, resource_path
CLASSES = ('kick', 'snare', 'hi-hat', 'toms', 'cymbals')

def check(doc, kind):
    if kind == 'reference' and not doc.get('synthetic', False):
        if not doc.get('human_validated', False):
            raise ValueError('Référence réelle non validée humainement')
        if not doc.get('alignment_fixed', False):
            raise ValueError('Alignement de référence réel non fixé indépendamment des prédictions')
    validate(doc, load(resource_path('configs/events.schema.json')))
    if doc['kind'] != kind:
        raise ValueError(f'Document attendu : {kind}')
    for e in doc['events']:
        if not math.isfinite(e['time']):
            raise ValueError('Temps non fini')
    if kind == 'reference':
        for c in doc['coverage']:
            if not all(math.isfinite(c[k]) for k in ('start','end')) or c['end'] <= c['start']:
                raise ValueError('Couverture invalide')

def match(ref, pred, tolerance):
    """Augmented assignment: missing costs dominate all valid distances."""
    n, m = len(ref), len(pred)
    if not n or not m:
        return []
    penalty = (n+m+1)*(tolerance+1)
    cost = np.full((n+m,n+m), penalty*4)
    distances = np.abs(np.subtract.outer(ref,pred))
    cost[:n,:m] = np.where(distances <= tolerance+1e-12, distances, penalty*4)
    cost[:n,m:] = penalty
    cost[n:,:m] = penalty
    cost[n:,m:] = 0
    rows, cols = linear_sum_assignment(cost)
    return [(int(i),int(j),float(distances[i,j])) for i,j in zip(rows,cols)
            if i<n and j<m and distances[i,j]<=tolerance+1e-12]

def metrics(tp, fp, fn):
    return {'tp':tp,'fp':fp,'fn':fn,
            'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None,
            'f1':2*tp/(2*tp+fp+fn) if tp+fn else None}

def evaluate(reference, prediction, tolerances=(50,25)):
    check(reference,'reference'); check(prediction,'prediction')
    if reference['piece_id'] != prediction['piece_id'] or reference.get('synthetic',False)!=prediction.get('synthetic',False):
        raise ValueError('Identifiants ou nature synthétique incompatibles')
    def covered(e):
        return any(c['start']<=e['time']<c['end'] and e['class'] in c['classes'] for c in reference['coverage'])
    refs=[e for e in reference['events'] if covered(e)]
    preds=[e for e in prediction['events'] if covered(e)]
    result={'synthetic':reference.get('synthetic',False),'piece_id':reference['piece_id'],
            'ignored_reference':len(reference['events'])-len(refs),
            'ignored_prediction':len(prediction['events'])-len(preds),'tolerances':{},
            'structure_metrics':None,'musical_placement_metrics':None}
    for ms in tolerances:
        if not math.isfinite(ms) or ms<=0: raise ValueError('Tolérance invalide')
        per={}; errors={}; totals=[0,0,0]; f1=[]; complete=True
        for cls in CLASSES:
            r=[e for e in refs if e['class']==cls]; p=[e for e in preds if e['class']==cls]
            pairs=match([e['time'] for e in r],[e['time'] for e in p],ms/1000)
            ri={i for i,j,d in pairs}; pj={j for i,j,d in pairs}
            class_coverage=[c for c in reference['coverage'] if cls in c['classes']]
            absence_evaluable=all(c.get('absence_evaluable', reference.get('synthetic',False)) for c in class_coverage)
            scored_fp=[e for j,e in enumerate(p) if j not in pj and any(
                c['start']<=e['time']<c['end'] and cls in c['classes'] and
                c.get('absence_evaluable',reference.get('synthetic',False)) for c in reference['coverage'])]
            per[cls]=metrics(len(pairs),len(scored_fp),len(r)-len(pairs))
            per[cls]['unscored_additional']=len(p)-len(pairs)-len(scored_fp)
            if not absence_evaluable:
                per[cls].update(fp=None,precision=None,f1=None)
                if r or p: complete=False
            totals[0]+=len(pairs);totals[1]+=len(scored_fp);totals[2]+=len(r)-len(pairs)
            if r and per[cls]['f1'] is not None: f1.append(per[cls]['f1'])
            errors[cls]={'false_negative':[e for i,e in enumerate(r) if i not in ri],
                         'false_positive':scored_fp,
                         'matched_distances_ms':[d*1000 for i,j,d in pairs]}
        micro=metrics(*totals)
        if not complete: micro.update(fp=None,precision=None,f1=None)
        result['tolerances'][str(ms)]={'per_class':per,'micro':micro,
            'macro_f1':sum(f1)/len(f1) if f1 and complete else None,'errors':errors,
            'absence_policy':'explicit_coverage_required_for_real_references',
            'precision_evaluable':complete}
    return result
