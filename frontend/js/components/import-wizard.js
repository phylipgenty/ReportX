import { el, toast } from '../utils/dom.js';
import { api } from '../api.js';
import { getState, ensureBootstrap } from '../store.js';

const STEPS = ['Upload file', 'Map columns', 'Review changes', 'Sync'];
const ACTION_TONE = { create: 'positive', update: 'info', unchanged: 'muted', skip: 'neutral', error: 'danger' };

/**
 * README §41–§42 import: Upload → Map Columns → Review Changes → Sync.
 * The mapping targets come from /api/bootstrap (import_fields); the server
 * suggests a mapping, dry-runs the changes for review, then applies them.
 */
export function ImportWizard(host) {
  const state = { step: 0, file: null, preview: null, sheet: null, mapping: {}, onExisting: 'update', review: null, result: null };
  render();

  function render() {
    host.innerHTML = '';
    host.appendChild(el('div', { class: 'wizard-steps' }, STEPS.map((label, i) =>
      el('div', { class: `wizard-step ${i === state.step ? 'active' : ''} ${i < state.step ? 'done' : ''}` }, [
        el('div', { class: 'num', text: String(i + 1) }),
        el('div', { text: label }),
      ])
    )));
    host.appendChild([stepUpload, stepMap, stepReview, stepSync][state.step]());
  }

  const sheet = () => state.preview.sheets.find(s => s.name === state.sheet);

  function stepUpload() {
    const input = el('input', { type: 'file', accept: '.xlsx,.xlsm', style: { display: 'none' } });
    const drop = el('div', { class: 'card drop-zone' }, [
      el('h3', { text: 'Drop an Excel file or choose one' }),
      el('p', { class: 'text-muted', text: 'Existing projects are matched on Project ID; other rows create new projects.' }),
      el('button', { class: 'btn btn-primary', text: 'Choose file', onclick: () => input.click() }),
      input,
    ]);
    input.addEventListener('change', () => input.files[0] && load(input.files[0]));
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => {
      e.preventDefault();
      drop.classList.remove('over');
      if (e.dataTransfer.files[0]) load(e.dataTransfer.files[0]);
    });
    return drop;
  }

  async function load(file) {
    try {
      state.preview = await api.imports.preview(file);
      state.file = file;
      selectSheet(state.preview.sheets[0].name);
      state.step = 1;
      render();
    } catch (e) {
      toast(e.message || 'Could not read file', 'error');
    }
  }

  function selectSheet(name) {
    state.sheet = name;
    state.mapping = { ...sheet().suggested_mapping };
  }

  function stepMap() {
    const s = sheet();
    const targets = getState().bootstrap.import_fields;

    const sheetSel = el('select', {
      onchange: (e) => { selectSheet(e.target.value); render(); },
    }, state.preview.sheets.map(x => el('option', { value: x.name, text: `${x.name} (${x.row_count} rows)`, selected: x.name === s.name ? 'selected' : null })));

    const rows = s.headers.map((h, idx) => {
      const sel = el('select', { onchange: (e) => { state.mapping[h] = e.target.value; } }, [
        el('option', { value: '', text: '— skip —' }),
        ...targets.map(t => el('option', { value: t.key, text: t.label, selected: state.mapping[h] === t.key ? 'selected' : null })),
      ]);
      return el('tr', {}, [
        el('td', { text: h }),
        el('td', { class: 'text-muted', text: s.sample_rows[0]?.[idx] ?? '' }),
        el('td', {}, [sel]),
      ]);
    });

    const radio = (value, label) => el('label', { class: 'check' }, [
      el('input', { type: 'radio', name: 'on-existing', value, checked: state.onExisting === value ? 'checked' : null,
        onchange: () => { state.onExisting = value; } }),
      ` ${label}`,
    ]);

    return el('div', {}, [
      el('div', { class: 'card stack' }, [
        el('div', { class: 'form-grid' }, [
          el('div', { class: 'field' }, [el('label', { text: 'Sheet' }), sheetSel]),
          el('div', { class: 'field' }, [el('label', { text: 'When a project already exists' }),
            el('div', { class: 'checks' }, [radio('update', 'Update it (match on Project ID)'), radio('create_only', 'Only add new projects')])]),
        ]),
      ]),
      el('div', { class: 'card', style: { padding: 0, overflow: 'hidden' } }, [
        el('div', { class: 'card-header', style: { padding: '20px' } }, [el('div', {}, [
          el('div', { class: 'card-title', text: 'Match your columns' }),
          el('div', { class: 'card-subtitle', text: `Headings found on row ${s.header_row || 1} · ${s.row_count} data rows. Suggestions are exact name matches — check anything left as skip.` }),
        ])]),
        el('div', { class: 'table-wrap', style: { border: 'none', borderRadius: 0 } }, [el('table', { class: 'data' }, [
          el('thead', {}, [el('tr', {}, ['Excel column', 'Sample', 'Maps to'].map(t => el('th', { text: t })))]),
          el('tbody', {}, rows),
        ])]),
      ]),
      el('div', { class: 'flex gap-2 form-actions' }, [
        el('button', { class: 'btn btn-outline', text: 'Back', onclick: () => { state.step = 0; render(); } }),
        el('button', { class: 'btn btn-primary', text: 'Review changes', onclick: review }),
      ]),
    ]);
  }

  function payload() {
    return { file: state.file, sheet: state.sheet, mapping: state.mapping, onExisting: state.onExisting };
  }

  async function review() {
    const mapped = Object.values(state.mapping);
    if (!mapped.includes('name') && !mapped.includes('project_id')) {
      toast('Map a Project ID or Project name column', 'error');
      return;
    }
    try {
      state.review = (await api.imports.review(payload())).rows;
      state.step = 2;
      render();
    } catch (e) { toast(e.message, 'error'); }
  }

  function stepReview() {
    const rows = state.review;
    const count = (a) => rows.filter(r => r.action === a).length;
    const fmt = (v) => (v == null || v === '' ? '—' : String(v));

    return el('div', {}, [
      el('div', { class: 'kpi-grid' }, ['create', 'update', 'unchanged', 'skip', 'error'].map(a =>
        el('div', { class: 'kpi' }, [el('div', { class: 'kpi-label', text: a }), el('div', { class: 'kpi-value', text: String(count(a)) })]))),
      el('div', { class: 'card', style: { padding: 0, overflow: 'hidden' } }, [
        el('div', { class: 'table-wrap', style: { border: 'none', borderRadius: 0 } }, [el('table', { class: 'data' }, [
          el('thead', {}, [el('tr', {}, ['Row', 'Project', 'Action', 'Changes', 'Notes'].map(t => el('th', { text: t })))]),
          el('tbody', {}, rows.map(r => el('tr', {}, [
            el('td', { text: String(r.row) }),
            el('td', {}, [el('div', { text: r.name || '—' }), el('div', { class: 'text-xs text-muted', text: r.project_id || 'New ID on sync' })]),
            el('td', {}, [el('span', { class: `badge ${ACTION_TONE[r.action] || 'neutral'}`, text: r.action })]),
            el('td', { class: 'wrap' }, r.changes.map(c => el('div', { class: 'text-sm', text: c.from === null && c.field === 'New project' ? 'New project' : `${c.field}: ${fmt(c.from)} → ${fmt(c.to)}` }))),
            el('td', { class: 'wrap' }, [
              ...r.errors.map(x => el('div', { class: 'text-sm text-danger', text: x })),
              ...r.warnings.map(x => el('div', { class: 'text-sm text-muted', text: x })),
            ]),
          ]))),
        ])]),
      ]),
      el('p', { class: 'text-sm text-muted', text: 'Rows with errors are not imported. Updated projects get a saved state first, and milestone changes are kept in history.' }),
      el('div', { class: 'flex gap-2 form-actions' }, [
        el('button', { class: 'btn btn-outline', text: 'Back', onclick: () => { state.step = 1; render(); } }),
        el('button', {
          class: 'btn btn-primary', text: 'Sync now',
          disabled: count('create') + count('update') === 0 ? 'disabled' : null,
          onclick: commit,
        }),
      ]),
    ]);
  }

  async function commit(e) {
    e.target.disabled = true;
    try {
      state.result = await api.imports.commit(payload());
      await ensureBootstrap(true);   // refresh "Last import"
      state.step = 3;
      render();
    } catch (err) {
      toast(err.message || 'Sync failed', 'error');
      e.target.disabled = false;
    }
  }

  function stepSync() {
    const r = state.result;
    return el('div', { class: 'card stack' }, [
      el('h3', { text: 'Import complete' }),
      el('p', { text: `${r.created} created · ${r.updated} updated · ${r.skipped} skipped · ${r.failed} with errors` }),
      el('div', { class: 'flex gap-2' }, [
        el('a', { class: 'btn btn-primary', text: 'Go to dashboard', href: '#/dashboard' }),
        el('button', { class: 'btn btn-outline', text: 'Import another file', onclick: () => ImportWizard(host) }),
      ]),
    ]);
  }
}
