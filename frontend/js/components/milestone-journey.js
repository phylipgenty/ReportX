import { el } from '../utils/dom.js';
import { selectMilestoneDefs } from '../store.js';
import { formatDate } from '../utils/dates.js';
import { badge, toneOf } from '../utils/lookups.js';

// Journey step styling keyed by lookup tone (presentation only).
const STEP_CLASS = { positive: 'done', info: 'wip', danger: 'delayed', warning: 'pending', neutral: 'pending', muted: 'na' };

/** README §10 / §46: BRD → SSD → … → Go-Live with each milestone's status. */
export function MilestoneJourney(milestones, { onSelect } = {}) {
  const byKey = Object.fromEntries(milestones.map(m => [m.key, m]));

  const row = el('div', { class: 'journey' });
  for (const d of selectMilestoneDefs()) {
    const m = byKey[d.key] || {};
    const dateLabel = m.actual_date
      ? formatDate(m.actual_date)
      : m.expected_date ? `Exp. ${formatDate(m.expected_date)}`
      : m.baseline_date ? `Base. ${formatDate(m.baseline_date)}`
      : 'Not set';

    row.appendChild(
      el('div', {
        class: `journey-step ${STEP_CLASS[toneOf('milestone_status', m.status)] || 'pending'} ${onSelect ? 'clickable' : ''}`,
        title: d.label,
        onclick: onSelect ? () => onSelect(d.key) : null,
      }, [
        el('div', { class: 'num', text: String(d.order) }),
        el('div', { class: 'label', text: d.short_label }),
        el('div', { class: 'date', text: dateLabel }),
        badge('milestone_status', m.status),
      ])
    );
  }
  return row;
}
