import { el, openModal, toast, confirmDialog } from '../utils/dom.js';
import { api } from '../api.js';
import { badge, labelOf, lookupSelect, option } from '../utils/lookups.js';
import { section } from './issues-panel.js';

/** README §19: probability, impact and a system-calculated score (P × I). */
export function RisksPanel(project, reload, editable) {
  const add = !editable ? null : el('button', { class: 'btn btn-outline btn-sm', text: '+ Add risk', onclick: () => openRiskForm(project, null, reload) });

  const body = project.risks.length
    ? el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
        el('thead', {}, [el('tr', {}, ['Priority', 'Probability', 'Impact', 'Score', 'Risk', 'Impact summary', 'Response strategy', 'Status', '']
          .map(t => el('th', { text: t })))]),
        el('tbody', {}, project.risks.map(r => el('tr', {}, [
          el('td', {}, [badge('issue_priority', r.priority)]),
          el('td', { text: `${r.probability} – ${labelOf('probability', r.probability)}` }),
          el('td', { text: `${r.impact} – ${labelOf('impact', r.impact)}` }),
          el('td', {}, [el('strong', { text: String(r.risk_score) })]),
          el('td', { class: 'wrap', text: r.description }),
          el('td', { class: 'wrap', text: r.impact_summary }),
          el('td', { class: 'wrap', text: r.response_strategy }),
          el('td', {}, [badge('risk_status', r.status)]),
          el('td', { class: 'row-actions' }, !editable ? [] : [
            el('button', { class: 'btn btn-ghost btn-sm', text: 'Edit', onclick: () => openRiskForm(project, r, reload) }),
            el('button', {
              class: 'btn btn-ghost btn-sm', text: 'Delete',
              onclick: async () => {
                if (!(await confirmDialog('Delete this risk?', { confirmText: 'Delete' }))) return;
                try { await api.risks.remove(project.id, r.id); toast('Risk deleted', 'success'); reload(); }
                catch (e) { toast(e.message, 'error'); }
              },
            }),
          ]),
        ]))),
      ])])
    : el('div', { class: 'empty', text: 'No risks recorded.' });

  return section('Risks', body, add);
}

function openRiskForm(project, risk, reload) {
  const r = risk || {};
  const priority = lookupSelect('issue_priority', r.priority);
  const probability = lookupSelect('probability', r.probability, { labelFn: o => `${o.value} – ${o.label} (${o.range})` });
  const impact = lookupSelect('impact', r.impact, { labelFn: o => `${o.value} – ${o.label}` });
  const status = lookupSelect('risk_status', r.status);
  const description = textarea(r.description, 'What could happen?');
  const impactSummary = textarea(r.impact_summary, 'Impact summary');
  const response = textarea(r.response_strategy, 'Response strategy');
  const score = el('div', { class: 'score-preview' });
  const impactHelp = el('div', { class: 'text-xs text-muted' });

  // Display-only preview; the saved score is always calculated by the server.
  const refresh = () => {
    score.textContent = `Risk score: ${Number(probability.value) * Number(impact.value)}`;
    impactHelp.textContent = option('impact', impact.value)?.description || '';
  };
  probability.addEventListener('change', refresh);
  impact.addEventListener('change', refresh);

  const save = el('button', { class: 'btn btn-primary', text: risk ? 'Save risk' : 'Add risk' });
  const modal = openModal({
    title: risk ? 'Edit risk' : 'Add risk',
    body: el('div', {}, [
      el('div', { class: 'form-grid' }, [
        field('Priority', priority), field('Status', status),
        field('Probability of occurrence', probability), field('Impact', el('div', {}, [impact, impactHelp])),
      ]),
      score,
      field('Risk description', description),
      field('Impact summary', impactSummary),
      field('Response strategy', response),
    ]),
    footer: [save],
  });
  refresh();

  save.addEventListener('click', async () => {
    if (!description.value.trim()) { toast('Describe the risk', 'error'); return; }
    const payload = {
      priority: priority.value, status: status.value,
      probability: Number(probability.value), impact: Number(impact.value),
      description: description.value, impact_summary: impactSummary.value, response_strategy: response.value,
    };
    save.disabled = true;
    try {
      if (risk) await api.risks.update(project.id, risk.id, payload);
      else await api.risks.add(project.id, payload);
      toast('Risk saved', 'success');
      modal.close();
      reload();
    } catch (e) { toast(e.message, 'error'); save.disabled = false; }
  });
}

function field(label, node) {
  return el('div', { class: 'field' }, [el('label', { text: label }), node]);
}
function textarea(value, placeholder) {
  const t = el('textarea', { placeholder });
  t.value = value || '';
  return t;
}
