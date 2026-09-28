import { el } from '../utils/dom.js';
import { formatMoney } from '../utils/currency.js';

/**
 * Schedule performance row: label | diverging bar | value.
 * days: number (can be negative), null => "Not set".
 */
export function SchedulePerformanceRow({ label, days }) {
  const valueText =
    days == null ? 'Not set'
    : days === 0 ? 'On date'
    : (days > 0 ? '+' : '') + days + ' days';

  const valueCls =
    days == null ? 'muted'
    : days === 0 ? ''
    : days > 0 ? 'late'
    : 'early';

  // bar: right half = late (red), left half = early (green)
  const track = el('div', { class: 'perf-track diverge' });
  if (days != null && days !== 0) {
    const mag = Math.min(50, Math.abs(days) / 8); // scale roughly
    const fill = el('div', {
      class: 'perf-fill',
      style: {
        left:  days > 0 ? '50%' : `calc(50% - ${mag}%)`,
        right: days > 0 ? `calc(50% - ${mag}%)` : '50%',
        background: days > 0 ? 'var(--danger)' : 'var(--positive)',
      },
    });
    track.appendChild(fill);
  }

  return el('div', { class: 'perf-row' }, [
    el('div', { class: 'perf-label', text: label, title: label }),
    track,
    el('div', { class: `perf-value ${valueCls}`, text: valueText }),
  ]);
}

/**
 * Cost performance row: two overlapping bars (budget vs actual).
 */
export function CostPerformanceRow({ label, budget, actual }) {
  const max = Math.max(budget || 0, actual || 0, 1);
  const budgetPct = ((budget || 0) / max) * 100;
  const actualPct = ((actual || 0) / max) * 100;
  const ahead = (actual || 0) > (budget || 0);

  const track = el('div', { class: 'perf-track' });
  track.appendChild(el('div', {
    class: 'perf-fill',
    style: { left: '0', width: `${budgetPct}%`, background: 'var(--cream-200)' },
  }));
  track.appendChild(el('div', {
    class: 'perf-fill',
    style: {
      left: '0', width: `${actualPct}%`,
      background: ahead ? 'var(--gold-500)' : 'var(--navy-800)',
    },
  }));

  return el('div', { class: 'perf-row' }, [
    el('div', { class: 'perf-label', text: label, title: label }),
    track,
    el('div', { class: 'perf-value', text: `${formatMoney(actual, { compact: true })} / ${formatMoney(budget, { compact: true })}` }),
  ]);
}