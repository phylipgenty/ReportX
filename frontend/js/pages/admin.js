import { el, mount, toast, openModal, confirmDialog } from '../utils/dom.js';
import { api } from '../api.js';
import { can, ensureBootstrap, getState } from '../store.js';
import { renderTopbar } from '../components/topbar.js';
import { formatDateTime } from '../utils/dates.js';

/** README §17 / §43–§44 Admin area: users, reference data, settings. */
const TABS = [
  { id: 'users',     label: 'Users',          perm: 'users',          render: UsersTab },
  { id: 'reference', label: 'Reference data', perm: 'reference_data', render: ReferenceTab },
  { id: 'settings',  label: 'Settings',       perm: 'settings',       render: SettingsTab },
];

const LOOKUP_NAMES = {
  project_status: 'Project status', milestone_status: 'Milestone status', rag: 'RAG status',
  issue_priority: 'Priority (issues & risks)', issue_impact_area: 'Issue impact areas', risk_status: 'Risk status',
  probability: 'Risk probability levels', impact: 'Risk impact levels', date_placeholder: 'Date placeholders (TBD / N/A)',
};
const FLAG_NAMES = {
  is_default: 'Default for new records', counts_complete: 'Counts towards completion %',
  is_complete: 'Means the project is completed', is_not_started: 'Means not started',
  is_delayed: 'Means delayed (at-risk KPI)', needs_attention: 'Needs attention (KPI)',
};
// Which flags make sense for which list.
const KIND_FLAGS = {
  project_status: ['is_default', 'is_complete', 'is_not_started'],
  milestone_status: ['is_default', 'counts_complete', 'is_delayed'],
  rag: ['is_default', 'needs_attention'],
  issue_priority: ['is_default'], risk_status: ['is_default'], probability: ['is_default'], impact: ['is_default'],
};

export async function AdminPage({ topbar, view, params }) {
  const tabs = TABS.filter(t => can(t.perm));
  const active = tabs.find(t => t.id === params.tab) || tabs[0];
  renderTopbar(topbar, { eyebrow: 'Administration', title: 'Admin', actions: [] });

  const body = el('div', {});
  mount(view, el('div', {}, [
    el('div', { class: 'tabs' }, tabs.map(t =>
      el('a', { class: `tab ${t === active ? 'active' : ''}`, href: `#/admin/${t.id}`, text: t.label }))),
    body,
  ]));
  const refresh = () => active.render(body, refresh);
  refresh();
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------
async function UsersTab(host, refresh) {
  mount(host, el('div', { class: 'loader', text: 'Loading users…' }));
  let data;
  try { data = await api.admin.users(); } catch (e) { mount(host, el('div', { class: 'empty', text: e.message })); return; }
  const { users, roles } = data;
  const me = getState().user;
  const roleLabel = (k) => roles.find(r => r.key === k)?.label || k;

  const rows = users.map(u => {
    const roleSel = el('select', {}, roles.map(r => el('option', { value: r.key, text: r.label, selected: r.key === u.role ? 'selected' : null })));
    roleSel.addEventListener('change', async () => {
      try { await api.admin.updateUser(u.id, { role: roleSel.value }); toast(`${u.name} is now ${roleLabel(roleSel.value)}`, 'success'); refresh(); }
      catch (e) { toast(e.message, 'error'); roleSel.value = u.role; }
    });
    return el('tr', { class: u.active ? '' : 'row-inactive' }, [
      el('td', {}, [el('strong', { text: u.name }), u.id === me.id ? el('span', { class: 'text-xs text-muted', text: ' (you)' }) : null]),
      el('td', { text: u.email }),
      el('td', {}, [roleSel]),
      el('td', {}, [el('span', { class: `badge ${u.active ? 'positive' : 'muted'}`, text: u.active ? 'Active' : 'Deactivated' }),
        u.must_change_password ? el('div', { class: 'text-xs text-muted', text: 'Temporary password' }) : null]),
      el('td', { text: formatDateTime(u.last_login_at) }),
      el('td', { class: 'row-actions' }, [
        el('button', { class: 'btn btn-ghost btn-sm', text: 'Edit', onclick: () => editUser(u, refresh) }),
        el('button', {
          class: 'btn btn-ghost btn-sm', text: 'Reset password',
          onclick: async () => {
            if (!(await confirmDialog(`Issue a new temporary password for ${u.name}? Their current password stops working.`, { confirmText: 'Reset' }))) return;
            try { showTempPassword(u.name, (await api.admin.resetPassword(u.id)).temporary_password); refresh(); }
            catch (e) { toast(e.message, 'error'); }
          },
        }),
        el('button', {
          class: 'btn btn-ghost btn-sm', text: u.active ? 'Deactivate' : 'Reactivate',
          onclick: async () => {
            if (u.active && !(await confirmDialog(`Deactivate ${u.name}? They are signed out and can no longer sign in.`, { confirmText: 'Deactivate' }))) return;
            try { await api.admin.updateUser(u.id, { active: !u.active }); refresh(); }
            catch (e) { toast(e.message, 'error'); }
          },
        }),
      ]),
    ]);
  });

  const matrix = el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
    el('thead', {}, [el('tr', {}, [el('th', { text: 'Role' }), el('th', { text: 'Can' })])]),
    el('tbody', {}, roles.map(r => el('tr', {}, [
      el('td', { text: r.label }),
      el('td', { class: 'wrap', text: ['View everything', ...r.permissions.map(permLabel)].join(' · ') }),
    ]))),
  ])]);

  mount(host, el('div', {}, [
    el('div', { class: 'card stack' }, [
      el('div', { class: 'card-header' }, [
        el('div', {}, [el('div', { class: 'card-title', text: 'Users' }),
          el('div', { class: 'card-subtitle', text: 'Everyone signs in with their own account. New users get a temporary password.' })]),
        el('button', { class: 'btn btn-primary btn-sm', text: '+ Add user', onclick: () => addUser(roles, refresh) }),
      ]),
      el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
        el('thead', {}, [el('tr', {}, ['Name', 'Email', 'Role', 'Status', 'Last sign-in', ''].map(t => el('th', { text: t })))]),
        el('tbody', {}, rows),
      ])]),
    ]),
    el('div', { class: 'card stack' }, [
      el('div', { class: 'card-header' }, [el('div', { class: 'card-title', text: 'What each role can do' })]),
      matrix,
    ]),
  ]));
}

