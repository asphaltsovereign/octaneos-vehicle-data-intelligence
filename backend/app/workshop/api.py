import hashlib
import os
from uuid import UUID
from typing import Annotated,Literal
from fastapi import APIRouter,Depends,Header,HTTPException,Request,Response,UploadFile,File,Form
from psycopg.types.json import Jsonb
from starlette.concurrency import run_in_threadpool
from .auth import authenticated_user,demo_login,supabase_request,logout,rate_limit
from .db import connection,require_member,demo_mode,check_config
from .schemas import WorkshopInput,LoginInput,CustomerInput,VehicleInput,VehicleEdit,JobInput,JobEdit,ReviewInput
from .evidence import VERSION,MAX_BYTES,inspection_evidence,telemetry_evidence

router=APIRouter(prefix='/api')
User=Annotated[UUID,Depends(authenticated_user)]
Workshop=Annotated[UUID,Header(alias='X-Workshop-Id')]

def one(conn,table,workshop,id):
    # Table identifiers are internal constants only.
    row=conn.execute(f'SELECT * FROM sentinel.{table} WHERE workshop_id=%s AND id=%s',(workshop,id)).fetchone()
    if not row:raise HTTPException(404,'Record not found in this workshop.')
    return row

def report_row(conn,workshop,id):
    row=one(conn,'reports',workshop,id)
    review=conn.execute('SELECT notes FROM sentinel.report_reviews WHERE workshop_id=%s AND report_id=%s',(workshop,id)).fetchone()
    row['technician_notes']=review['notes'] if review else ''
    return row

@router.get('/config')
def config():return {'demo':demo_mode(),'version':VERSION,'auth_provider':'demo' if demo_mode() else 'supabase'}

@router.get('/ready')
def ready():
    with connection() as c:
        if not c.execute("SELECT 1 FROM sentinel.schema_migrations WHERE version='001_workshop'").fetchone():raise HTTPException(503,'Database migrations are required.')
    return {'status':'ready','database':'PostgreSQL (PGlite/WASM)' if demo_mode() and os.getenv('OCTANE_DATABASE_ENGINE')=='pglite' else 'PostgreSQL','mode':'DEMO' if demo_mode() else 'production'}

@router.post('/auth/demo')
def enter_demo(request:Request):
    rate_limit(('demo',request.client.host if request.client else 'local'),20)
    return demo_login()

@router.post('/auth/login')
async def login(body:LoginInput,request:Request):
    rate_limit(('login',request.client.host if request.client else 'local'),10)
    if demo_mode():raise HTTPException(400,'Use the clearly labeled demo entry.')
    data=await supabase_request('POST','token?grant_type=password',payload=body.model_dump())
    if not isinstance(data.get('access_token'),str):raise HTTPException(503,'Sign-in response was invalid.')
    return {'access_token':data['access_token'],'expires_in':data.get('expires_in',3600)}

@router.post('/auth/logout',status_code=204)
async def end_session(user:User,authorization:str=Header()):
    await logout(authorization)
    return Response(status_code=204)

@router.get('/workshops')
def workshops(user:User):
    with connection(user) as c:return c.execute('SELECT * FROM sentinel.workshops ORDER BY created_at').fetchall()

@router.post('/workshops')
def create_workshop(body:WorkshopInput,user:User):
    rate_limit(('onboard',str(user)),5)
    with connection(user) as c:return c.execute('SELECT * FROM sentinel.create_workshop(%s)',(body.name,)).fetchone()

@router.get('/customers')
def customers(user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop)
        return c.execute('SELECT * FROM sentinel.customers WHERE workshop_id=%s ORDER BY name LIMIT 1000',(workshop,)).fetchall()

@router.post('/customers')
def create_customer(body:CustomerInput,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop)
        return c.execute('INSERT INTO sentinel.customers(workshop_id,name,phone,notes) VALUES(%s,%s,%s,%s) RETURNING *',(workshop,body.name,body.phone,body.notes)).fetchone()

@router.patch('/customers/{id}')
def edit_customer(id:UUID,body:CustomerInput,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop);one(c,'customers',workshop,id)
        return c.execute('UPDATE sentinel.customers SET name=%s,phone=%s,notes=%s WHERE workshop_id=%s AND id=%s RETURNING *',(body.name,body.phone,body.notes,workshop,id)).fetchone()

@router.get('/vehicles')
def vehicles(user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop)
        return c.execute('SELECT * FROM sentinel.vehicles WHERE workshop_id=%s ORDER BY created_at DESC LIMIT 1000',(workshop,)).fetchall()

@router.post('/vehicles')
def create_vehicle(body:VehicleInput,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop);one(c,'customers',workshop,body.customer_id)
        return c.execute('INSERT INTO sentinel.vehicles(workshop_id,customer_id,make,model,year,odometer,registration,source_identifier,is_demo) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *',(workshop,body.customer_id,body.make,body.model,body.year,body.odometer,body.registration,body.source_identifier,body.is_demo or demo_mode())).fetchone()

