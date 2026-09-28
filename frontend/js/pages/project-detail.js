import { el, mount, toast, openModal } from '../utils/dom.js';
import { api } from '../api.js';
import { ensureBootstrap, selectEntityName, selectDivisionName, canEditProject } from '../store.js';
import { renderTopbar } from '../components/topbar.js';
import { MilestoneJourney } from '../components/milestone-journey.js';
import { openMilestoneUpdateForm } from '../components/milestone-update-form.js';
import { IssuesPanel } from '../components/issues-panel.js';
import { RisksPanel } from '../components/risks-panel.js';
import { DocumentsPanel } from '../components/documents-panel.js';
import { HistoryPanel } from '../components/history-panel.js';
import { openReportDialog } from '../components/report-dialog.js';
import { badge, milestoneLabel } from '../utils/lookups.js';
import { formatMoney } from '../utils/currency.js';
import { formatDate, formatVariance, varianceClass } from '../utils/dates.js';

/** README §30: the single-project view with all project information. */
export async function ProjectDetailPage({ topbar, view, params }) {
  const { id } = params;
  renderTopbar(topbar, { eyebrow: 'Project', title: 'Loading…', actions: [] });
  mount(view, el('div', { class: 'loader', text: 'Loading project…' }));

  const load = async () => {
    try {
      await ensureBootstrap();
      const [project, states, changes] = await Promise.all([api.projects.get(id), api.states.list(id), api.states.changes(id)]);
      render(project, states, changes);
    } catch (e) {
      mount(view, el('div', { class: 'empty', text: `Failed: ${e.message}` }));
    }
  };
  await load();

  function render(project, states, changes) {
    const editable = canEditProject(project);
    renderTopbar(topbar, {
      eyebrow: `${project.id}${project.is_draft ? ' · Draft' : ''}`,
      title: project.identity.name,
      actions: [
        editable ? el('a', { class: 'btn btn-outline', text: 'Edit project', href: `#/project/${project.id}/edit` }) : null,
        editable ? el('button', { class: 'btn btn-outline', text: 'Save state', onclick: () => saveState(project, load) }) : null,
        el('button', { class: 'btn btn-primary', text: 'Generate report', onclick: () => openReportDialog(project) }),
      ].filter(Boolean),
    });

    const i = project.identity, s = project.schedule, r = project.resources;

    const identity = card('Project identity', [
      el('div', { class: 'flex gap-2', style: { marginBottom: '8px' } }, [
        badge('project_status', i.status),
        project.is_draft ? el('span', { class: 'badge warning', text: 'Draft' }) : null,
      ]),
      kv('Project ID', project.id),
      kv('Entity / subsidiary', selectEntityName(i.entity_id)),
      kv('Division', selectDivisionName(i.division_id)),
      kv('Project manager', i.project_manager),
      kv('Executive sponsor', i.executive_sponsor),
      kv('Delivery organisation', i.delivery_organisation),
      kv('Percentage completion', `${i.completion_pct}%`),
      i.weight_pct != null ? kv('Weight % (imported)', `${i.weight_pct}`) : null,
      i.description ? el('p', { class: 'text-sm', style: { marginTop: '12px' }, text: i.description }) : null,
    ]);

    const milestones = card('Milestones', [
      editable ? el('p', { class: 'text-sm text-muted', text: 'Select a milestone to update its status, dates and notes.' }) : null,
      MilestoneJourney(project.milestones, { onSelect: editable ? (key) => openMilestoneUpdateForm(project, key, load) : null }),
      el('div', { class: 'table-wrap', style: { marginTop: '16px' } }, [el('table', { class: 'data' }, [
        el('thead', {}, [el('tr', {}, ['Milestone', 'Status', 'Baseline', 'Expected', 'Actual', 'Note', ''].map(t => el('th', { text: t })))]),
        el('tbody', {}, project.milestones.map(m => el('tr', {}, [
          el('td', { text: milestoneLabel(m.key, { short: false }) }),
          el('td', {}, [badge('milestone_status', m.status)]),
          el('td', { text: formatDate(m.baseline_date) }),
          el('td', { text: formatDate(m.expected_date) }),
          el('td', { text: formatDate(m.actual_date) }),
          el('td', { class: 'wrap', text: m.note || '—' }),
          el('td', { class: 'row-actions' }, editable ? [
            el('button', { class: 'btn btn-ghost btn-sm', text: 'Update', onclick: () => openMilestoneUpdateForm(project, m.key, load) }),
          ] : []),
        ]))),
      ])]),
    ]);

    const schedule = card('Schedule', [
      kv('Start date', formatDate(s.start_date)),
      kv('Original baseline', formatDate(s.original_baseline)),
      kv('TSC approved date', formatDate(s.tsc_approved_date)),
      kv('Planned delivery', formatDate(s.planned_delivery)),
      kv('Forecast delivery', formatDate(s.forecast_delivery)),
      kv('Actual delivery', formatDate(s.actual_delivery)),
      el('div', { class: 'flex-between kv' }, [
        el('span', { class: 'text-muted', text: 'Schedule variance' }),
        el('strong', { class: `perf-value ${varianceClass(s.variance_days)}`, text: formatVariance(s.variance_days) }),
      ]),
    ]);

    const cost = card('Cost and resources', [
      kv('Junior days', String(r.junior_days)),
      kv('Intermediate days', String(r.intermediate_days)),
      kv('Expert days', String(r.expert_days)),
      kv('Resource cost', formatMoney(r.resource_cost)),
      kv('Contingency', formatMoney(r.contingency)),
      kv('Other planned costs', formatMoney(r.other_planned_costs)),
      kv('Planned budget', formatMoney(r.planned_budget), true),
      kv('Actual cost to date', formatMoney(r.actual_cost_to_date), true),
    ]);

    const ragRow = (label, key) => el('div', { class: 'kv' }, [
      el('div', { class: 'flex-between' }, [el('span', { class: 'text-muted', text: label }), badge('rag', project.rag[key])]),
      project.rag[`${key}_comment`] ? el('div', { class: 'text-sm prewrap', style: { marginTop: '4px' }, text: project.rag[`${key}_comment`] }) : null,
    ]);
    const rag = card('RAG', [ragRow('Schedule', 'schedule'), ragRow('Budget', 'budget'), ragRow('Issues', 'issues')]);

    const status = card('Status update', [el('p', { class: 'prewrap', text: i.status_update || 'No status update yet.' })]);
    const summary = card('Executive summary', [el('p', { class: 'prewrap', text: project.executive_summary || 'No executive summary yet.' })]);

    const pa = project.planned_activities;
    const list = (xs) => xs.length ? el('ul', { class: 'plain-list' }, xs.map(x => el('li', { text: x }))) : el('p', { class: 'text-muted text-sm', text: 'None recorded.' });
    const activities = card('Planned activities', [
      el('div', { class: 'card-subtitle', text: 'Planned accomplishments' }), list(pa.accomplishments),
      el('div', { class: 'card-subtitle', text: 'Planned but not accomplished' }), list(pa.not_accomplished),
      el('div', { class: 'card-subtitle', text: 'Planned actions for next period' }), list(pa.next_period),
    ]);

    mount(view, el('div', {}, [
      el('div', { class: 'detail-grid' }, [
        el('div', {}, [identity, status, summary]),
        el('div', {}, [schedule, rag, cost]),
      ]),
      milestones,
      activities,
      IssuesPanel(project, load, editable),
      RisksPanel(project, load, editable),
      DocumentsPanel(project, load, editable),
      HistoryPanel(project, states, changes),
    ]));
  }
}

function saveState(project, onDone) {
  const label = el('input', { type: 'text', placeholder: 'e.g. September status' });
  const save = el('button', { class: 'btn btn-primary', text: 'Save state' });
  const m = openModal({
    title: 'Save project state',
    body: el('div', {}, [
      el('p', { class: 'text-sm text-muted', text: 'Keeps an unchangeable copy of the project as it is now, for history and reporting.' }),
      el('div', { class: 'field' }, [el('label', { text: 'Label' }), label]),
    ]),
    footer: [save],
  });
  save.addEventListener('click', async () => {
    save.disabled = true;
    try {
      await api.states.save(project.id, label.value);
      toast('Project state saved', 'success');
      m.close();
      onDone();
    } catch (e) { toast(e.message, 'error'); save.disabled = false; }
  });
}

function card(title, children) {
  return el('div', { class: 'card stack' }, [
    el('div', { class: 'card-header' }, [el('div', { class: 'card-title', text: title })]),
    ...children.filter(Boolean),
  ]);
}

function kv(label, value, strong = false) {
  return el('div', { class: 'flex-between kv' }, [
    el('span', { class: 'text-muted', text: label }),
    el(strong ? 'strong' : 'span', { text: value || '—' }),
  ]);
}
