import csv
import io
import hashlib
import json
import numpy as np
import pandas as pd
from datetime import datetime,timezone
from fastapi import HTTPException
from ..services.ingestion import ingest_csv_bytes, SAN_REQUIRED

VERSION='workshop-beta-0.1.0'
MAX_BYTES=2*1024*1024
MAX_ROWS=20000
BOUNDARY='Screening and inspection evidence only; no confirmed component failure, calibrated failure probability, remaining useful life, ethanol compatibility or Yamaha R15 diagnostic validation.'

def inspection_evidence(job):
    findings=[]
    for key,value in job['inspection'].items():
        if value=='not_checked':continue
        findings.append({'id':'manual-'+key,'title':key.capitalize()+' inspection','detail':('Technician marked attention required; inspect and measure before deciding on repair.' if value=='attention' else 'Technician marked this visual check as passed; this is not instrumented verification.'),'severity':'caution' if value=='attention' else 'info','origin':'manual_inspection'})
    if not findings:
        findings=[{'id':'manual-unchecked','title':'Inspection not completed','detail':'No completed checklist items were recorded. Technician observations alone do not establish vehicle health.','severity':'caution','origin':'manual_inspection'}]
    return {'findings':findings,'limitations':[BOUNDARY,'Manual inspection only. No telemetry model was run.'],'quality':{'status':'inspection_only','telemetry_samples':0},'model':{'runtime_mode':'not_run_manual','version':None},'provenance':{'pipeline':VERSION,'generated_utc':datetime.now(timezone.utc).isoformat(),'raw_file_retained':False},'inspection_snapshot':{'inspection':job['inspection'],'observations':job['observations'],'complaint':job['complaint']}}

def telemetry_evidence(raw,source_classification,vehicle,job):
    if not raw or len(raw)>MAX_BYTES:raise HTTPException(422,'Upload a non-empty CSV no larger than 2 MiB.')
    try:
        text=raw.decode('utf-8-sig')
        reader=csv.reader(io.StringIO(text),strict=True)
        headers=next(reader)
        if len(headers)>64 or len(headers)!=len(set(headers)):raise ValueError('Invalid headers')
        rows=0
        for row in reader:
            rows+=1
            if rows>MAX_ROWS or len(row)!=len(headers) or any(len(cell)>2048 for cell in row):raise ValueError('CSV limits')
        if 'schema_version' in headers:
            if not set(SAN_REQUIRED).issubset(headers):raise ValueError('Incomplete SAN headers')
            check=pd.read_csv(io.BytesIO(raw),dtype=str)
            if set(check['schema_version'].dropna())!={'1.0'}:raise ValueError('Unsupported SAN schema version')
            seq=pd.to_numeric(check['sample_seq'],errors='coerce')
            if seq.isna().any() or (seq%1!=0).any() or (seq.diff().dropna()<=0).any():raise ValueError('Invalid sample sequence')
        session=ingest_csv_bytes(raw)
        frame=session.frame
        if len(frame)<12 or (frame.timestamp.diff().dt.total_seconds().dropna()<=0).any():raise ValueError('Insufficient or duplicate samples')
        signals=['speed','rpm','maf','engine_load','temp','fuel_rate','battery','soc']
        if any(np.isinf(frame[x].to_numpy(dtype=float)).any() for x in signals):raise ValueError('Nonfinite measurements')
        required=['speed','battery'] if session.source_type=='san' else ['speed']
        if any(frame[x].notna().mean()<0.8 for x in required):raise ValueError('Insufficient signal coverage')
        if not frame.gps_fix.dropna().isin([0,1]).all():raise ValueError('Invalid GPS fix')
        if frame.temp.dropna().between(-60,100).all()==False or frame.battery.dropna().between(0,1000).all()==False:raise ValueError('Signal units or range invalid')
    except (ValueError,UnicodeError,StopIteration,csv.Error,OverflowError):
        raise HTTPException(422,'Unsupported or invalid CSV. Use a single-session SAN-V1 or VED export with correct units; maximum 20,000 rows and 64 columns.') from None
    if not session.analysis_ready:raise HTTPException(422,{'message':'Data-quality gate rejected this session.','quality_score':session.quality_score,'notes':session.quality_notes})
    if source_classification=='vehicle_telemetry':
        if session.source_type!='san' or vehicle['is_demo']:
            raise HTTPException(422,'Real vehicle telemetry requires SAN-V1 data attached to a real vehicle.')
        if not vehicle['source_identifier'] or session.vehicle_id!=vehicle['source_identifier']:
            raise HTTPException(422,'CSV vehicle identifier does not match the registered source identifier.')
    elif source_classification in ('public_dataset','synthetic'):
        if not vehicle['is_demo']:raise HTTPException(422,'Public or synthetic data must be linked to a demonstration vehicle.')
        if source_classification=='public_dataset' and session.source_type!='ved':raise HTTPException(422,'Public dataset classification requires a supported VED export.')
    else:raise HTTPException(422,'Select an explicit telemetry source classification.')
    from ..main import analyze_frame
    analysis=analyze_frame(session.frame,session.source_type,session.session_id,session.quality_score,session.analysis_ready,session.quality_notes,session.file_hash)
    if analysis['model']['status']!='ok':
        raise HTTPException(422,'The available data cannot support the analyzer. Save a manual inspection report instead.')
    # Source overrides inferred parser labels; synthetic SAN is never live-hardware evidence.
    analysis['source_label']={'synthetic':'Synthetic demonstration telemetry','public_dataset':'Public passenger-car dataset','vehicle_telemetry':'Vehicle SAN-V1 telemetry'}[source_classification]
    base=inspection_evidence(job)
    base['limitations']=[BOUNDARY]+analysis.get('limitations',[])
    if source_classification!='vehicle_telemetry':base['limitations'].append('Public/synthetic data does not establish health of a customer motorcycle.')
    base['findings'].append({'id':'telemetry-screening','title':'Telemetry screening completed','detail':f"Screened {analysis['sample_count']} samples; data-quality score {analysis['quality_score']}/100. This is not a component diagnosis.",'severity':'info','origin':'telemetry_quality'})
    for i,rule in enumerate(analysis.get('rules',[])):
        if not isinstance(rule,dict):continue
        base['findings'].append({'id':f'rule-{i}','title':str(rule.get('title') or rule.get('name') or rule.get('code') or 'Telemetry rule'),'detail':str(rule.get('evidence') or rule.get('message') or rule.get('detail') or ('Rule triggered from '+', '.join(rule.get('signals',[]))+'. Review recorded signal values; this is not a confirmed component fault.')),'severity':'caution','origin':'deterministic_rule'})
    count=len(analysis.get('anomaly_regions',[]))
    base['findings'].append({'id':'ml-regions','title':'Statistical anomaly screening','detail':f'{count} statistically unusual regions identified. An anomaly score is not a calibrated probability of failure.','severity':'caution' if count else 'info','origin':'ml_screening'})
    base.update(quality={'status':'accepted','score':session.quality_score,'samples':len(session.frame),'notes':session.quality_notes},model=analysis['model'],analysis=analysis)
    base['provenance'].update(sha256=hashlib.sha256(raw).hexdigest(),source_contract=session.source_type,source_classification=source_classification,rule_version='sentinel-v3.4-preserved',analysis_version=analysis['provenance']['pipeline'])
    # Persist a finite JSON representation only.
    json.dumps(base,allow_nan=False)
    return base