@router.patch('/vehicles/{id}')
def edit_vehicle(id:UUID,body:VehicleEdit,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop)
        c.execute('SELECT id FROM sentinel.vehicles WHERE workshop_id=%s AND id=%s FOR UPDATE',(workshop,id))
        old=one(c,'vehicles',workshop,id)
        # Source labels cannot be changed once evidence exists.
        if (old['is_demo']!=body.is_demo or old['source_identifier']!=body.source_identifier) and c.execute('SELECT 1 FROM sentinel.reports WHERE workshop_id=%s AND vehicle_id=%s',(workshop,id)).fetchone():
            raise HTTPException(409,'Source identity is locked after evidence has been recorded.')
        return c.execute('UPDATE sentinel.vehicles SET make=%s,model=%s,year=%s,odometer=%s,registration=%s,source_identifier=%s,is_demo=%s WHERE workshop_id=%s AND id=%s RETURNING *',(body.make,body.model,body.year,body.odometer,body.registration,body.source_identifier,body.is_demo or demo_mode(),workshop,id)).fetchone()

@router.get('/jobs')
def jobs(user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop)
        return c.execute('SELECT * FROM sentinel.jobs WHERE workshop_id=%s ORDER BY created_at DESC LIMIT 1000',(workshop,)).fetchall()

@router.post('/jobs')
def create_job(body:JobInput,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop)
        vehicle=one(c,'vehicles',workshop,body.vehicle_id)
        if vehicle['customer_id']!=body.customer_id:raise HTTPException(409,'Vehicle does not belong to the selected customer.')
        old=c.execute('SELECT * FROM sentinel.jobs WHERE workshop_id=%s AND idempotency_key=%s',(workshop,body.idempotency_key)).fetchone()
        if old:
            if any(old[k]!=getattr(body,k) for k in ('customer_id','vehicle_id','complaint')):raise HTTPException(409,'Submission key was already used for different job details.')
            return old
        return c.execute('INSERT INTO sentinel.jobs(workshop_id,customer_id,vehicle_id,complaint,idempotency_key) VALUES(%s,%s,%s,%s,%s) RETURNING *',(workshop,body.customer_id,body.vehicle_id,body.complaint,body.idempotency_key)).fetchone()

@router.get('/jobs/{id}')
def get_job(id:UUID,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop);return one(c,'jobs',workshop,id)

@router.patch('/jobs/{id}')
def edit_job(id:UUID,body:JobEdit,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop)
        c.execute('SELECT id FROM sentinel.jobs WHERE workshop_id=%s AND id=%s FOR UPDATE',(workshop,id))
        old=one(c,'jobs',workshop,id)
        transitions={'draft':{'draft','in_progress'},'in_progress':{'in_progress','reviewed'},'reviewed':{'reviewed','closed'},'closed':set()}
        if body.status not in transitions[old['status']]:raise HTTPException(409,'This job cannot make that status transition. Closed jobs are read-only.')
        if body.status in ('reviewed','closed') and not c.execute('SELECT 1 FROM sentinel.reports WHERE workshop_id=%s AND job_id=%s',(workshop,id)).fetchone():raise HTTPException(409,'Save an analysis report before marking this job reviewed.')
        return c.execute('UPDATE sentinel.jobs SET complaint=%s,observations=%s,inspection=%s,status=%s,updated_at=now() WHERE workshop_id=%s AND id=%s RETURNING *',(body.complaint,body.observations,Jsonb(body.inspection),body.status,workshop,id)).fetchone()

@router.get('/jobs/{id}/reports')
def reports(id:UUID,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop);one(c,'jobs',workshop,id)
        ids=c.execute('SELECT id FROM sentinel.reports WHERE workshop_id=%s AND job_id=%s ORDER BY created_at DESC',(workshop,id)).fetchall()
        return [report_row(c,workshop,r['id']) for r in ids]

