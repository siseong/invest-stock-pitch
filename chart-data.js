/* Chart calculations shared by the browser and dependency-free Node tests. */
(function (root) {
  'use strict';
  function portfolioSeries(rows) {
    const valid = rows.filter(r => Number.isFinite(r.returnPct) && r.history?.length);
    if (!valid.length) return [];
    const dates = [...new Set(valid.flatMap(r => r.history.map(p => p.date)))].sort();
    return dates.map(date => {
      const returns = valid.map(r => r.history.filter(p => p.date <= date).at(-1)?.returnPct).filter(Number.isFinite);
      return { date, returnPct: returns.reduce((a, b) => a + b, 0) / returns.length };
    });
  }
  function alignSeries(lines) {
    const dates = [...new Set(lines.flatMap(line => line.points.map(p => p.date)))].sort();
    return { dates, lines: lines.map(line => ({ ...line, points: dates.map(date => {
      const prior = line.points.filter(p => p.date <= date).at(-1);
      return prior ? { date, returnPct: prior.returnPct } : { date, returnPct: null };
    }) })) };
  }
  const api = { portfolioSeries, alignSeries };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PitchChart = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
