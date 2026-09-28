/**
 * Lookup helpers. Every status, RAG, priority and matrix value — and its
 * label and visual tone — comes from /api/bootstrap, never from the code.
 */
import { el } from './dom.js';
import { getState, selectMilestoneDefs } from '../store.js';

export function options(kind) {
  return getState().bootstrap?.lookups?.[kind] || [];
}

export function option(kind, value) {
  return options(kind).find(o => o.value === String(value));
}

export function labelOf(kind, value) {
  if (value == null || value === '') return '—';
  return option(kind, value)?.label ?? String(value);
}

export function toneOf(kind, value) {
  return option(kind, value)?.tone || 'neutral';
}

export function badge(kind, value) {
  return el('span', { class: `badge ${toneOf(kind, value)}`, text: labelOf(kind, value) });
}

/** <select> built from a lookup; with no value it preselects the lookup's
 *  `is_default` option. `blank` adds an empty first option. */
export function lookupSelect(kind, value, { blank, labelFn } = {}) {
  const opts = options(kind);
  const wanted = value == null || value === ''
    ? (blank ? '' : (opts.find(o => o.is_default) || opts[0])?.value)
    : String(value);
  const children = blank ? [el('option', { value: '', text: blank })] : [];
  for (const o of opts) {
    children.push(el('option', {
      value: o.value,
      text: labelFn ? labelFn(o) : o.label,
      selected: wanted === o.value ? 'selected' : null,
    }));
  }
  return el('select', {}, children);
}

export function milestoneLabel(key, { short = true } = {}) {
  const d = selectMilestoneDefs().find(x => x.key === key);
  return d ? (short ? d.short_label : d.label) : key;
}

export function isDatePlaceholder(value) {
  return options('date_placeholder').some(o => o.value === value);
}
