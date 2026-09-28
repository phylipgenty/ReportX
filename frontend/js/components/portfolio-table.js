import { el } from '../utils/dom.js';
import { formatMoney } from '../utils/currency.js';
import { formatVariance, varianceClass, formatDate } from '../utils/dates.js';
import { selectEntityName, selectDivisionName } from '../store.js';
import { badge } from '../utils/lookups.js';

/** README §28–§29: portfolio list; every project links to its detail page. */
export function PortfolioTable(projects) {
  if (!projects.length) {
    return el('div', { class: 'empty', text: 'No projects yet. Add one or import from Excel.' });
  }

  const thead = el('thead', {}, [el('tr', {}, [
    el('th', { text: 'Project' }),
    el('th', { text: 'Entity' }),
    el('th', { text: 'Division' }),
    el('th', { text: 'Completion' }),
    el('th', { text: 'Status' }),
    el('th', { text: 'TSC Approved' }),
    el('th', { text: 'Planned Go-Live' }),
    el('th', { text: 'Variance' }),
    el('th', { text: 'Budget' }),
    el('th', { text: 'Actual' }),
  ])]);

  const tbody = el('tbody');
  for (const p of projects) {
    const variance = p.schedule.variance_days;
    const completion = p.identity.completion_pct ?? 0;

    tbody.appendChild(el('tr', {}, [
      el('td', { class: 'name' }, [
        el('a', { href: `#/project/${p.id}`, text: p.identity.name }),
        el('div', { class: 'text-xs text-muted' }, [
          el('a', { href: `#/project/${p.id}`, class: 'text-muted', text: p.id }),
          p.is_draft ? el('span', { class: 'badge warning', style: { marginLeft: '6px' }, text: 'Draft' }) : null,
        ]),
      ]),
      el('td', { text: selectEntityName(p.identity.entity_id) }),
      el('td', { text: selectDivisionName(p.identity.division_id) }),
      el('td', {}, [
        el('div', { class: 'progress' }, [
          el('div', { class: 'bar' }, [el('span', { style: { width: `${completion}%` } })]),
          el('span', { class: 'pct', text: `${completion}%` }),
        ]),
      ]),
      el('td', {}, [badge('project_status', p.identity.status)]),
      el('td', { text: formatDate(p.schedule.tsc_approved_date) }),
      el('td', { text: formatDate(p.schedule.actual_delivery || p.schedule.forecast_delivery) }),
      el('td', { class: `perf-value ${varianceClass(variance)}`, text: formatVariance(variance) }),
      el('td', { text: formatMoney(p.resources.planned_budget, { compact: true }) }),
      el('td', { text: formatMoney(p.resources.actual_cost_to_date, { compact: true }) }),
    ]));
  }

  return el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [thead, tbody])]);
}
