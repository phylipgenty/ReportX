import { el, mount } from '../utils/dom.js';
import { api } from '../api.js';
import { ensureBootstrap } from '../store.js';
import { renderTopbar } from '../components/topbar.js';
import { CostAssumptionsForm } from '../components/cost-assumptions-form.js';
import { formatMoney } from '../utils/currency.js';

export async function CostAssumptionsPage({ topbar, view }) {
  renderTopbar(topbar, {
    eyebrow: 'Administration',
    title: 'Cost assumptions',
    actions: [
      el('a', { class: 'btn btn-outline', text: 'Back to dashboard', href: '#/dashboard' }),
    ],
  });

  mount(view, el('div', { class: 'loader', text: 'Loading…' }));

  await ensureBootstrap();
  const rows = await api.costs.byProject();

  const table = el('div', { class: 'card', style: { padding: 0, marginTop: '24px', overflow: 'hidden' } }, [
    el('div', { class: 'card-header', style: { padding: '20px' } }, [
      el('div', {}, [
        el('div', { class: 'card-title', text: 'Planned resource cost by project' }),
        el('div', { class: 'card-subtitle', text: 'Days per level come from each project’s data entry.' }),
      ]),
    ]),
    el('div', { class: 'table-wrap', style: { border: 'none', borderRadius: 0 } }, [
      el('table', { class: 'data' }, [
        el('thead', {}, [el('tr', {}, [
          el('th', { text: 'Project' }),
          el('th', { text: 'Junior days' }),
          el('th', { text: 'Intermediate days' }),
          el('th', { text: 'Expert days' }),
          el('th', { text: 'Resource cost' }),
          el('th', { text: 'Contingency' }),
          el('th', { text: 'Planned cost' }),
        ])]),
        el('tbody', {}, rows.map(r => el('tr', {}, [
          el('td', {}, [el('a', { href: `#/project/${r.project_id}`, text: r.project_name })]),
          el('td', { text: String(r.junior_days) }),
          el('td', { text: String(r.intermediate_days) }),
          el('td', { text: String(r.expert_days) }),
          el('td', { text: formatMoney(r.resource_cost) }),
          el('td', { text: formatMoney(r.contingency) }),
          el('td', { text: formatMoney(r.planned_cost) }),
        ]))),
      ]),
    ]),
  ]);

  mount(view, el('div', {}, [CostAssumptionsForm({ onSaved: () => CostAssumptionsPage({ topbar, view }) }), table]));
}