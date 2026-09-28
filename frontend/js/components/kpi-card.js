import { el } from '../utils/dom.js';

/**
 * KPI tile. All strings come from the caller (server-derived), never hard-coded.
 */
export function KpiCard({ label, value, foot, barPct }) {
  return el('div', { class: 'kpi' }, [
    el('div', { class: 'kpi-label', text: label }),
    el('div', { class: 'kpi-value', text: value }),
    foot ? el('div', { class: 'kpi-foot', text: foot }) : null,
    barPct != null
      ? el('div', { class: 'kpi-bar' }, [
          el('span', { style: { width: `${Math.min(100, Math.max(0, barPct))}%` } }),
        ])
      : null,
  ]);
}