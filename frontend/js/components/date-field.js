import { el } from '../utils/dom.js';
import { options, isDatePlaceholder } from '../utils/lookups.js';

/**
 * Milestone date input (README §12): a real date, a placeholder from the
 * `date_placeholder` lookup (TBD / N/A), or empty. Returns { node, value() }.
 */
export function DateField(value) {
  const mode = el('select', { class: 'date-mode' }, [
    el('option', { value: 'date', text: 'Date' }),
    ...options('date_placeholder').map(o => el('option', { value: o.value, text: o.label })),
  ]);
  const date = el('input', { type: 'date' });

  if (isDatePlaceholder(value)) mode.value = value;
  else { mode.value = 'date'; date.value = value || ''; }

  const sync = () => { date.style.display = mode.value === 'date' ? '' : 'none'; };
  mode.addEventListener('change', sync);
  sync();

  return {
    node: el('div', { class: 'date-field' }, [mode, date]),
    value: () => (mode.value === 'date' ? (date.value || null) : mode.value),
  };
}
