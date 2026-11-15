import {useState} from 'react';
import {chartSeries,axisLabel} from './chartMath';
import type {Sample} from './chartMath';
import {Glyph,Source} from './Workspace';
const signals=[{id:'speed',name:'Speed',unit:'km/h'},{id:'rpm',name:'Engine speed',unit:'rpm'},{id:'battery',name:'Battery voltage',unit:'V'},{id:'engine_load',name:'Engine load',unit:'%'},{id:'anomaly_score',name:'Anomaly score',unit:'0–1'}];
export function Telemetry({analysis,source}:{analysis?:Record<string,unknown>;source:string}){
 const [signal,setSignal]=useState('speed'),[cursor,setCursor]=useState(0);
 const rows=(Array.isArray(analysis?.telemetry)?analysis.telemetry:[]) as Sample[];
 if(!rows.length)return <div className="telemetryEmpty"><Glyph name="pulse"/><span>Manual inspection · No telemetry model was run for this report.</span></div>;
 const series=chartSeries(rows,signal),selected=signals.find(s=>s.id===signal)!,sample=series.points[Math.min(cursor,rows.length-1)];
 const toX=(x:number)=>55+x*8.7,toY=(y:number)=>15+y*1.65;
 const regions=Array.isArray(analysis?.anomaly_regions)?analysis.anomaly_regions.length:0;
 return <section className="telemetryPanel panel"><div className="sectionTitle"><div><p className="eyebrow">SAVED TELEMETRY / INVESTIGATION</p><h2>Signal workspace</h2></div><Source value={source}/></div><div className="signalTabs">{signals.map(s=><button key={s.id} className={signal===s.id?'selected':''} onClick={()=>{setSignal(s.id);setCursor(0)}}>{s.name}<small>{s.unit}</small></button>)}</div><div className="signalReadout"><div><span>{selected.name}</span><strong>{sample.value===null?'Not measured':sample.value.toFixed(2)} <small>{sample.value===null?'':selected.unit}</small></strong></div><div><span>Selected timestamp</span><b>{sample.timestamp}</b></div><div><span>Screened samples</span><b>{String(analysis?.sample_count??'—')}</b></div><div><span>Unusual regions</span><b>{regions}</b></div></div>{series.available?<><svg className="telemetryChart" viewBox="0 0 950 215" role="img" aria-label={`${selected.name} over elapsed time in seconds`}>
  {[0,25,50,75,100].map(y=><g key={y}><line x1="55" y1={toY(y)} x2="925" y2={toY(y)} stroke="currentColor" opacity=".12"/><text x="46" y={toY(y)+4} textAnchor="end">{axisLabel(series.ceiling-(series.ceiling-series.floor)*y/100,series.ceiling-series.floor)}</text></g>)}
  {[0,25,50,75,100].map(x=><g key={x}><line x1={toX(x)} y1="15" x2={toX(x)} y2="180" stroke="currentColor" opacity=".07"/><text x={toX(x)} y="203" textAnchor="middle">{(series.duration*x/100).toFixed(1)}s</text></g>)}
  {series.segments.map((part,i)=>part.length===1?<circle key={i} cx={toX(part[0].x)} cy={toY(part[0].y!)} r="3" fill="#69c8ee"/>:<polyline key={i} fill="none" stroke="#69c8ee" strokeWidth="2" vectorEffect="non-scaling-stroke" points={part.map(p=>`${toX(p.x)},${toY(p.y!)}`).join(' ')}/>)}
  <line x1={toX(sample.x)} y1="15" x2={toX(sample.x)} y2="180" stroke="#f0b566" strokeDasharray="4 4"/>
  {sample.y!==null&&<circle cx={toX(sample.x)} cy={toY(sample.y)} r="4" fill="#f0b566"/>}
 </svg><label className="chartScrubber">Inspect saved sample <input aria-label="Inspect saved sample" type="range" min="0" max={rows.length-1} value={Math.min(cursor,rows.length-1)} onChange={e=>setCursor(Number(e.target.value))}/><span>{Math.min(cursor,rows.length-1)+1} / {rows.length}</span></label></>:<div className="blankState"><h3>Signal not measured</h3><p>This source contains no usable {selected.name.toLowerCase()} values. Missing data is never plotted as zero.</p></div>}<p className="fine">{selected.unit} · Elapsed time in seconds · {rows.length} retained preview points; gaps represent missing measurements. Anomaly scores are not failure probabilities.</p></section>;
}
