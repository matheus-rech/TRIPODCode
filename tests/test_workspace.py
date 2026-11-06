"""Offline service/API integration: no credentials or model requests."""
import base64
import json
import threading
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.api import create_app
from src.tripod.store import Store
from src.tripod.jobs import Jobs
from src.tripod.datasets import demo_records, evaluation, normalize, parse_upload
from src.tripod.provenance import digest

TOKEN = 'test-session-token-' * 4
HEADERS = {'Authorization': 'Bearer ' + TOKEN}

def terminal(store, identifier):
    for _ in range(200):
        job = store.job(identifier)
        if job['state'] not in ('queued','running','cancelling'): return job
        time.sleep(.01)
    raise AssertionError('Job did not finish')

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        client.headers.update(HEADERS)
        yield client

def test_auth_origin_and_host(client):
    assert client.get('/api/health', headers={'Authorization':''}).status_code == 401
    assert client.get('/api/health', headers={'Origin':'https://evil.example'}).status_code == 403
    assert client.get('/api/health', headers={'Host':'evil.example'}).status_code == 403
    assert client.get('/api/health').json()['ready']

def test_demo_end_to_end_export_and_evaluation(client):
    dataset = client.post('/api/datasets/demo').json()
    run = client.post('/api/jobs', json={'dataset_id':dataset['id']}).json()
    done = terminal(client.app.state.store, run['id'])
    assert done['state'] == 'incomplete' and done['progress'] == 6
    results = client.get(f"/api/jobs/{run['id']}/results").json()
    assert {r['status'] for r in results} == {'succeeded','missing','failed'}
    negative = next(r for r in results if r['record_id']=='demo-002')
    assert negative['assessment']['is_match'] is False
    comparison = client.get(f"/api/jobs/{run['id']}/evaluation").json()['metrics'][0]
    assert (comparison['n'], comparison['excluded'], comparison['tp'], comparison['tn']) == (4,2,2,2)
    exported = client.get(f"/api/jobs/{run['id']}/export").json()
    assert exported['job']['provenance']['input_sha256'] == dataset['sha256']
    assert TOKEN not in json.dumps(exported)
    assert client.get(f"/api/jobs/{run['id']}/export?format=csv").text.startswith('record_id,status')
    assert client.get('/api/datasets/'+dataset['id']).json()['records'][0]['human']['article']['is_match'] is True

def test_repository_demo_distinguishes_null_and_inapplicable(client):
    dataset = client.post('/api/datasets/demo').json()
    run = client.post('/api/jobs',json={'dataset_id':dataset['id'],'stage':'repository'}).json()
    terminal(client.app.state.store,run['id'])
    results = client.get(f"/api/jobs/{run['id']}/results").json()
    missing_readme = next(r for r in results if r['record_id']=='demo-005')
    assert missing_readme['assessment']['contains_readme'] is False
    assert missing_readme['assessment']['readme_purpose_and_outputs'] is None
    assert next(r for r in results if r['record_id']=='demo-006')['status']=='inapplicable'

def test_import_originals_and_no_implicit_demo(client, tmp_path):
    payload=b'id,title,text,human\nx,Example,content,"{""article"":{""is_match"":true}}"\n'
    response=client.post('/api/datasets/import',json={'filename':'example.csv','content_base64':base64.b64encode(payload).decode()})
    assert response.status_code==201, response.text
    dataset=response.json()
    assert (tmp_path/'datasets'/dataset['id']/'original').read_bytes()==payload
    assert client.post('/api/jobs',json={'dataset_id':dataset['id']}).status_code==400
    assert client.post('/api/jobs',json={'dataset_id':dataset['id'],'mode':'live','model':'test'}).status_code==400

@pytest.mark.parametrize('records', [
 [{'id':'x'},{'id':'x'}], [{'title':'no ID'}], [{'id':'x','text':123}], [{'id':'x','human':[]}],
])
def test_invalid_datasets_rejected(records):
    with pytest.raises(ValueError): normalize(records)

def test_duplicate_csv_columns_rejected():
    with pytest.raises(ValueError,match='Duplicate'):
        parse_upload(b'id,id\na,b\n','test.csv')

