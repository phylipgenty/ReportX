import { el } from '../utils/dom.js';
import { selectMilestoneDefs } from '../store.js';
import { formatDate, formatDateRange } from '../utils/dates.js';
import { badge } from '../utils/lookups.js';

export function MilestoneTrackerGrid(projects) {
  const defs = selectMilestoneDefs();
  const last = defs[defs.length - 1];   // final lifecycle milestone (Go-Live)

  const thead = el('thead', {}, [el('tr', {}, [
    el('th', { text: 'Project' }),
    ...defs.map(d => el('th', { title: d.label }, [
      el('div', { text: d.short_label }),
      el('span', { class: 'sub', text: `${d.order}/${defs.length}` }),
    ])),
    el('th', { text: last ? `${last.short_label} date` : '' }),
  ])]);

  const tbody = el('tbody');
  if (!projects.length) {
    tbody.appendChild(el('tr', {}, [
      el('td', { colspan: String(defs.length + 2) }, [el('div', { class: 'empty', text: 'No projects.' })]),
    ]));
  }

  for (const p of projects) {
    const byKey = Object.fromEntries(p.milestones.map(m => [m.key, m]));
    const final = (last && byKey[last.key]) || {};

    tbody.appendChild(el('tr', {}, [
      el('td', { class: 'project-cell' }, [
        el('a', { href: `#/project/${p.id}`, class: 'name', text: p.identity.name }),
        el('div', { class: 'meta', text: `${p.id} · ${p.identity.completion_pct}%` }),
      ]),
      ...defs.map(d => {
        const m = byKey[d.key] || {};
        const dates = m.actual_date ? formatDate(m.actual_date) : formatDateRange(m.baseline_date, m.expected_date);
        return el('td', { title: dates }, [badge('milestone_status', m.status)]);
      }),
      el('td', { class: 'go-live-cell', text: final.actual_date ? formatDate(final.actual_date) : formatDateRange(final.baseline_date, final.expected_date) }),
    ]));
  }

  return el('div', { class: 'tracker-scroll' }, [el('table', { class: 'tracker' }, [thead, tbody])]);
}
