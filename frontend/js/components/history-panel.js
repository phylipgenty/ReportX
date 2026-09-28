import { el, openModal, toast } from '../utils/dom.js';
import { api } from '../api.js';
import { formatDate, formatDateTime, formatVariance } from '../utils/dates.js';
import { badge, labelOf, milestoneLabel } from '../utils/lookups.js';
import { formatMoney } from '../utils/currency.js';
import { selectEntityName, selectDivisionName } from '../store.js';
import { section } from './issues-panel.js';

/** README §13 / §39–§40: saved project states and the full change log. */
export function HistoryPanel(project, states, changes = []) {
  const stateList = states.length
    ? el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
        el('thead', {}, [el('tr', {}, ['Saved', 'Label', 'By', ''].map(t => el('th', { text: t })))]),
        el('tbody', {}, states.map(s => el('tr', {}, [
          el('td', { text: formatDateTime(s.saved_at) }),
          el('td', { text: s.label || '—' }),
          el('td', { text: s.saved_by }),
          el('td', { class: 'row-actions' }, [
            el('button', { class: 'btn btn-ghost btn-sm', text: 'View', onclick: () => viewState(project.id, s.id) }),
          ]),
        ]))),
      ])])
    : el('div', { class: 'empty', text: 'No saved states yet. Use “Save state” to keep a point-in-time copy.' });

  // Filter by area so long histories stay readable.
  const areas = [...new Set(changes.map(c => c.area))];
  const filter = el('select', {}, [
    el('option', { value: '', text: 'All changes' }),
    ...areas.map(a => el('option', { value: a, text: AREA_LABELS[a] || a })),
  ]);
  const logHost = el('div', {});
  const renderLog = () => {
    const rows = changes.filter(c => !filter.value || c.area === filter.value);
    logHost.innerHTML = '';
    logHost.appendChild(rows.length
      ? el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
          el('thead', {}, [el('tr', {}, ['When', 'What', 'Change', 'By', 'Note'].map(t => el('th', { text: t })))]),
          el('tbody', {}, rows.map(c => el('tr', {}, [
            el('td', { text: formatDateTime(c.changed_at) }),
            el('td', { class: 'wrap' }, [
              el('div', { text: whatChanged(c) }),
              c.source === 'import' ? el('span', { class: 'badge info', text: 'Import' }) : null,
            ]),
            el('td', { class: 'wrap', text: describe(c) }),
            el('td', { text: c.changed_by }),
            el('td', { class: 'wrap', text: c.note || '—' }),
          ]))),
        ])])
      : el('div', { class: 'empty', text: 'No changes recorded yet.' }));
  };
  filter.addEventListener('change', renderLog);
  renderLog();

  return section('History', el('div', {}, [
    el('div', { class: 'card-subtitle', text: 'Saved states' }), stateList,
    el('div', { class: 'flex-between', style: { marginTop: '16px' } }, [
      el('div', { class: 'card-subtitle', text: 'Change log' }), filter,
    ]),
    logHost,
  ]));
}

const AREA_LABELS = {
  project: 'Project details', milestone: 'Milestones', issue: 'Issues', risk: 'Risks',
  document: 'Documents', state: 'Saved states', costs: 'Cost rates',
};

const FIELD_LABELS = {
  'identity.name': 'Project name', 'identity.entity_id': 'Entity', 'identity.division_id': 'Division',
  'identity.description': 'Description', 'identity.project_manager': 'Project manager',
  'identity.manager_user_id': 'Manager account', 'identity.status': 'Status', 'identity.status_update': 'Status update',
  'identity.weight_pct': 'Weight %', 'identity.executive_sponsor': 'Executive sponsor',
  'identity.delivery_organisation': 'Delivery organisation',
  'schedule.start_date': 'Start date', 'schedule.original_baseline': 'Original baseline',
  'schedule.tsc_approved_date': 'TSC approved date', 'schedule.planned_delivery': 'Planned delivery',
  'schedule.forecast_delivery': 'Forecast delivery', 'schedule.actual_delivery': 'Actual delivery',
  'resources.junior_days': 'Junior days', 'resources.intermediate_days': 'Intermediate days',
  'resources.expert_days': 'Expert days', 'resources.other_planned_costs': 'Other planned costs',
  'resources.actual_cost_to_date': 'Actual cost to date',
  'rag.schedule': 'Schedule RAG', 'rag.budget': 'Budget RAG', 'rag.issues': 'Issues RAG',
  'rag.schedule_comment': 'Schedule commentary', 'rag.budget_comment': 'Budget commentary', 'rag.issues_comment': 'Issues commentary',
  executive_summary: 'Executive summary', is_draft: 'Draft',
  'planned_activities.accomplishments': 'Planned accomplishments',
  'planned_activities.not_accomplished': 'Planned but not accomplished',
  'planned_activities.next_period': 'Planned actions for next period',
  status: 'Status', baseline_date: 'Baseline date', expected_date: 'Expected date', actual_date: 'Actual date',
  note: 'Note', priority: 'Priority', description: 'Description', impact_summary: 'Impact summary',
  impact_areas: 'Impact areas', action_steps: 'Action steps', milestone_key: 'Milestone',
  probability: 'Probability', impact: 'Impact', response_strategy: 'Response strategy',
  junior_rate: 'Junior day rate', intermediate_rate: 'Intermediate day rate', expert_rate: 'Expert day rate',
  contingency_pct: 'Contingency %', file: 'File',
};

