export type Sample = {timestamp:string;[signal:string]:unknown};
export function axisLabel(value:number,span:number){return value.toFixed(Math.min(6,Math.max(1,Math.ceil(-Math.log10(Math.max(span/4,1e-6))))))}
export function chartSeries(rows:Sample[], signal:string){
 const values=rows.map(r=>typeof r[signal]==='number'&&Number.isFinite(r[signal])?r[signal] as number:null);
 const available=values.filter((x):x is number=>x!==null);
 const min=available.length?Math.min(...available):0,max=available.length?Math.max(...available):0;
 const start=Date.parse(rows[0]?.timestamp||''),end=Date.parse(rows.at(-1)?.timestamp||'');
 const duration=Number.isFinite(end-start)?Math.max(0,(end-start)/1000):0;
 const floor=min===max?min-1:min,ceiling=min===max?max+1:max;
 const points=rows.map((r,i)=>({x:duration?((Date.parse(r.timestamp)-start)/1000/duration)*100:0,y:values[i]===null?null:100-((values[i]!-floor)/(ceiling-floor))*100,value:values[i],timestamp:r.timestamp}));
 const segments:typeof points[]=[];let current:typeof points=[];
 for(const p of points){if(p.value===null){if(current.length)segments.push(current);current=[]}else current.push(p)}
 if(current.length)segments.push(current);
 return {points,segments,min,max,floor,ceiling,duration,available:available.length};
}
