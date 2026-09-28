import { el, toast } from '../utils/dom.js';
import { api } from '../api.js';
import { getState, ensureBootstrap, can } from '../store.js';

export function CostAssumptionsForm({ onSaved } = {}) {
  const rates = getState().bootstrap?.cost_assumptions || {};

  const junior = el('input', { type: 'number', value: rates.junior_rate ?? 0 });
  const inter  = el('input', { type: 'number', value: rates.intermediate_rate ?? 0 });
  const expert = el('input', { type: 'number', value: rates.expert_rate ?? 0 });
  const cont   = el('input', { type: 'number', value: rates.contingency_pct ?? 0, step: '0.1' });

  const editable = can('costs');
  if (!editable) [junior, inter, expert, cont].forEach(i => { i.disabled = true; });

  const form = el('div', { class: 'card' }, [
    el('div', { class: 'card-header' }, [
      el('div', {}, [
        el('div', { class: 'card-title', text: 'Cost assumptions' }),
        el('div', { class: 'card-subtitle', text: 'Every project’s planned resource cost is calculated from these rates. Changing them updates all projects.' }),
      ]),
    ]),
    el('div', { class: 'form-grid' }, [
      field('Junior — Level 1 (day rate)', junior),
      field('Intermediate — Level 2 (day rate)', inter),
      field('Expert — Level 3 (day rate)', expert),
      field('Contingency (%)', cont),
    ]),
    !editable ? el('p', { class: 'text-sm text-muted', style: { marginTop: '12px' }, text: 'Only PMO and Admin can change cost rates.' }) : null,
    !editable ? null : el('div', { class: 'flex gap-2', style: { marginTop: '16px' } }, [
      el('button', {
        class: 'btn btn-primary',
        text: 'Save assumptions',
        onclick: async () => {
          try {
            const updated = await api.costs.update({
              junior_rate: Number(junior.value),
              intermediate_rate: Number(inter.value),
              expert_rate: Number(expert.value),
              contingency_pct: Number(cont.value),
              currency: getState().bootstrap.cost_assumptions.currency,
              currency_symbol: getState().bootstrap.cost_assumptions.currency_symbol,
            });
            await ensureBootstrap(true);
            toast(`Cost assumptions saved — contingency ${updated.contingency_pct}%`, 'success');
            onSaved && onSaved();
          } catch (e) {
            toast(e.message || 'Save failed', 'error');
          }
        },
      }),
    ]),
  ]);

  return form;
}

function field(label, input) {
  return el('div', { class: 'field' }, [el('label', { text: label }), input]);
}