function whatChanged(c) {
  const area = AREA_LABELS[c.area] || c.area;
  if (c.area === 'milestone') return `Milestone · ${c.item_label}`;
  if (c.area === 'project') return c.action === 'created' ? 'Project created' : area;
  if (c.area === 'state') return 'Saved state';
  if (c.area === 'costs') return 'Cost rates (all projects)';
  if (c.area === 'document') return `Document${c.item_label ? ` · ${milestoneLabel(c.item_label)}` : ''}`;
  const item = c.item_label ? ` · ${truncate(c.item_label, 60)}` : '';
  return `${c.area === 'issue' ? 'Issue' : 'Risk'} ${c.action}${item}`;
}

function describe(c) {
  if (c.area === 'state') return `Saved “${c.item_label || 'Untitled'}”`;
  if (c.action === 'created') return c.area === 'project' ? c.item_label : 'Added';
  if (c.action === 'deleted') return c.field === 'file' ? `Removed ${c.old}` : 'Deleted';
  if (c.action === 'uploaded') return `Uploaded ${c.new}`;
  if (c.action === 'replaced') return `${c.old || '—'} → ${c.new}`;
  const label = FIELD_LABELS[c.field] || c.field;
  return `${label}: ${fmt(c.field, c.old)} → ${fmt(c.field, c.new)}`;
}

function fmt(field, v) {
  if (v === null || v === undefined || v === '' || (Array.isArray(v) && !v.length)) return '—';
  const f = field || '';
  if (Array.isArray(v)) return v.join('; ');
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  if (f === 'identity.entity_id') return selectEntityName(v);
  if (f === 'identity.division_id') return selectDivisionName(v);
  if (f.endsWith('status') && f.startsWith('identity')) return labelOf('project_status', v);
  if (f === 'status') return String(v);
  if (/^rag\.(schedule|budget|issues)$/.test(f)) return labelOf('rag', v);
  if (f.endsWith('_date') || f.startsWith('schedule.')) return formatDate(v);
  if (/rate$|cost|costs$/.test(f)) return formatMoney(v);
  if (f === 'milestone_key') return milestoneLabel(v);
  return truncate(String(v), 140);
}

function truncate(s, n) {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

async function viewState(projectId, stateId) {
  try {
    const s = await api.states.get(projectId, stateId);
    const p = s.snapshot;
    const kv = (k, v) => el('div', { class: 'flex-between kv' }, [el('span', { class: 'text-muted', text: k }), v]);
    openModal({
      title: `Saved state · ${s.label || formatDateTime(s.saved_at)}`,
      size: 'wide',
      body: el('div', {}, [
        el('p', { class: 'text-sm text-muted', text: `Saved ${formatDateTime(s.saved_at)} by ${s.saved_by}` }),
        el('div', { class: 'detail-grid' }, [
          el('div', {}, [
            kv('Status', badge('project_status', p.identity.status)),
            kv('Completion', el('span', { text: `${p.identity.completion_pct}%` })),
            kv('Forecast delivery', el('span', { text: formatDate(p.schedule.forecast_delivery) })),
            kv('Variance', el('span', { text: formatVariance(p.schedule.variance_days) })),
            kv('Planned budget', el('span', { text: formatMoney(p.resources.planned_budget) })),
            kv('Actual cost', el('span', { text: formatMoney(p.resources.actual_cost_to_date) })),
            kv('RAG', el('span', {}, [badge('rag', p.rag.schedule), ' ', badge('rag', p.rag.budget), ' ', badge('rag', p.rag.issues)])),
            kv('Issues / risks', el('span', { text: `${p.issues.length} / ${p.risks.length}` })),
          ]),
          el('div', {}, p.milestones.map(m => kv(milestoneLabel(m.key), badge('milestone_status', m.status)))),
        ]),
      ]),
    });
  } catch (e) { toast(e.message, 'error'); }
}
