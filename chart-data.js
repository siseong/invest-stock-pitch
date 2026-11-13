/* Chart calculations shared by the browser and dependency-free Node tests. */
(function (root) {
  'use strict';
  function portfolioSeries(rows, weighting = 'equal') {
    const weight = row => weighting === 'selection' ? row.selectionCount : 1;
    const valid = rows.filter(r => Number.isFinite(r.returnPct) && r.history?.length && Number.isFinite(weight(r)) && weight(r) > 0);
    if (!valid.length) return [];
    const dates = [...new Set(valid.flatMap(r => r.history.map(p => p.date)))].sort();
    return dates.map(date => {
      const returns = valid.map(r => ({value: r.history.filter(p => p.date <= date).at(-1)?.returnPct, weight: weight(r)})).filter(p => Number.isFinite(p.value));
      const totalWeight = returns.reduce((sum, p) => sum + p.weight, 0);
      return { date, returnPct: totalWeight ? returns.reduce((sum, p) => sum + p.value * p.weight, 0) / totalWeight : null };
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
