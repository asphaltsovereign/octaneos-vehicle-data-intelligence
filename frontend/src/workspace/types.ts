export type Customer = {id:string; name:string; phone:string; notes:string};
export type Vehicle = {id:string; customer_id:string; make:string; model:string; year:number; odometer:number; registration:string; source_identifier:string; is_demo:boolean};
export type Job = {id:string; customer_id:string; vehicle_id:string; complaint:string; observations:string; inspection:Record<string,string>; status:string; created_at:string; updated_at:string};
export type ReportIndex = {id:string; job_id:string; vehicle_id:string; created_at:string; source_classification:string; finding_count:number; attention_count:number; runtime_mode:string; quality_score:string|null; has_notes:boolean};
export type View = 'overview'|'vehicles'|'evidence'|'governance'|'queue'|'people'|'new-job'|'job'|'report'|'passport';
