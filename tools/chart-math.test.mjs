import {test} from 'node:test';
import assert from 'node:assert/strict';
import {chartSeries,axisLabel} from '../frontend/src/workspace/chartMath.ts';

test('chart uses elapsed time, not equally spaced sample positions',()=>{
 const s=chartSeries([{timestamp:'2026-01-01T00:00:00Z',speed:0},{timestamp:'2026-01-01T00:00:01Z',speed:10},{timestamp:'2026-01-01T00:00:10Z',speed:20}],'speed');
 assert.deepEqual(s.points.map(p=>p.x),[0,10,100]);
 assert.equal(s.duration,10);
 assert.equal(s.max,20);
});
test('missing signal values split chart paths instead of inventing zeros',()=>{
 const s=chartSeries([{timestamp:'2026-01-01T00:00:00Z',rpm:1000},{timestamp:'2026-01-01T00:00:01Z',rpm:null},{timestamp:'2026-01-01T00:00:02Z',rpm:2000}],'rpm');
 assert.equal(s.segments.length,2);
 assert.equal(s.points[1].value,null);
 assert.equal(s.available,2);
});
test('entirely missing or constant signal has finite chart coordinates',()=>{
 const rows=[{timestamp:'2026-01-01T00:00:00Z',battery:12},{timestamp:'2026-01-01T00:00:01Z',battery:12}];
 assert.equal(chartSeries(rows,'rpm').available,0);
 assert.ok(chartSeries(rows,'battery').points.every(p=>Number.isFinite(p.y)));
});
test('small voltage range keeps distinct axis labels',()=>{
 assert.equal(axisLabel(13.75,.03),'13.750');
 assert.equal(axisLabel(13.78,.03),'13.780');
});
