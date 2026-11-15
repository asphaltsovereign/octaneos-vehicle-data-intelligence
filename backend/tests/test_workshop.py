"""Real PostgreSQL integration tests; TEST_DATABASE_URL must point at disposable migrated DB."""
import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('OCTANE_ENV','development')
    monkeypatch.setenv('OCTANE_DEMO','1')
    monkeypatch.setenv('DATABASE_URL',os.getenv('TEST_DATABASE_URL','postgresql://postgres@127.0.0.1:55432/postgres?sslmode=disable'))
    with TestClient(app) as c:
        yield c

def test_workshop_requires_auth(client):
    assert client.get('/api/workshops').status_code == 401

def enter(client):
    r=client.post('/api/auth/demo',json={})
    assert r.status_code==200,r.text
    h={'Authorization':'Bearer '+r.json()['access_token']}
    r=client.post('/api/workshops',headers=h,json={'name':'DEMO test workshop '+str(uuid4())[:8]})
    assert r.status_code==200,r.text
    h['X-Workshop-Id']=r.json()['id']
    return h

def job_setup(client,h):
    c=client.post('/api/customers',headers=h,json={'name':'Synthetic rider'})
    assert c.status_code==200,c.text
    v=client.post('/api/vehicles',headers=h,json={'customer_id':c.json()['id'],'make':'Yamaha','model':'R15 demo','year':2015,'odometer':12000,'is_demo':True})
    assert v.status_code==200,v.text
    payload={'customer_id':c.json()['id'],'vehicle_id':v.json()['id'],'complaint':'Synthetic brake inspection','idempotency_key':str(uuid4())}
    j=client.post('/api/jobs',headers=h,json=payload)
    assert j.status_code==200,j.text
    assert client.post('/api/jobs',headers=h,json=payload).json()['id']==j.json()['id']
    return j.json(),v.json()

def test_persistent_inspection_report_passport_and_immutable_evidence(client):
    h=enter(client);j,v=job_setup(client,h)
    r=client.patch('/api/jobs/'+j['id'],headers=h,json={'complaint':j['complaint'],'observations':'Check brake pad thickness','inspection':{'brakes':'attention','tyres':'pass'},'status':'in_progress'})
    assert r.status_code==200,r.text
    data={'source_classification':'manual','idempotency_key':str(uuid4())}
    r=client.post('/api/jobs/'+j['id']+'/analyze',headers=h,data=data)
    assert r.status_code==200,r.text
    report=r.json(); assert report['evidence']['model']['runtime_mode']=='not_run_manual'
    assert client.post('/api/jobs/'+j['id']+'/analyze',headers=h,data=data).json()['id']==report['id']
    assert client.get('/api/reports/'+report['id'],headers=h).json()['evidence']==report['evidence']
    review=client.patch('/api/reports/'+report['id']+'/review',headers=h,json={'notes':'Measure before repair'})
    assert review.status_code==200,review.text
    assert review.json()['evidence']==report['evidence']
    history=client.get('/api/vehicles/'+v['id']+'/history',headers=h).json()
    assert history[0]['report_id']==report['id']
    assert client.post('/api/reports/'+report['id']+'/explain',headers=h,json={}).json()['status']=='deterministic_local'

def test_upload_errors_and_tenant_reference_checks(client):
    h=enter(client);j,v=job_setup(client,h)
    for raw in [b'',b'bad\n1\n2',b'<script>alert(1)</script>']:
        r=client.post('/api/jobs/'+j['id']+'/analyze',headers=h,data={'source_classification':'synthetic','idempotency_key':str(uuid4())},files={'file':('bad.csv',raw,'text/csv')})
        assert r.status_code==422,r.text
    wrong={**h,'X-Workshop-Id':str(uuid4())}
    assert client.get('/api/jobs',headers=wrong).status_code==403
    assert client.get('/api/reports/'+str(uuid4()),headers=h).status_code==404
    assert client.post('/api/jobs',headers=h,json={'customer_id':str(uuid4()),'vehicle_id':v['id'],'complaint':'invalid linkage','idempotency_key':str(uuid4())}).status_code in (404,409)

def test_production_demo_fails_closed(client,monkeypatch):
    monkeypatch.setenv('OCTANE_ENV','production')
    monkeypatch.setenv('OCTANE_DEMO','1')
    assert client.post('/api/auth/demo',json={}).status_code in (404,503)
    assert client.get('/api/ready').status_code==503

def test_supported_synthetic_csv_saved_with_hash_and_actual_model(client):
    from pathlib import Path
    import hashlib
    h=enter(client);j,v=job_setup(client,h)
    raw=(Path(__file__).resolve().parents[2]/'samples/normal.csv').read_bytes()
    r=client.post('/api/jobs/'+j['id']+'/analyze',headers=h,data={'source_classification':'synthetic','idempotency_key':str(uuid4())},files={'file':('normal.csv',raw,'text/csv')})
    assert r.status_code==200,r.text
    evidence=r.json()['evidence']
    assert evidence['provenance']['sha256']==hashlib.sha256(raw).hexdigest()
    assert evidence['model']['status']=='ok'
    assert evidence['analysis']['source_label']=='Synthetic demonstration telemetry'
    assert evidence['model']['runtime_mode']=='legacy_fallback_no_frozen_model'
    assert client.get('/api/reports/'+r.json()['id'],headers=h).json()['evidence']==evidence