def save_analysis(id,user,workshop,key,classification,raw):
    # Lock job across snapshot, computation and save: prevents a report attaching to a changed inspection.
    with connection(user) as c:
        require_member(c,workshop)
        c.execute('SELECT id FROM sentinel.jobs WHERE workshop_id=%s AND id=%s FOR UPDATE',(workshop,id))
        job=one(c,'jobs',workshop,id)
        old=c.execute('SELECT id,source_classification,evidence FROM sentinel.reports WHERE workshop_id=%s AND job_id=%s AND idempotency_key=%s',(workshop,id,key)).fetchone()
        if old:
            if old['source_classification']!=classification or old['evidence']['provenance'].get('sha256')!=(hashlib.sha256(raw).hexdigest() if raw is not None else None):raise HTTPException(409,'Submission key was already used for different evidence.')
            return report_row(c,workshop,old['id'])
        if job['status']=='closed':raise HTTPException(409,'Closed jobs are read-only.')
        c.execute('SELECT id FROM sentinel.vehicles WHERE workshop_id=%s AND id=%s FOR UPDATE',(workshop,job['vehicle_id']))
        vehicle=one(c,'vehicles',workshop,job['vehicle_id'])
        if classification=='manual':
            if raw is not None:raise HTTPException(422,'Manual inspections cannot be submitted as telemetry.')
            evidence=inspection_evidence(job)
        else:
            if raw is None:raise HTTPException(422,'Choose a supported CSV file for telemetry analysis.')
            evidence=telemetry_evidence(raw,classification,vehicle,job)
        evidence['vehicle_snapshot']={k:str(vehicle[k]) if isinstance(vehicle[k],UUID) else vehicle[k] for k in ('id','make','model','year','odometer','is_demo','source_identifier')}
        report=c.execute('INSERT INTO sentinel.reports(workshop_id,job_id,vehicle_id,source_classification,evidence,idempotency_key) VALUES(%s,%s,%s,%s,%s,%s) RETURNING *',(workshop,id,job['vehicle_id'],classification,Jsonb(evidence),key)).fetchone()
        c.execute('INSERT INTO sentinel.passport_events(workshop_id,report_id,job_id,vehicle_id,source_classification) VALUES(%s,%s,%s,%s,%s)',(workshop,report['id'],id,job['vehicle_id'],classification))
        report['technician_notes']=''
        return report

@router.post('/jobs/{id}/analyze')
async def analyze_job(id:UUID,user:User,workshop:Workshop,idempotency_key:Annotated[UUID,Form()],source_classification:Annotated[Literal['manual','public_dataset','synthetic','vehicle_telemetry'],Form()],file:UploadFile|None=File(default=None)):
    rate_limit(('analysis',str(user)),10)
    # Authorize before reading or parsing any uploaded content.
    with connection(user) as c:
        require_member(c,workshop);one(c,'jobs',workshop,id)
    raw=None
    if file:
        if not file.filename or not file.filename.lower().endswith('.csv'):raise HTTPException(415,'Upload a CSV file.')
        raw=await file.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise HTTPException(413,'CSV exceeds the 2 MiB limit.')
    return await run_in_threadpool(save_analysis,id,user,workshop,idempotency_key,source_classification,raw)

@router.get('/reports')
def report_register(user:User,workshop:Workshop):
    """Compact tenant-scoped register; telemetry remains on individual reports."""
    with connection(user) as c:
        require_member(c,workshop)
        return c.execute('''
            SELECT r.id,r.job_id,r.vehicle_id,r.created_at,r.source_classification,
                   jsonb_array_length(r.evidence->'findings') AS finding_count,
                   (SELECT count(*) FROM jsonb_array_elements(r.evidence->'findings') f
                    WHERE f->>'severity' IN ('attention','warning','high','caution')) AS attention_count,
                   r.evidence->'model'->>'runtime_mode' AS runtime_mode,
                   r.evidence->'quality'->>'score' AS quality_score,
                   COALESCE(length(v.notes)>0,false) AS has_notes
            FROM sentinel.reports r
            LEFT JOIN sentinel.report_reviews v ON v.report_id=r.id AND v.workshop_id=r.workshop_id
            WHERE r.workshop_id=%s ORDER BY r.created_at DESC,r.id LIMIT 1000
        ''',(workshop,)).fetchall()

@router.get('/reports/{id}')
def get_report(id:UUID,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop);return report_row(c,workshop,id)

@router.patch('/reports/{id}/review')
def review_report(id:UUID,body:ReviewInput,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop);one(c,'reports',workshop,id)
        c.execute('INSERT INTO sentinel.report_reviews(report_id,workshop_id,notes,reviewed_by) VALUES(%s,%s,%s,%s) ON CONFLICT(report_id) DO UPDATE SET notes=excluded.notes,reviewed_by=excluded.reviewed_by,updated_at=now()',(id,workshop,body.notes,user))
        return report_row(c,workshop,id)

@router.get('/vehicles/{id}/history')
def history(id:UUID,user:User,workshop:Workshop):
    with connection(user) as c:
        require_member(c,workshop);one(c,'vehicles',workshop,id)
        return c.execute('SELECT * FROM sentinel.passport_events WHERE workshop_id=%s AND vehicle_id=%s ORDER BY created_at DESC',(workshop,id)).fetchall()

@router.post('/reports/{id}/explain')
async def explain_report(id:UUID,user:User,workshop:Workshop):
    rate_limit(('explain',str(user)),6)
    with connection(user) as c:
        require_member(c,workshop);report=report_row(c,workshop,id)
    from .explanation import explain
    return await explain(report['evidence'])
