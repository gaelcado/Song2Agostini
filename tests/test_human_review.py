"""Private review contract tests, using synthetic notation only."""
import hashlib
import json
import pytest
from drum_lab.human_review import CATEGORIES, ReviewStore
from test_ui import local_server, request, session, upload, completed

@pytest.fixture
def prepared(tmp_path):
 root=tmp_path/'private';root.mkdir();candidate=root/'candidate.json';candidate.write_text('{"synthetic":true}')
 (root/'source.png').write_bytes(b'private-source');(root/'audio.wav').write_bytes(b'0123456789')
 metadata={'piece_id':'piece_01','candidate':'candidate.json','candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'source_sha256':'source-hash','measures':[{'id':'synthetic-1','system':1}], 'files':{'source-1':{'path':'source.png','mime':'image/png'},'audio':{'path':'audio.wav','mime':'audio/wav'}}}
 (root/'assets.json').write_text(json.dumps(metadata));return root,metadata

def body(metadata):
 return {'candidate_sha256':metadata['candidate_sha256'],'measures':['synthetic-1'],'answers':{i:{'status':'confirmed','comment':'<script>alert(1)</script>'} for i,_,_ in CATEGORIES},'human_validated':True,'alignment_fixed':True}

def test_review_partial_is_versioned_never_promoted(prepared):
 root,metadata=prepared;store=ReviewStore(root)
 first=store.save(body(metadata));second=store.save(body(metadata))
 assert first['id']!=second['id']
 assert not first['human_validated'] and not first['alignment_fixed']
 assert len(store.snapshot()['decisions'])==2
 assert not store.snapshot()['human_validated']
 assert json.loads((root/'candidate.json').read_text())=={'synthetic':True}

def test_review_hash_scope_and_paths_are_gated(prepared):
 root,metadata=prepared;store=ReviewStore(root)
 changed=body(metadata)|{'candidate_sha256':'stale'}
 with pytest.raises(ValueError):store.save(changed)
 with pytest.raises(ValueError):store.save(body(metadata)|{'measures':['../secret']})
 for key in ['../candidate.json','candidate.json','source-1/../../candidate.json']:
  with pytest.raises(ValueError):store.document(key)
 (root/'candidate.json').write_text('changed')
 with pytest.raises(ValueError):store.snapshot()

def test_product_has_no_private_review_access_or_mutations(local_server, prepared):
 root,metadata=prepared;server,app=local_server()
 # Historical files remain on disk, including decisions, but no product route reads them.
 store=ReviewStore(root);store.save(body(metadata))
 before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
 routes=['/verification','/verification/','/verification.html','/verification.js','/verification.css',
         '/web/verification.html','/api/verification','/api/verification/',
         '/api/verification/catalog','/api/verification/snapshot',
         '/api/verification/snapshot?piece=bench_01',
         '/api/verification/documents/source-1','/api/verification/documents/audio',
         '/api/verification/documents/motor-pdf','/api/verification/decisions']
 for auth in [{},session(server),session(server)]:
  for path in routes:
   assert request(server,'GET',path,headers=auth)[0] in {403,404}
   assert request(server,'POST',path,json.dumps(body(metadata)).encode(),auth)[0] in {403,404}
 assert {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}==before
 assert not hasattr(app,'review_root')
 auth=session(server);job=upload(server,auth);result=completed(server,auth,job)
 assert result['status']=='completed'
 assert 'candidate_sha256' not in result and 'decisions' not in result
 assert all(not v.resolve().is_relative_to(root) for v in app.jobs[job]['artifacts'].values())


def test_review_asset_hash_changes_block_documents_and_decisions(prepared):
 root,metadata=prepared
 metadata['files']['source-1']['sha256']=hashlib.sha256((root/'source.png').read_bytes()).hexdigest()
 (root/'assets.json').write_text(json.dumps(metadata))
 store=ReviewStore(root);store.save(body(metadata));(root/'source.png').write_bytes(b'replaced-source')
 with pytest.raises(ValueError):store.document('source-1')
 with pytest.raises(ValueError):store.save(body(metadata))
 assert len(list((root/'decisions').glob('*.json')))==1

def test_frozen_motor_pdf_is_private_separate_and_allowlisted(prepared):
 root,metadata=prepared;(root/'motor.pdf').write_bytes(b'predicted synthetic PDF');(root/'motor.png').write_bytes(b'preview')
 files={'motor-pdf':{'path':'motor.pdf','mime':'application/pdf'},'motor-preview':{'path':'motor.png','mime':'image/png'}}
 (root/'motor-artifacts.json').write_text(json.dumps({'piece_id':'piece_01','files':files,'label':'Frozen motor'}))
 store=ReviewStore(root);snap=store.snapshot()
 assert snap['motor']['pdf']=='motor-pdf' and 'files' not in snap
 assert store.document('motor-pdf')[0].read_bytes()==b'predicted synthetic PDF'
 assert not snap['human_validated'] and not snap['alignment_fixed']

def test_motor_documents_reject_changed_hash_and_path_escape(prepared,tmp_path):
 root,metadata=prepared
 outside=tmp_path/'outside.pdf';outside.write_bytes(b'private outside file')
 motor=root/'motor.pdf';motor.write_bytes(b'frozen synthetic PDF')
 files={'motor-pdf':{'path':'motor.pdf','mime':'application/pdf','sha256':hashlib.sha256(motor.read_bytes()).hexdigest()},
        'motor-preview':{'path':'motor.png','mime':'image/png'}}
 registry={'piece_id':'piece_01','files':files}
 (root/'motor-artifacts.json').write_text(json.dumps(registry));store=ReviewStore(root)
 motor.write_bytes(b'changed synthetic PDF')
 with pytest.raises(ValueError,match='changed'):store.document('motor-pdf')
 with pytest.raises(ValueError,match='changed'):store.save(body(metadata))
 files['motor-pdf']['path']=str(outside)
 (root/'motor-artifacts.json').write_text(json.dumps(registry))
 with pytest.raises(ValueError,match='unavailable'):store.document('motor-pdf')

@pytest.mark.parametrize('stale_files',[{}, {'motor-pdf':{'path':'motor.pdf','mime':'application/pdf'},'motor-preview':{'path':'motor.png','mime':'image/png'}}])
def test_failed_motor_run_has_message_and_no_stale_pdf_fallback(prepared,stale_files):
 root,_=prepared;(root/'motor.pdf').write_bytes(b'stale')
 (root/'motor-artifacts.json').write_text(json.dumps({'piece_id':'piece_01','state':'failed','files':stale_files,'label':'failed'}))
 store=ReviewStore(root);snapshot=store.snapshot()
 assert 'motor' not in snapshot and 'aucun PDF final' in snapshot['motor_failure']
 with pytest.raises(ValueError):store.document('motor-pdf')

@pytest.mark.parametrize('status,text',[
 ('accepted_as_readable_draft','Brouillon jugé lisible'),
 ('rejected_pedagogical_draft','Présentation à corriger'),
 ('requires_independent_review','Présentation en attente'),
])
def test_visual_motor_label_requires_exact_piece_and_pdf_hash(status,text):
 from drum_lab.human_review import motor_visual_label,VISUAL_PENDING
 feedback={'piece_id':'bench_01','artifact_sha256':{'pdf':'exact'},'visual_review':status}
 assert motor_visual_label(feedback,'bench_01','exact').startswith(text)
 assert motor_visual_label(feedback,'bench_01','changed')==VISUAL_PENDING
 assert motor_visual_label(feedback,'bench_02','exact')==VISUAL_PENDING
 assert motor_visual_label({},'bench_01','exact')==VISUAL_PENDING


def rejection_handler(reader, headers, status=403):
    """Exercise the real error response without network timing or any private assets."""
    from email.message import Message
    from io import BytesIO
    from types import SimpleNamespace
    from drum_lab.ui import Handler
    handler=Handler.__new__(Handler)
    handler.command='POST';handler._post_body_unread=True
    handler.headers=Message()
    for name,value in headers.items():handler.headers[name]=value
    handler.rfile=reader;handler.wfile=BytesIO();handler.statuses=[];handler.timeouts=[]
    handler.connection=SimpleNamespace(gettimeout=lambda:60,settimeout=handler.timeouts.append)
    handler.send_response=handler.statuses.append
    handler.send_header=lambda *args:None
    handler.end_headers=lambda:None
    return handler


def test_small_rejected_post_is_consumed_before_same_forbidden_response():
    from io import BytesIO
    reader=BytesIO(b'private request ignored')
    handler=rejection_handler(reader,{'Content-Length':str(len(reader.getvalue()))})
    def respond(status):
        assert reader.tell()==len(reader.getvalue())
        handler.statuses.append(status)
    handler.send_response=respond
    handler._json(403,{'error':'Session invalide.'})
    assert handler.statuses==[403] and json.loads(handler.wfile.getvalue())['error']=='Session invalide.'
    assert handler.timeouts[-1]==60 and handler._post_body_unread is False


@pytest.mark.parametrize('headers',[
    {'Content-Length':'65537'},
    {'Content-Length':'20','Transfer-Encoding':'chunked'},
    {'Content-Length':'invalid'},
    {},
])
def test_large_chunked_or_unknown_rejection_never_reads_body(headers):
    from types import SimpleNamespace
    reader=SimpleNamespace(read1=lambda size:pytest.fail('Unbounded rejected body must not be read'))
    handler=rejection_handler(reader,headers)
    handler._json(404,{'error':'Ressource introuvable.'})
    assert handler.statuses==[404] and handler.timeouts==[]


def test_partial_rejection_timeout_preserves_refusal_and_restores_socket():
    from types import SimpleNamespace
    reads=[]
    def timeout(size):
        reads.append(size);raise TimeoutError('partial upload')
    handler=rejection_handler(SimpleNamespace(read1=timeout),{'Content-Length':'10'})
    handler._json(403,{'error':'Session invalide.'})
    assert handler.statuses==[403] and reads==[10]
    assert 0<handler.timeouts[0]<=.250 and handler.timeouts[-1]==60


def test_rejected_slow_drip_has_one_global_deadline(monkeypatch):
    from types import SimpleNamespace
    import drum_lab.ui as module
    times=iter([0,.100,.251])
    monkeypatch.setattr(module.time,'monotonic',lambda:next(times))
    reads=[]
    def drip(size):reads.append(size);return b'x'
    handler=rejection_handler(SimpleNamespace(read1=drip),{'Content-Length':'10'})
    handler._json(403,{'error':'Session invalide.'})
    assert handler.statuses==[403] and reads==[10]
    assert handler.timeouts==[.150,60]


def test_consumed_or_partially_accepted_upload_is_not_read_again():
    from types import SimpleNamespace
    reader=SimpleNamespace(read1=lambda size:pytest.fail('Upload already handled must not be reread'))
    handler=rejection_handler(reader,{'Content-Length':'20'})
    handler._post_body_unread=False
    handler._json(400,{'error':'Transfert interrompu.'})
    assert handler.statuses==[400] and handler.timeouts==[]
