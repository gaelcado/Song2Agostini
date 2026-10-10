"""Côté vérification uniquement : la référence ne traverse pas le retour recherche."""
import datetime
import math
from pathlib import Path

from .files import ROOT, digest, load, write
from .evaluation import evaluate


def feedback(report):
    """Allowlist explicite : métriques, jamais notes, FP/FN horodatés ou correction."""
    result = {'schema_version': 1, 'piece_id': report['piece_id'],
              'synthetic': report['synthetic'], 'tolerances': {}}
    for tolerance, values in report['tolerances'].items():
        per_class = {}
        for cls, metrics in values['per_class'].items():
            per_class[cls] = {
                **{key: metrics[key] for key in ('tp', 'fp', 'fn', 'precision', 'recall', 'f1')},
                'unscored_additional':metrics.get('unscored_additional',0),
            }
        result['tolerances'][tolerance] = {
            'macro_f1': values['macro_f1'],
            'micro': {key: values['micro'][key] for key in ('tp', 'fp', 'fn', 'precision', 'recall', 'f1')},
            'per_class': per_class,
        }
    # Diagnostic par passage grossier ; aucune liste de notes attendues.
    passages = {}
    for cls, errors in report['tolerances']['50']['errors'].items():
        for name, key in (('false_positive', 'fp'), ('false_negative', 'fn')):
            for event in errors[name]:
                start = 10 * math.floor(event['time'] / 10)
                counts = passages.setdefault(start, {}).setdefault(cls, {'fp': 0, 'fn': 0})
                counts[key] += 1
    result['passages_10s'] = [
        {'start': start, 'end': start + 10, 'per_class': passages[start]}
        for start in sorted(passages)
    ]
    return result


def evaluate_files(reference, prediction_path, private_name=None):
    reference_hash = digest(reference)
    prediction_hash = digest(prediction_path)
    report = evaluate(load(reference), load(prediction_path))
    public = feedback(report)
    public['prediction_sha256'] = prediction_hash
    private = ROOT / 'work/verification' / (private_name or ('evaluation-' + reference_hash + '-' + prediction_hash))
    private.mkdir(parents=True, exist_ok=True)
    write(private / 'metrics.json', report)
    write(private / 'record.json', {
        'piece_id': report['piece_id'], 'reference_sha256': reference_hash,
        'prediction_sha256': prediction_hash,
        'evaluation_sha256': digest(ROOT / 'configs/evaluation.v2.json'),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    return public


def verify_run(reference, run_directory):
    out = Path(run_directory).resolve()
    record = load(out / 'record.json')
    prediction_path = out / 'events.json'
    prediction = load(prediction_path)
    if record['piece_id'] != prediction['piece_id']:
        raise ValueError('Identifiant du run incompatible avec la prédiction')
    # Le retour est une projection des champs autorisés, pas le rapport complet.
    public = evaluate_files(reference, prediction_path, out.name)
    write(out / 'feedback.json', public)
    return public
