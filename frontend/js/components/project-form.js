import { el, toast } from '../utils/dom.js';
import { api } from '../api.js';
import { getState, can } from '../store.js';
import { lookupSelect } from '../utils/lookups.js';
import { formatMoney } from '../utils/currency.js';
import { formatVariance } from '../utils/dates.js';

const CALCULATED = 'Calculated on save';

/**
 * README §47 project data-entry form: identity, schedule, resources/budget,
 * RAG, planned activities and executive summary. Calculated values are
 * shown read-only. Milestones, issues, risks and documents are maintained
 * on the Project Detail page (their changes are history-tracked there).
 */
export function ProjectForm({ project, onSaved, users = [] }) {
  const { bootstrap, user } = getState();
  const isEdit = !!project;
  const p = project || {
    identity: {}, schedule: {}, resources: {}, rag: {},
    planned_activities: { accomplishments: [], not_accomplished: [], next_period: [] },
    executive_summary: '',
  };

  const refSelect = (rows, value) => el('select', {}, rows.map(r =>
    el('option', { value: r.id, text: `${r.code} — ${r.name}`, selected: r.id === value ? 'selected' : null })));

  const name        = input('text', p.identity.name);
  const entitySel   = refSelect(bootstrap.entities, p.identity.entity_id);
  const divisionSel = refSelect(bootstrap.divisions, p.identity.division_id);
  // Project manager: a user account (drives edit rights, README §44). PMO/Admin pick
  // anyone; a Project Manager always manages their own projects. A free-text name
  // is kept for projects whose manager has no account (e.g. imported initials).
  const canAssign = can('project.edit_all');
  const pmUser = el('select', { disabled: canAssign ? null : 'disabled' }, [
    el('option', { value: '', text: '— no ReportX account —' }),
    ...users.map(u => el('option', { value: u.id, text: u.name })),
  ]);
  const currentPm = p.identity.manager_user_id || (!isEdit && !canAssign ? user.id : '');
  if (currentPm && !users.some(u => u.id === currentPm)) {   // e.g. a since-deactivated manager
    pmUser.appendChild(el('option', { value: currentPm, text: p.identity.project_manager || user.name }));
  }
  pmUser.value = currentPm;
  const pm = input('text', p.identity.project_manager);
  pm.placeholder = 'Name, if the manager has no account';
  const pmNameField = field('Manager name', pm);
  const syncPm = () => { pmNameField.style.display = pmUser.value ? 'none' : ''; };
  pmUser.addEventListener('change', syncPm);
  syncPm();
  const statusSel   = lookupSelect('project_status', p.identity.status);
  const description = textarea(p.identity.description, 'Brief description of the project');
  const sponsor     = input('text', p.identity.executive_sponsor);
  sponsor.placeholder = 'e.g. Finance Service Division';
  const deliveryOrg = input('text', p.identity.delivery_organisation);
  deliveryOrg.placeholder = 'Delivery team or vendor shown on the report cover';
  const statusUpd   = textarea(p.identity.status_update, 'Current status update / comments');

  const sched = {};
  for (const k of ['start_date', 'original_baseline', 'tsc_approved_date', 'planned_delivery', 'forecast_delivery', 'actual_delivery']) {
    sched[k] = input('date', p.schedule[k]);
  }

  const res = {};
  for (const k of ['junior_days', 'intermediate_days', 'expert_days', 'other_planned_costs', 'actual_cost_to_date']) {
    res[k] = input('number', p.resources[k] ?? 0);
    res[k].min = '0';
  }

  const rag = {};
  const ragNote = {};
  for (const k of ['schedule', 'budget', 'issues']) {
    rag[k] = lookupSelect('rag', p.rag[k]);
    ragNote[k] = textarea(p.rag[`${k}_comment`], 'Commentary shown beside this RAG in the report (one point per line)');
    ragNote[k].rows = 2;
  }

  const acts = {};
  for (const k of ['accomplishments', 'not_accomplished', 'next_period']) {
    acts[k] = textarea((p.planned_activities[k] || []).join('\n'), 'One activity per line');
  }
  const execSummary = textarea(p.executive_summary, 'Executive summary for the status report');
  execSummary.rows = 5;

  const payload = (isDraft) => ({
    identity: {
      name: name.value.trim(),
      entity_id: entitySel.value,
      division_id: divisionSel.value,
      project_manager: pm.value.trim(),
      ...(canAssign ? { manager_user_id: pmUser.value || null } : {}),
      status: statusSel.value,
      description: description.value,
      status_update: statusUpd.value,
      executive_sponsor: sponsor.value.trim(),
      delivery_organisation: deliveryOrg.value.trim(),
    },
    schedule: Object.fromEntries(Object.entries(sched).map(([k, n]) => [k, n.value || null])),
    resources: Object.fromEntries(Object.entries(res).map(([k, n]) => [k, Number(n.value || 0)])),
    rag: {
      ...Object.fromEntries(Object.entries(rag).map(([k, n]) => [k, n.value])),
      ...Object.fromEntries(Object.entries(ragNote).map(([k, n]) => [`${k}_comment`, n.value])),
    },
    planned_activities: Object.fromEntries(Object.entries(acts).map(([k, n]) =>
      [k, n.value.split('\n').map(s => s.trim()).filter(Boolean)])),
    executive_summary: execSummary.value,
    is_draft: isDraft,
  });

  const save = async (isDraft) => {
    if (!name.value.trim()) { toast('Project name is required', 'error'); name.focus(); return; }
    try {
      const saved = isEdit
        ? await api.projects.update(project.id, payload(isDraft))
        : await api.projects.create(payload(isDraft));
      toast(isDraft ? 'Draft saved' : 'Project saved', 'success');
      onSaved && onSaved(saved);
    } catch (e) {
      toast(e.message || 'Save failed', 'error');
    }
  };

  const calc = (label, value) => field(label, el('input', { disabled: 'disabled', value }));

  return el('div', {}, [
    el('div', { class: 'detail-grid' }, [
      el('div', {}, [
        card('Project identity', [
          field('Project name', name),
          el('div', { class: 'form-grid' }, [
            calc('Project ID', isEdit ? project.id : 'Generated on save'),
            field('Status', statusSel),
            field('Subsidiary / entity', entitySel),
            field('Division', divisionSel),
            field('Project manager', pmUser),
            pmNameField,
            calc('Percentage completion', isEdit ? `${project.identity.completion_pct}%` : CALCULATED),
          ]),
          el('div', { class: 'form-grid' }, [
            field('Executive sponsor', sponsor),
            field('Delivery organisation', deliveryOrg),
          ]),
          field('Brief description', description),
          field('Status update / comments', statusUpd),
        ]),
        card('RAG status', [
          el('p', { class: 'text-sm text-muted', text: 'Entered manually — ReportX does not calculate RAG.' }),
          ...['schedule', 'budget', 'issues'].map(k => el('div', { class: 'rag-row' }, [
            field(`${k[0].toUpperCase()}${k.slice(1)} RAG`, rag[k]),
            field(`${k[0].toUpperCase()}${k.slice(1)} commentary`, ragNote[k]),
          ])),
        ]),
        card('Executive summary', [
          el('p', { class: 'text-sm text-muted', text: 'The narrative summary of status on the report — one point per line.' }),
          el('div', { class: 'field' }, [execSummary]),
        ]),
      ]),
      el('div', {}, [
        card('Schedule', [el('div', { class: 'form-grid' }, [
          field('Start date', sched.start_date),
          field('Original baseline', sched.original_baseline),
          field('TSC approved (planned) date', sched.tsc_approved_date),
          field('Planned delivery', sched.planned_delivery),
          field('Forecast delivery', sched.forecast_delivery),
          field('Actual delivery', sched.actual_delivery),
          calc('Schedule variance', isEdit ? formatVariance(project.schedule.variance_days) : CALCULATED),
        ])]),
        card('Resources and budget', [el('div', { class: 'form-grid' }, [
          field('Junior days', res.junior_days),
          field('Intermediate days', res.intermediate_days),
          field('Expert days', res.expert_days),
          field('Other planned costs', res.other_planned_costs),
          field('Actual cost to date', res.actual_cost_to_date),
          calc('Resource cost', isEdit ? formatMoney(project.resources.resource_cost) : CALCULATED),
          calc('Contingency', isEdit ? formatMoney(project.resources.contingency) : CALCULATED),
          calc('Planned budget', isEdit ? formatMoney(project.resources.planned_budget) : CALCULATED),
        ])]),
        card('Planned activities', [
          field('Planned accomplishments', acts.accomplishments),
          field('Planned but not accomplished', acts.not_accomplished),
          field('Planned actions for next period', acts.next_period),
        ]),
      ]),
    ]),
    el('div', { class: 'flex gap-2 form-actions' }, [
      isEdit ? el('a', { class: 'btn btn-ghost', text: 'Cancel', href: `#/project/${project.id}` }) : null,
      el('button', { class: 'btn btn-outline', text: 'Save draft', onclick: () => save(true) }),
      el('button', { class: 'btn btn-primary', text: 'Save project', onclick: () => save(false) }),
    ]),
  ]);
}

function card(title, children) {
  return el('div', { class: 'card stack' }, [
    el('div', { class: 'card-header' }, [el('div', { class: 'card-title', text: title })]),
    ...children,
  ]);
}
function field(label, input) {
  return el('div', { class: 'field' }, [el('label', { text: label }), input]);
}
function input(type, value) {
  const node = el('input', { type });
  if (value != null) node.value = value;
  return node;
}
function textarea(value, placeholder = '') {
  const node = el('textarea', { placeholder });
  if (value) node.value = value;
  return node;
}
