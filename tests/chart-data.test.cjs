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
test('selection weights use initial amounts and cumulative returns', () => {
 const rows=[
  {selectionCount:2,returnPct:10,history:[{date:'2026-11-13',returnPct:0},{date:'2026-11-16',returnPct:10}]},
  {selectionCount:1,returnPct:-2,history:[{date:'2026-11-13',returnPct:0},{date:'2026-11-16',returnPct:-2}]}
 ];
 const series=portfolioSeries(rows,'selection');
 assert.equal(series[0].returnPct,0);
 assert.equal(series[1].returnPct,6);
 assert.equal(portfolioSeries(rows)[1].returnPct,4);
});
test('weighted missing-price coverage excludes unconfirmed choices from denominator', () => {
 const rows=[
  {selectionCount:2,returnPct:10,history:[{date:'2026-11-16',returnPct:10}]},
  {selectionCount:1,returnPct:null,history:[]},
  {selectionCount:0,returnPct:50,history:[{date:'2026-11-16',returnPct:50}]}
 ];
 assert.equal(portfolioSeries(rows,'selection')[0].returnPct,10);
 assert.deepEqual(portfolioSeries([{selectionCount:2,returnPct:null,history:[]}],'selection'),[]);
});
test('full class allocation has 41 votes across 38 stocks', () => {
 const config=require('../resources/stocks.json');
 const rows=config.stocks.map(stock=>({...stock,returnPct:stock.symbol==='NVDA'?41:0,history:[{date:'2026-11-16',returnPct:stock.symbol==='NVDA'?41:0}]}));
 assert.equal(portfolioSeries(rows,'selection')[0].returnPct,2);
 assert.equal(rows.reduce((sum,r)=>sum+r.selectionCount,0),41);
});
