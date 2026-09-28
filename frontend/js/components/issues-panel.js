import { el, openModal, toast, confirmDialog } from '../utils/dom.js';
import { api } from '../api.js';
import { selectMilestoneDefs } from '../store.js';
import { badge, options, lookupSelect, milestoneLabel } from '../utils/lookups.js';

/** README §18: Priority · Issue description · Impact summary · Action steps. */
export function IssuesPanel(project, reload, editable) {
  const add = !editable ? null : el('button', { class: 'btn btn-outline btn-sm', text: '+ Add issue', onclick: () => openIssueForm(project, null, reload) });

  const body = project.issues.length
    ? el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
        el('thead', {}, [el('tr', {}, ['Priority', 'Issue', 'Impact', 'Action steps', 'Milestone', ''].map(t => el('th', { text: t })))]),
        el('tbody', {}, project.issues.map(i => el('tr', {}, [
          el('td', {}, [badge('issue_priority', i.priority)]),
          el('td', { class: 'wrap', text: i.description }),
          el('td', { class: 'wrap' }, [
            i.impact_summary,
            i.impact_areas.length ? el('div', { class: 'text-xs text-muted', text: i.impact_areas.join(', ') }) : null,
          ]),
          el('td', { class: 'wrap', text: i.action_steps }),
          el('td', { text: i.milestone_key ? milestoneLabel(i.milestone_key) : '—' }),
          el('td', { class: 'row-actions' }, !editable ? [] : [
            el('button', { class: 'btn btn-ghost btn-sm', text: 'Edit', onclick: () => openIssueForm(project, i, reload) }),
            el('button', {
              class: 'btn btn-ghost btn-sm', text: 'Delete',
              onclick: async () => {
                if (!(await confirmDialog('Delete this issue?', { confirmText: 'Delete' }))) return;
                try { await api.issues.remove(project.id, i.id); toast('Issue deleted', 'success'); reload(); }
                catch (e) { toast(e.message, 'error'); }
              },
            }),
          ]),
        ]))),
      ])])
    : el('div', { class: 'empty', text: 'No issues recorded.' });

  return section('Issues', body, add);
}

function openIssueForm(project, issue, reload) {
  const i = issue || { impact_areas: [] };
  const priority = lookupSelect('issue_priority', i.priority);
  const description = textarea(i.description, 'What is the issue?');
  const impact = textarea(i.impact_summary, 'Impact summary');
  const steps = textarea(i.action_steps, 'Action steps');
  const milestone = el('select', {}, [
    el('option', { value: '', text: '— none —' }),
    ...selectMilestoneDefs().map(d => el('option', { value: d.key, text: d.short_label, selected: d.key === i.milestone_key ? 'selected' : null })),
  ]);
  const areas = options('issue_impact_area').map(o => {
    const cb = el('input', { type: 'checkbox', value: o.value });
    cb.checked = i.impact_areas.includes(o.value);
    return { cb, node: el('label', { class: 'check' }, [cb, ` ${o.label}`]) };
  });

  const save = el('button', { class: 'btn btn-primary', text: issue ? 'Save issue' : 'Add issue' });
  const modal = openModal({
    title: issue ? 'Edit issue' : 'Add issue',
    body: el('div', {}, [
      el('div', { class: 'form-grid' }, [field('Priority', priority), field('Related milestone', milestone)]),
      field('Issue description', description),
      field('Impact summary', impact),
      field('Impact areas', el('div', { class: 'checks' }, areas.map(a => a.node))),
      field('Action steps', steps),
    ]),
    footer: [save],
  });

  save.addEventListener('click', async () => {
    if (!description.value.trim()) { toast('Describe the issue', 'error'); return; }
    const payload = {
      priority: priority.value, description: description.value, impact_summary: impact.value,
      action_steps: steps.value, milestone_key: milestone.value || null,
      impact_areas: areas.filter(a => a.cb.checked).map(a => a.cb.value),
    };
    save.disabled = true;
    try {
      if (issue) await api.issues.update(project.id, issue.id, payload);
      else await api.issues.add(project.id, payload);
      toast('Issue saved', 'success');
      modal.close();
      reload();
    } catch (e) { toast(e.message, 'error'); save.disabled = false; }
  });
}

export function section(title, body, action) {
  return el('div', { class: 'card stack' }, [
    el('div', { class: 'card-header' }, [el('div', { class: 'card-title', text: title }), action || null]),
    body,
  ]);
}
function field(label, node) {
  return el('div', { class: 'field' }, [el('label', { text: label }), node]);
}
function textarea(value, placeholder) {
  const t = el('textarea', { placeholder });
  t.value = value || '';
  return t;
}
