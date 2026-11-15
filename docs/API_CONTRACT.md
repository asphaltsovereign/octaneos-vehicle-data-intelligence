# Workshop API contract
All paths same origin. JSON bodies/responses unless upload. Auth header Bearer access_token; workshop routes also X-Workshop-Id UUID. Errors {detail:string|object}. IDs UUID strings. Dates ISO. All list endpoints return arrays.
GET /api/config -> {demo:boolean,version:string,auth_provider:string}
POST /api/auth/demo {} -> {access_token,expires_in:28800}; only explicit development demo.
POST /api/auth/login {email,password} -> {access_token,expires_in}; Supabase proxy.
POST /api/auth/logout -> 204.
GET /api/workshops -> [{id,name}]
POST /api/workshops {name} -> {id,name}; creates owner membership.
GET /api/customers -> [{id,name,phone,notes}]
POST /api/customers {name,phone?:string,notes?:string} -> customer
PATCH /api/customers/{id} {name,phone,notes} -> customer
GET /api/vehicles -> [{id,customer_id,make,model,year,odometer,registration,source_identifier,is_demo}]
POST /api/vehicles {customer_id,make,model,year,odometer,registration?:string,source_identifier?:string,is_demo:boolean} -> vehicle
PATCH /api/vehicles/{id} same fields except customer_id -> vehicle
GET /api/jobs -> [{id,customer_id,vehicle_id,complaint,observations,inspection,status,created_at,updated_at}]
POST /api/jobs {customer_id,vehicle_id,complaint,idempotency_key:UUID} -> job
GET /api/jobs/{id} -> job
PATCH /api/jobs/{id} {complaint,observations,inspection,status} -> job; status draft|in_progress|reviewed|closed. Allowed forward transitions draft->in_progress->reviewed->closed; same status allowed. Reviewed requires saved report. Closed read-only.
inspection object maps brakes|tyres|lights|leaks|battery to not_checked|pass|attention.
POST /api/jobs/{id}/analyze multipart: file optional CSV, source_classification manual|public_dataset|synthetic|vehicle_telemetry, idempotency_key UUID -> report, persisted immediately. With no file use manual. Public/synthetic only on is_demo vehicle. SAN real telemetry requires vehicle.source_identifier match CSV vehicle_id. Demo mode forces all vehicles is_demo.
GET /api/jobs/{id}/reports -> report[]
GET /api/reports/{id} -> report
report: {id,job_id,vehicle_id,created_at,source_classification,evidence:{findings:[{id,title,detail,severity,origin}],limitations:string[],quality:object,model:object,provenance:object,analysis?:object},technician_notes:string}
PATCH /api/reports/{id}/review {notes} -> report; separate notes only, original evidence immutable.
POST /api/reports/{id}/explain {} -> {status:deterministic_local|ai_selected,summary:string,items:[{evidence_id,text}],reason?:string}; optional, report available first.
GET /api/vehicles/{id}/history -> [{id,report_id,job_id,created_at,source_classification}]
GET /api/ready -> {status,database,mode}; 503 on bad config.
No export URL needed: print current report with window.print(); React escapes text. No public share URL; print/save PDF locally.
