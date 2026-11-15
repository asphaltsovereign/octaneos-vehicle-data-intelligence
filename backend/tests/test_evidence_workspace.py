"""Report register must expose only the selected tenant's compact evidence index."""
from uuid import uuid4
import pytest
from test_workshop import client, enter, job_setup


@pytest.fixture(autouse=True)
def isolated_demo_identity(monkeypatch):
    # Each test owns its records and rate-limit bucket; production limits stay intact.
    monkeypatch.setattr('app.workshop.auth.DEMO_USER', uuid4())


def test_report_register_is_compact_and_tenant_scoped(client):
    headers = enter(client)
    job, vehicle = job_setup(client, headers)
    response = client.post('/api/jobs/' + job['id'] + '/analyze', headers=headers,
        data={'source_classification': 'manual', 'idempotency_key': str(uuid4())})
    assert response.status_code == 200, response.text
    report = response.json()
    response = client.get('/api/reports', headers=headers)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]['id'] == report['id']
    assert rows[0]['vehicle_id'] == vehicle['id']
    assert rows[0]['finding_count'] == 1
    assert rows[0]['attention_count'] == 1
    assert rows[0]['runtime_mode'] == 'not_run_manual'
    assert rows[0]['source_classification'] == 'manual'
    assert 'evidence' not in rows[0]  # Register must not transfer raw telemetry.
    other = enter(client)
    assert client.get('/api/reports', headers=other).json() == []
    assert client.get('/api/reports', headers={**headers, 'X-Workshop-Id': str(uuid4())}).status_code == 403
    assert client.get('/api/reports').status_code == 401


def test_report_register_includes_saved_review_presence(client):
    headers = enter(client)
    job, _ = job_setup(client, headers)
    report = client.post('/api/jobs/' + job['id'] + '/analyze', headers=headers,
        data={'source_classification': 'manual', 'idempotency_key': str(uuid4())}).json()
    client.patch('/api/reports/' + report['id'] + '/review', headers=headers, json={'notes':'Measure pad thickness'})
    response = client.get('/api/reports', headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()[0]['has_notes'] is True
