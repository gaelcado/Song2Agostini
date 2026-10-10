"""Independent final-artifact verifier. Full reference data stays on this side."""
import json
import subprocess
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
import pretty_midi
from .files import ROOT,load,write,digest
from .verification import evaluate_files


def verify_final(directory,reference=None):
    directory=Path(directory).resolve()
    private=ROOT/'work/verification'/directory.name;private.mkdir(parents=True,exist_ok=True)
    feedback={'schema_version':1,'piece_id':None,'integrity':'failed','musical_fidelity':None,
              'visual_review':'requires_independent_review','rhythmic_grid':'draft',
              'reason':'Référence symbolique validée, couverture et alignement requis.'}
    try:
        production=load(directory/'production.json');feedback['piece_id']=production['piece_id']
        record_path=directory/'record.json'
        if record_path.is_file():
            record=load(record_path)
            if (record['id']!=directory.name or record['piece_id']!=production['piece_id']
                or record.get('audio_sha256')!=production.get('audio_sha256')
                or record.get('synthetic',False)!=production.get('synthetic',False)
                or record['status']!='awaiting_verification'
                or any(production.get('config',{}).get(key)!=value for key,value in record.get('config',{}).items())):
                raise ValueError('Registre incompatible avec la production figée')
        paths={key:Path(value) for key,value in production['artifacts'].items()}
        if any(not p.resolve().is_relative_to(directory) for p in paths.values()):raise ValueError('Artefact hors dossier')
        if production['status']!='completed':raise ValueError('Production incomplète')
        hashes={key:digest(p) for key,p in paths.items()}
        if hashes!=production['artifact_sha256']:raise ValueError('Artefact modifié depuis production')
        xml=ET.parse(paths['musicxml'])
        if xml.findall('.//pitch') or not xml.findall('.//clef/sign') or any(n.text!='percussion' for n in xml.findall('.//clef/sign')):
            raise ValueError('Notation non exclusivement percussive')
        raw=pretty_midi.PrettyMIDI(str(paths['raw_midi']));quant=pretty_midi.PrettyMIDI(str(paths['midi']))
        if any(not part.is_drum for midi in (raw,quant) for part in midi.instruments):raise ValueError('Piste mélodique')
        raw_count=sum(len(part.notes) for part in raw.instruments);quant_count=sum(len(part.notes) for part in quant.instruments)
        if raw_count!=quant_count:raise ValueError('Suppression de coups non déclarée dans MIDI')
        events=load(directory/'events.json')
        if len(events['events'])!=raw_count or events['piece_id']!=production['piece_id']:raise ValueError('JSON/MIDI incompatible')
        notation=load(directory/'notation/notation.json')
        if not notation['musicxml_audit']['valid']:raise ValueError('Audit de notation invalide')
        info=subprocess.run(['pdfinfo',str(paths['pdf'])],check=True,capture_output=True,text=True,timeout=30).stdout
        pages=int(next(line.split(':')[1] for line in info.splitlines() if line.startswith('Pages:')))
        if pages<1:raise ValueError('PDF vide')
        feedback.update(integrity='passed',artifact_sha256=hashes,
                        prediction_stats={'raw_hits':raw_count,'quantized_hits':quant_count,'pdf_pages':pages,
                            'displayed_measures':notation.get('displayed_measures'),'expanded_measures':notation['measures'],
                            'quantization':notation.get('quality',{})})
        review_path=directory/'agent-feedback.json'
        if review_path.is_file():
            review=load(review_path)
            if review.get('artifact_sha256')==hashes and review.get('piece_id')==production['piece_id']:
                feedback['visual_review']=review.get('status','requires_independent_review')
                feedback['agent_review_id']=review.get('review_id')
        if reference and Path(reference).is_file():
            ref=load(reference)
            if not ref.get('synthetic',False) and not ref.get('alignment_fixed',False):
                raise ValueError('Alignement de référence non fixé')
            feedback['musical_fidelity']=evaluate_files(reference,directory/'events.json',directory.name+'-events')
            feedback['reason']=None
    except Exception:
        (private/'verification-error.log').write_text(traceback.format_exc())
        if feedback['integrity']=='failed':feedback['reason']='Contrôle des artefacts échoué ; détails réservés au vérificateur.'
    write(private/'final-feedback.json',feedback)
    write(directory/'final-feedback.json',feedback)
    return feedback