function permLabel(p) {
  return ({
    'report.export': 'Export reports', 'project.create': 'Create projects',
    'project.edit_own': 'Edit own projects', 'project.edit_all': 'Edit all projects',
    import: 'Import from Excel', costs: 'Change cost rates', users: 'Manage users',
    reference_data: 'Edit reference data', settings: 'Change settings',
  })[p] || p;
}

function addUser(roles, refresh) {
  const name = el('input', { type: 'text' });
  const email = el('input', { type: 'email' });
  const role = el('select', {}, roles.map(r => el('option', { value: r.key, text: r.label })));
  const save = el('button', { class: 'btn btn-primary', text: 'Create user' });
  const m = openModal({
    title: 'Add user',
    body: el('div', {}, [field('Name', name), field('Work email', email), field('Role', role)]),
    footer: [save],
  });
  save.addEventListener('click', async () => {
    save.disabled = true;
    try {
      const r = await api.admin.createUser({ name: name.value, email: email.value, role: role.value });
      m.close();
      showTempPassword(r.user.name, r.temporary_password);
      refresh();
    } catch (e) { toast(e.message, 'error'); save.disabled = false; }
  });
}

function editUser(u, refresh) {
  const name = el('input', { type: 'text', value: u.name });
  const email = el('input', { type: 'email', value: u.email });
  const save = el('button', { class: 'btn btn-primary', text: 'Save' });
  const m = openModal({ title: `Edit ${u.name}`, body: el('div', {}, [field('Name', name), field('Work email', email)]), footer: [save] });
  save.addEventListener('click', async () => {
    save.disabled = true;
    try { await api.admin.updateUser(u.id, { name: name.value, email: email.value }); m.close(); toast('User updated', 'success'); refresh(); }
    catch (e) { toast(e.message, 'error'); save.disabled = false; }
  });
}

function showTempPassword(name, password) {
  const code = el('code', { class: 'temp-password', text: password });
  const copy = el('button', {
    class: 'btn btn-outline', text: 'Copy',
    onclick: async () => { try { await navigator.clipboard.writeText(password); toast('Copied', 'success'); } catch { toast('Copy failed — select and copy manually', 'error'); } },
  });
  openModal({
    title: 'Temporary password',
    body: el('div', {}, [
      el('p', { text: `Give this temporary password to ${name}. It is shown only once; they will be asked to choose their own password when they sign in.` }),
      code,
    ]),
    footer: [copy],
  });
}

