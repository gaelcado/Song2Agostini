import itertools
import inspect
import math
import pytest
from drum_lab.evaluation import match, evaluate, check, CLASSES
from drum_lab.adapters import adtof

def doc(kind,events):
    d={'schema_version':1,'kind':kind,'piece_id':'synthetic','synthetic':True,'events':[{'time':t,'class':c} for t,c in events]}
    if kind=='reference': d.update(human_validated=False,coverage=[{'start':0,'end':10,'classes':list(CLASSES)}])
    return d

def test_greedy_trap():
    assert len(match([.04,.09],[0,.05],.05))==2

def test_min_distance():
    assert match([1],[.97,1.01],.05)[0][1]==1

@pytest.mark.parametrize('delta,count',[(.025,1),(.025001,0),(.05,0)])
def test_tolerance(delta,count):
    assert len(match([1],[1+delta],.025))==count

def test_duplicates_and_absent_class():
    r=evaluate(doc('reference',[(1,'kick')]),doc('prediction',[(1,'kick'),(1,'kick'),(2,'snare')]))['tolerances']['50']
    assert r['micro']['tp']==1 and r['micro']['fp']==2
    assert r['macro_f1']==pytest.approx(2/3)
    assert r['per_class']['snare']['f1'] is None

def test_empty():
    r=evaluate(doc('reference',[]),doc('prediction',[(1,'kick')]))['tolerances']['50']
    assert r['macro_f1'] is None and r['micro']['f1'] is None
    r=evaluate(doc('reference',[(1,'kick')]),doc('prediction',[]))['tolerances']['50']
    assert r['macro_f1']==0

def test_coverage():
    r=doc('reference',[(1,'kick')]); r['coverage']=[{'start':0,'end':2,'classes':['kick']}]
    result=evaluate(r,doc('prediction',[(1,'kick'),(1,'snare'),(2,'kick')]))
    assert result['ignored_prediction']==2
    assert result['tolerances']['50']['macro_f1']==1

@pytest.mark.parametrize('time',[-1,float('nan'),float('inf')])
def test_bad_time(time):
    with pytest.raises(Exception): check(doc('prediction',[(time,'kick')]),'prediction')

def test_human_validation_required():
    r=doc('reference',[(1,'kick')]); r['synthetic']=False
    with pytest.raises(ValueError): check(r,'reference')

def test_identity():
    p=doc('prediction',[]);p['piece_id']='piece_02'
    with pytest.raises(ValueError): evaluate(doc('reference',[]),p)

def test_adapter_has_no_reference_argument():
    assert 'reference' not in inspect.signature(adtof).parameters

def test_matching_against_exhaustive_small_cases():
    # All assignments for small instances verify cardinality and distance jointly.
    for r in itertools.combinations_with_replacement([0,.04,.08],2):
        for p in itertools.combinations_with_replacement([0,.04,.08],3):
            possibilities=[]
            for choices in itertools.product([-1,0,1,2],repeat=2):
                used=[j for j in choices if j>=0]
                if len(used)!=len(set(used)): continue
                if any(j>=0 and abs(r[i]-p[j])>.050000000001 for i,j in enumerate(choices)): continue
                possibilities.append((len(used),sum(abs(r[i]-p[j]) for i,j in enumerate(choices) if j>=0)))
            best=sorted(possibilities,key=lambda x:(-x[0],x[1]))[0]
            pairs=match(r,p,.05)
            assert len(pairs)==best[0]
            assert sum(d for i,j,d in pairs)==pytest.approx(best[1])

def test_missing_manifest(tmp_path):
    from drum_lab.cli import validate_manifest
    with pytest.raises(FileNotFoundError): validate_manifest(tmp_path/'absent.json')

def test_incomplete_manifest():
    from drum_lab.cli import validate_manifest
    from drum_lab.evaluation import ROOT
    with pytest.raises(ValueError,match='audio absent'): validate_manifest(ROOT/'data/manifest.example.json')

def test_run_bounds_and_control_gate():
    from drum_lab.runner import run
    with pytest.raises(ValueError,match='12 variantes'): run('absent',[{}]*14,'piece_01')
    with pytest.raises(ValueError,match='seul contrôle'): run('absent',[{},{}],'piece_02')


def test_simplified_reference_does_not_score_extra_notes_as_errors():
    r=doc('reference',[(1,'kick')]);r['synthetic']=False;r['human_validated']=True
    r['alignment_fixed']=True
    p=doc('prediction',[(1,'kick'),(2,'kick')]);p['synthetic']=False
    report=evaluate(r,p)['tolerances']['50']
    assert report['per_class']['kick']['unscored_additional']==1
    assert report['per_class']['kick']['recall']==1
    assert report['per_class']['kick']['fp'] is None
    assert report['micro']['f1'] is None and report['macro_f1'] is None


def test_explicit_absence_coverage_allows_precision_for_real_reference():
    r=doc('reference',[(1,'kick')]);r['synthetic']=False;r['human_validated']=True
    r['alignment_fixed']=True
    r['coverage'][0]['absence_evaluable']=True
    p=doc('prediction',[(1,'kick'),(2,'kick')]);p['synthetic']=False
    report=evaluate(r,p)['tolerances']['50']
    assert report['per_class']['kick']['fp']==1
    assert report['macro_f1']==pytest.approx(2/3)


def test_real_reference_requires_independently_fixed_alignment():
    r=doc('reference',[(1,'kick')]);r['synthetic']=False;r['human_validated']=True
    p=doc('prediction',[(1,'kick')]);p['synthetic']=False
    with pytest.raises(ValueError,match='Alignement'):evaluate(r,p)
    r['alignment_fixed']=False
    with pytest.raises(ValueError,match='Alignement'):evaluate(r,p)


@pytest.mark.parametrize('synthetic',[False,None])
@pytest.mark.parametrize('field,value',[('human_validated',None),('human_validated',False),
                                       ('alignment_fixed',None),('alignment_fixed',False)])
def test_schema_requires_real_reference_validation(synthetic,field,value):
    from jsonschema import validate,ValidationError
    from drum_lab.files import ROOT,load
    r=doc('reference',[]);r.update(human_validated=True,alignment_fixed=True)
    if synthetic is None:r.pop('synthetic')
    else:r['synthetic']=synthetic
    if value is None:r.pop(field)
    else:r[field]=value
    with pytest.raises(ValidationError):validate(r,load(ROOT/'configs/events.schema.json'))


def test_schema_keeps_synthetic_fixture_exception():
    from jsonschema import validate
    from drum_lab.files import ROOT,load
    validate(doc('reference',[]),load(ROOT/'configs/events.schema.json'))
