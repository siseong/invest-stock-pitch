const test = require('node:test');
const assert = require('node:assert/strict');
const {portfolioSeries,alignSeries} = require('../chart-data.js');
test('equal weights are by unique stock, not selection count', () => {
 const result = portfolioSeries([
  {selectionCount:2,returnPct:10,history:[{date:'2026-11-13',returnPct:0},{date:'2026-11-16',returnPct:10}]},
  {selectionCount:1,returnPct:-2,history:[{date:'2026-11-13',returnPct:0},{date:'2026-11-16',returnPct:-2}]}
 ]);
 assert.equal(result[1].returnPct,4);
});
test('holidays carry the prior value across a common date axis', () => {
 const result=alignSeries([
  {id:'portfolio',points:[{date:'2026-11-13',returnPct:0},{date:'2026-11-16',returnPct:4}]},
  {id:'index',points:[{date:'2026-11-13',returnPct:0},{date:'2026-11-17',returnPct:2}]}
 ]);
 assert.deepEqual(result.dates,['2026-11-13','2026-11-16','2026-11-17']);
 assert.deepEqual(result.lines[1].points.map(p=>p.returnPct),[0,0,2]);
 assert.deepEqual(result.lines[0].points.map(p=>p.returnPct),[0,4,4]);
});
test('an unconfirmed baseline never creates an invented zero line', () => {
 const result=alignSeries([{id:'pending',points:[]},{id:'ready',points:[{date:'2026-11-16',returnPct:2}]}]);
 assert.equal(result.lines[0].points[0].returnPct,null);
 assert.deepEqual(portfolioSeries([{returnPct:null,history:[]}]),[]);
});