// ---------------------------------------------------------------------------
// Reference data
// ---------------------------------------------------------------------------
async function ReferenceTab(host, refresh) {
  mount(host, el('div', { class: 'loader', text: 'Loading reference data…' }));
  let ref;
  try { ref = await api.admin.reference(); } catch (e) { mount(host, el('div', { class: 'empty', text: e.message })); return; }

  const done = async (msg) => { toast(msg, 'success'); await ensureBootstrap(true); refresh(); };
  const fail = (e) => toast(e.message, 'error');

  // Entities & divisions
  const refCard = (kind, title) => el('div', { class: 'card stack' }, [
    el('div', { class: 'card-header' }, [
      el('div', { class: 'card-title', text: title }),
      el('button', { class: 'btn btn-outline btn-sm', text: '+ Add', onclick: () => refForm(kind, null) }),
    ]),
    el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
      el('thead', {}, [el('tr', {}, ['Code', 'Name', 'Projects', ''].map(t => el('th', { text: t })))]),
      el('tbody', {}, ref[kind].map(r => el('tr', {}, [
        el('td', {}, [el('strong', { text: r.code })]), el('td', { text: r.name }), el('td', { text: String(r.in_use) }),
        el('td', { class: 'row-actions' }, [
          el('button', { class: 'btn btn-ghost btn-sm', text: 'Edit', onclick: () => refForm(kind, r) }),
          r.in_use ? null : el('button', {
            class: 'btn btn-ghost btn-sm', text: 'Delete',
            onclick: async () => {
              if (!(await confirmDialog(`Delete ${r.code}?`, { confirmText: 'Delete' }))) return;
              try { await api.admin.deleteRef(kind, r.id); done('Deleted'); } catch (e) { fail(e); }
            },
          }),
        ]),
      ]))),
    ])]),
  ]);

  function refForm(kind, r) {
    const code = el('input', { type: 'text', value: r?.code || '' });
    const name = el('input', { type: 'text', value: r?.name || '' });
    const save = el('button', { class: 'btn btn-primary', text: 'Save' });
    const m = openModal({ title: r ? `Edit ${r.code}` : 'Add', body: el('div', {}, [field('Code', code), field('Name', name)]), footer: [save] });
    save.addEventListener('click', async () => {
      try {
        const payload = { code: code.value, name: name.value };
        if (r) await api.admin.editRef(kind, r.id, payload); else await api.admin.addRef(kind, payload);
        m.close(); done('Saved');
      } catch (e) { fail(e); }
    });
  }

  // Milestones (labels only — the nine-stage lifecycle is fixed, README §52)
  const msCard = el('div', { class: 'card stack' }, [
    el('div', { class: 'card-header' }, [el('div', {}, [
      el('div', { class: 'card-title', text: 'Milestone lifecycle' }),
      el('div', { class: 'card-subtitle', text: 'The nine stages are fixed; their names can be changed.' }),
    ])]),
    el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
      el('thead', {}, [el('tr', {}, ['#', 'Full name', 'Short name', ''].map(t => el('th', { text: t })))]),
      el('tbody', {}, ref.milestone_definitions.map(d => {
        const label = el('input', { type: 'text', value: d.label });
        const short = el('input', { type: 'text', value: d.short_label });
        return el('tr', {}, [
          el('td', { text: String(d.order) }), el('td', {}, [label]), el('td', {}, [short]),
          el('td', { class: 'row-actions' }, [el('button', {
            class: 'btn btn-ghost btn-sm', text: 'Save',
            onclick: async () => { try { await api.admin.editMilestone(d.key, { label: label.value, short_label: short.value }); done('Milestone renamed'); } catch (e) { fail(e); } },
          })]),
        ]);
      })),
    ])]),
  ]);

  // Lookup lists
  const kinds = Object.keys(ref.lookups);
  const kindSel = el('select', {}, kinds.map(k => el('option', { value: k, text: LOOKUP_NAMES[k] || k })));
  const lookupBody = el('div', {});
  const renderLookup = () => {
    const kind = kindSel.value;
    mount(lookupBody, el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
      el('thead', {}, [el('tr', {}, ['Value', 'Label', 'Style', 'Rules', 'Used by', ''].map(t => el('th', { text: t })))]),
      el('tbody', {}, ref.lookups[kind].map(o => el('tr', {}, [
        el('td', { text: o.value }),
        el('td', {}, [el('span', { class: `badge ${o.tone}`, text: o.label })]),
        el('td', { text: o.tone }),
        el('td', { class: 'wrap text-sm' }, [
          Object.keys(FLAG_NAMES).filter(f => o[f]).map(f => FLAG_NAMES[f]).join(', ') || '—',
          o.aliases?.length ? el('div', { class: 'text-xs text-muted', text: `Also matches: ${o.aliases.join(', ')}` }) : null,
        ]),
        el('td', { text: String(o.in_use) }),
        el('td', { class: 'row-actions' }, [
          el('button', { class: 'btn btn-ghost btn-sm', text: 'Edit', onclick: () => lookupForm(kind, o) }),
          o.in_use ? null : el('button', {
            class: 'btn btn-ghost btn-sm', text: 'Delete',
            onclick: async () => {
              if (!(await confirmDialog(`Delete “${o.label}”?`, { confirmText: 'Delete' }))) return;
              try { await api.admin.deleteLookup(kind, o.value); done('Deleted'); } catch (e) { fail(e); }
            },
          }),
        ]),
      ]))),
    ])]));
  };
  kindSel.addEventListener('change', renderLookup);
  renderLookup();

  function lookupForm(kind, o) {
    const value = el('input', { type: 'text', value: o?.value || '', disabled: o ? 'disabled' : null });
    const label = el('input', { type: 'text', value: o?.label || '' });
    const tone = el('select', {}, ref.tones.map(t => el('option', { value: t, text: t, selected: t === (o?.tone || 'neutral') ? 'selected' : null })));
    const preview = el('span', { class: `badge ${o?.tone || 'neutral'}`, text: o?.label || 'Preview' });
    const sync = () => { preview.className = `badge ${tone.value}`; preview.textContent = label.value || 'Preview'; };
    tone.addEventListener('change', sync); label.addEventListener('input', sync);
    const flags = (KIND_FLAGS[kind] || []).map(f => {
      const cb = el('input', { type: 'checkbox' }); cb.checked = !!o?.[f];
      return { f, cb, node: el('label', { class: 'check' }, [cb, ` ${FLAG_NAMES[f]}`]) };
    });
    const extraKey = kind === 'probability' ? 'range' : ['impact', 'issue_priority'].includes(kind) ? 'description' : null;
    const extra = extraKey ? el('input', { type: 'text', value: o?.[extraKey] || '' }) : null;
    const aliases = el('input', { type: 'text', value: (o?.aliases || []).join(', '), placeholder: 'e.g. Completed, Complete' });
    const save = el('button', { class: 'btn btn-primary', text: 'Save' });
    const m = openModal({
      title: o ? `Edit “${o.label}”` : `Add to ${LOOKUP_NAMES[kind] || kind}`,
      body: el('div', {}, [
        el('div', { class: 'form-grid' }, [field('Stored value', value), field('Label shown to users', label), field('Style', tone), field('Preview', preview)]),
        extra ? field(extraKey === 'range' ? 'Probability range' : kind === 'issue_priority' ? 'Report legend text' : 'Description', extra) : null,
        flags.length ? field('Rules', el('div', { class: 'checks-col' }, flags.map(x => x.node))) : null,
        field('Other spellings matched on Excel import (comma-separated)', aliases),
        o ? el('p', { class: 'text-xs text-muted', text: 'Stored values can’t be renamed because existing records use them.' }) : null,
      ]),
      footer: [save],
    });
    save.addEventListener('click', async () => {
      const payload = {
        value: value.value, label: label.value, tone: tone.value,
        flags: Object.fromEntries(flags.map(x => [x.f, x.cb.checked])),
        aliases: aliases.value.split(',').map(a => a.trim()).filter(Boolean),
        ...(extraKey ? { [extraKey]: extra.value } : {}),
      };
      try {
        if (o) await api.admin.editLookup(kind, o.value, payload); else await api.admin.addLookup(kind, payload);
        m.close(); done('Saved');
      } catch (e) { fail(e); }
    });
  }

  const lookupCard = el('div', { class: 'card stack' }, [
    el('div', { class: 'card-header' }, [
      el('div', {}, [el('div', { class: 'card-title', text: 'Lists and statuses' }),
        el('div', { class: 'card-subtitle', text: 'Options used in dropdowns, badges, KPIs and calculations.' })]),
      el('div', { class: 'flex gap-2' }, [kindSel, el('button', { class: 'btn btn-outline btn-sm', text: '+ Add option', onclick: () => lookupForm(kindSel.value, null) })]),
    ]),
    lookupBody,
  ]);

  // Import column names
  const importCard = el('div', { class: 'card stack' }, [
    el('div', { class: 'card-header' }, [el('div', {}, [
      el('div', { class: 'card-title', text: 'Excel import columns' }),
      el('div', { class: 'card-subtitle', text: 'Column headings recognised automatically when importing (comma-separated).' }),
    ])]),
    el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
      el('thead', {}, [el('tr', {}, ['Field', 'Recognised headings', ''].map(t => el('th', { text: t })))]),
      el('tbody', {}, ref.import_fields.map(f => {
        const aliases = el('input', { type: 'text', value: f.aliases.join(', ') });
        return el('tr', {}, [
          el('td', { text: f.label }), el('td', {}, [aliases]),
          el('td', { class: 'row-actions' }, [el('button', {
            class: 'btn btn-ghost btn-sm', text: 'Save',
            onclick: async () => { try { await api.admin.editImportField(f.key, { label: f.label, aliases: aliases.value.split(',') }); done('Import columns saved'); } catch (e) { fail(e); } },
          })]),
        ]);
      })),
    ])]),
  ]);

  mount(host, el('div', {}, [
    el('div', { class: 'dash-grid' }, [refCard('entities', 'Entities / subsidiaries'), refCard('divisions', 'Divisions')]),
    lookupCard, msCard, importCard,
  ]));
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
const SETTING_FIELDS = [
  ['app_name', 'Application name', 'text'],
  ['organisation_name', 'Organisation name (shown on reports)', 'text'],
  ['currency', 'Currency code', 'text'],
  ['currency_symbol', 'Currency symbol', 'text'],
  ['project_id_prefix', 'Project ID prefix', 'text'],
  ['project_id_width', 'Project ID digits', 'number'],
  ['upload_extensions', 'Accepted attachment types', 'text'],
  ['upload_max_mb', 'Maximum attachment size (MB)', 'number'],
  ['report_classification', 'Report classification label (e.g. PUBLIC)', 'text'],
];