def test_evaluation_excludes_failure_and_undefined():
    records=normalize([{'id':'a','human':{'article':{'is_match':False}}},
                       {'id':'b','human':{'article':{'is_match':True}}}])
    result=evaluation(records,[{'record_id':'a','status':'succeeded','assessment':{'is_match':False}},
                               {'record_id':'b','status':'failed','assessment':None}],'article')['metrics'][0]
    assert result['n']==1 and result['tn']==1 and result['excluded']==1
    assert result['precision'] is None and result['recall'] is None

def imported(store, count=3):
    rows=[{'id':str(i),'text':'Synthetic fixture'} for i in range(count)]
    return store.import_data(json.dumps(rows).encode(),'fixture.json')

def paper_result():
    return demo_records()[0]['demo']['article']['assessment']

def test_cancel_resume_and_no_duplicate_success(tmp_path):
    store=Store(tmp_path);dataset=imported(store)
    entered=threading.Event();release=threading.Event();calls=[]
    def provider(text, stage, model):
        calls.append(text)
        if len(calls)==1:
            entered.set();assert release.wait(3)
        return paper_result()
    engine=Jobs(store,provider)
    try:
        job=engine.create(dataset['id'],mode='live',model='mock',allow_network=True)
        assert entered.wait(3)
        engine.cancel(job['id']);release.set()
        assert terminal(store,job['id'])['state']=='cancelled'
        assert len(store.results(job['id']))==1
        engine.resume(job['id'])
        assert terminal(store,job['id'])['state']=='succeeded'
        assert len(calls)==3
        with pytest.raises(ValueError):engine.resume(job['id'])
    finally:
        release.set();engine.close()

def test_restart_recovers_without_running_and_version_change_blocks_resume(tmp_path, monkeypatch):
    store=Store(tmp_path);dataset=imported(store,1)
    first=Jobs(store,lambda *_:paper_result())
    job=first.create(dataset['id'],mode='live',model='mock',allow_network=True)
    terminal(store,job['id']);first.close()
    store.set_state(job['id'],'running')
    calls=[]
    second=Jobs(Store(tmp_path),lambda *_:calls.append('unexpected'))
    try:
        assert second.store.job(job['id'])['state']=='interrupted'
        assert calls==[]
        monkeypatch.setattr('src.tripod.jobs.provenance',lambda *args:{'changed':'schema'})
        with pytest.raises(ValueError,match='changed'):second.resume(job['id'])
    finally:second.close()

def test_modified_dataset_fails_integrity(tmp_path):
    store=Store(tmp_path);dataset=imported(store,1)
    (tmp_path/'datasets'/dataset['id']/'records.json').write_text('[]')
    with pytest.raises(ValueError,match='integrity'):store.records(dataset['id'])

def test_failure_is_redacted_and_retry_is_explicit(tmp_path):
    store=Store(tmp_path);dataset=imported(store,1);calls=[]
    def fail(*args):
        calls.append(1);raise RuntimeError('sk-secret example private text')
    engine=Jobs(store,fail)
    try:
        job=engine.create(dataset['id'],mode='live',model='mock',allow_network=True)
        assert terminal(store,job['id'])['state']=='incomplete'
        assert len(calls)==1
        result=store.results(job['id'])[0]
        assert result['assessment'] is None and 'sk-secret' not in json.dumps(result)
    finally:engine.close()

def test_csv_formula_injection_is_escaped(tmp_path):
    store=Store(tmp_path);dataset=store.import_data(b'[{"id":"=HYPERLINK(1)","text":"example"}]','test.json')
    with TestClient(create_app(tmp_path,TOKEN,lambda *_:paper_result())) as client:
        client.headers.update(HEADERS)
        job=client.post('/api/jobs',json={'dataset_id':dataset['id'],'mode':'live','model':'mock','allow_network':True}).json()
        terminal(client.app.state.store,job['id'])
        assert "'=HYPERLINK(1)" in client.get(f"/api/jobs/{job['id']}/export?format=csv").text
