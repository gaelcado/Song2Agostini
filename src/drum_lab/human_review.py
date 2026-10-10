"""Private human review. Never imported by transcription engines or evaluation."""
from __future__ import annotations
import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = [
 ('lecture', 'Notes, silences et durées', 'Comparer les têtes, les positions et les valeurs avec la feuille. Une croche vaut un demi-temps, une double croche un quart; le point ajoute la moitié de la valeur.'),
 ('mapping', 'Légende des instruments', 'Les classes sont proposées. Confirmer les croix, les croix cerclées et les positions sur la portée; une croix centrale ne suffit pas à identifier un instrument.'),
 ('reprises', 'Reprises et ordre de lecture', 'Vérifier le sens de X8 et X3, et le nombre total de passages. Les mesures affichées sont les mesures écrites, sans déplier les reprises.'),
 ('ornements', 'Roulements et signes de jeu', 'Les roulements ne sont pas transformés en frappes inventées. Préciser les signes carré/rond et laisser incertain ce qui reste illisible.'),
 ('couverture', 'Exhaustive ou simplifiée ?', 'Si la feuille est pédagogique, les petites notes absentes ne deviennent pas automatiquement des erreurs. Décrire ce qui est réellement évaluable.'),
 ('pages', 'Couverture des pages', 'Seule la première page a été saisie. Les pages 2 et 3 sont consultables comme sources, sans proposition de notes.'),
 ('alignement', 'Repères dans l’audio', 'Le lecteur contient les 40 premières secondes. Relever vous-même des premiers temps, en secondes; aucun clic ne fixe un alignement ni un tempo.'),
 ('conclusion', 'Décision et réserves', 'Ces décisions concernent seulement votre sélection. Elles ne valident ni toute la référence ni son alignement; les corrections restent des commentaires privés.'),
]

VISUAL_PENDING = 'Présentation en attente de vérification ; fidélité musicale non mesurée'
VISUAL_LABELS = {
    'accepted_as_readable_draft': 'Brouillon jugé lisible par le vérificateur ; fidélité musicale non mesurée',
    'rejected_pedagogical_draft': 'Présentation à corriger ; fidélité musicale non mesurée',
}

def motor_visual_label(feedback, piece_id, pdf_sha256):
    """Only certify presentation for the exact frozen PDF reviewed."""
    if not isinstance(feedback, dict) or feedback.get('piece_id') != piece_id:
        return VISUAL_PENDING
    hashes=feedback.get('artifact_sha256')
    if not isinstance(hashes, dict) or not pdf_sha256 or hashes.get('pdf') != pdf_sha256:
        return VISUAL_PENDING
    return VISUAL_LABELS.get(feedback.get('visual_review'), VISUAL_PENDING)


class ReviewStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.assets = self.root / 'assets.json'

    def manifest(self):
        data = json.loads(self.assets.read_text())
        candidate = self.safe(data['candidate'])
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != data['candidate_sha256']:
            raise ValueError('Candidate changed; rerender required')
        motor=self.root/'motor-artifacts.json'
        if motor.is_file():
            extra=json.loads(motor.read_text())
            if extra.get('piece_id')==data['piece_id'] and extra.get('state')=='failed':
                data['motor_failure']='Génération échouée : aucun PDF final disponible.'
            elif extra.get('piece_id')==data['piece_id'] and set(extra.get('files',{}))=={'motor-pdf','motor-preview'}:
                data['files'].update(extra['files'])
                data['motor']={'pdf':'motor-pdf','preview':'motor-preview','label':str(extra.get('label','Sortie moteur figée'))[:250]}
        return data

    def safe(self, name):
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError('Private file unavailable')
        return path

    def snapshot(self):
        data = self.manifest()
        data = {k:v for k,v in data.items() if k not in {'candidate','files'}}
        decisions=[]
        for path in sorted((self.root / 'decisions').glob('*.json')):
            item=json.loads(path.read_text())
            if item.get('candidate_sha256') == data['candidate_sha256']:
                decisions.append(item)
        return data | {'categories':[{'id':i,'title':t,'help':h} for i,t,h in CATEGORIES], 'decisions':decisions,
                       'human_validated':False,'alignment_fixed':False}

    def document(self, key):
        files=self.manifest()['files']
        if key not in files: raise ValueError('Not allowlisted')
        item=files[key]
        path=self.safe(item['path'])
        if item.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Private document changed')
        return path,item['mime']

    def save(self, body):
        data=self.manifest()
        for item in data['files'].values():
            if item.get('sha256') and hashlib.sha256(self.safe(item['path']).read_bytes()).hexdigest()!=item['sha256']:
                raise ValueError('Reviewed asset changed; rerender required')
        if body.get('candidate_sha256') != data['candidate_sha256']: raise ValueError('Candidate hash mismatch')
        measures=body.get('measures')
        valid={m['id'] for m in data['measures']}
        if not isinstance(measures,list) or not measures or len(measures)>16 or any(m not in valid for m in measures):
            raise ValueError('Invalid measure scope')
        answers=body.get('answers')
        if not isinstance(answers,dict) or set(answers)!={i for i,_,_ in CATEGORIES}: raise ValueError('Invalid checklist')
        clean={}
        for key,value in answers.items():
            if not isinstance(value,dict) or value.get('status') not in {'confirmed','correct','uncertain'}: raise ValueError('Invalid answer')
            comment=value.get('comment','')
            if not isinstance(comment,str) or len(comment)>4000: raise ValueError('Invalid comment')
            clean[key]={'status':value['status'],'comment':comment}
        record={'id':datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+secrets.token_hex(6),
                'created_utc':datetime.now(timezone.utc).isoformat(),'candidate_sha256':data['candidate_sha256'],
                'source_sha256':data['source_sha256'],'piece_id':data['piece_id'],
                'measures':sorted(set(measures)), 'answers':clean,'human_validated':False,'alignment_fixed':False,
                'scope':'partial_private_review'}
        folder=self.root/'decisions';folder.mkdir(exist_ok=True)
        (folder/(record['id']+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2))
        return record