async function SettingsTab(host, refresh) {
  mount(host, el('div', { class: 'loader', text: 'Loading settings…' }));
  let values;
  try { values = await api.admin.settings(); } catch (e) { mount(host, el('div', { class: 'empty', text: e.message })); return; }

  const inputs = Object.fromEntries(SETTING_FIELDS.map(([k, , type]) => [k, el('input', { type, value: values[k] ?? '' })]));
  const example = el('div', { class: 'text-sm text-muted' });
  const syncExample = () => {
    const w = Math.max(1, Number(inputs.project_id_width.value) || 1);
    example.textContent = `Next project IDs look like ${inputs.project_id_prefix.value || '?'}-${'1'.padStart(w, '0')}`;
  };
  inputs.project_id_prefix.addEventListener('input', syncExample);
  inputs.project_id_width.addEventListener('input', syncExample);
  syncExample();

  const save = el('button', { class: 'btn btn-primary', text: 'Save settings' });
  save.addEventListener('click', async () => {
    save.disabled = true;
    try {
      const payload = Object.fromEntries(SETTING_FIELDS.map(([k, , type]) => [k, type === 'number' ? Number(inputs[k].value) : inputs[k].value]));
      await api.admin.saveSettings(payload);
      await ensureBootstrap(true);
      toast('Settings saved', 'success');
      refresh();
    } catch (e) { toast(e.message, 'error'); save.disabled = false; }
  });

  mount(host, el('div', { class: 'card stack' }, [
    el('div', { class: 'card-header' }, [el('div', {}, [
      el('div', { class: 'card-title', text: 'Settings' }),
      el('div', { class: 'card-subtitle', text: 'Changes apply immediately. Existing project IDs never change.' }),
    ])]),
    el('div', { class: 'form-grid' }, SETTING_FIELDS.map(([k, label]) => field(label, inputs[k]))),
    example,
    el('div', { class: 'flex gap-2 form-actions' }, [save]),
  ]));
}

function field(label, node) {
  return el('div', { class: 'field' }, [el('label', { text: label }), node]);
}
