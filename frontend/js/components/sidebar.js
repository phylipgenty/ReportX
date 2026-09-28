import { el, svg, toast, openModal } from '../utils/dom.js';
import { getState, can } from '../store.js';
import { api } from '../api.js';
import { formatDate } from '../utils/dates.js';
import { closeNav } from './nav-drawer.js';

const ICONS = {
  dashboard:          'M3 12l9-9 9 9M5 10v10h14V10',
  milestones:         'M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01',
  'project-detail':   'M4 4h16v16H4zM8 8h8M8 12h8M8 16h5',
  'project-new':      'M12 5v14M5 12h14',
  import:             'M12 3v12M7 10l5 5 5-5M5 21h14',
  admin:              'M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z',
};

// README §3 navigation. `show` hides items the signed-in user can't use.
const NAV = [
  { id: 'dashboard',        label: 'Dashboard',          href: '#/dashboard' },
  { id: 'milestones',       label: 'Milestones',         href: '#/milestones' },
  { id: 'project-detail',   label: 'Project detail',     href: null },
  { id: 'project-new',      label: 'Project data entry', href: '#/project/new', show: () => can('project.create') },
  { id: 'import',           label: 'Import data',        href: '#/import',      show: () => can('import') },
  { id: 'cost-assumptions', label: 'Cost assumptions',   href: '#/cost-assumptions' },
  { id: 'admin',            label: 'Admin',              href: '#/admin',
    show: () => can('users') || can('reference_data') || can('settings') },
];

export function renderSidebar(container, { active, onSignOut }) {
  const { bootstrap, user } = getState();
  container.innerHTML = '';
  container.appendChild(
    el('div', { class: 'sidebar-head' }, [
      el('div', { class: 'brand' }, [
        bootstrap?.app?.name || '',
        el('small', { text: bootstrap?.app?.organisation || '' }),
      ]),
      // Drawer close button — shown only on narrow screens.
      el('button', { class: 'drawer-close', type: 'button', 'aria-label': 'Close menu', onclick: closeNav },
        [svg('M6 6l12 12M18 6L6 18', 20)]),
    ])
  );

  const nav = el('nav', { class: 'nav' });
  for (const item of NAV) {
    if (item.show && !item.show()) continue;
    if (!item.href && item.id !== active) continue;   // only shown while viewing a project
    nav.appendChild(
      el('a', { class: `nav-item ${item.id === active ? 'active' : ''}`, href: item.href || location.hash, onclick: closeNav }, [
        item.id === 'cost-assumptions'
          // Currency symbol from settings (e.g. ₦) rather than a fixed glyph.
          ? el('span', { class: 'icon icon-text', text: bootstrap?.app?.currency_symbol || '' })
          : el('span', { class: 'icon' }, [svg(ICONS[item.id], 18)]),
        el('span', { text: item.label }),
      ])
    );
  }
  container.appendChild(nav);
  container.appendChild(el('div', { class: 'spacer' }));

  const last = bootstrap?.last_import;
  if (last) {
    container.appendChild(
      el('div', { class: 'last-import' }, [
        el('strong', { text: 'Last import' }),
        el('div', { text: last.filename }),
        el('div', { text: `${formatDate(last.date)} by ${last.by}` }),
      ])
    );
  }

  if (user) {
    container.appendChild(el('div', { class: 'user-chip' }, [
      el('div', { class: 'user-name', text: user.name }),
      el('div', { class: 'user-role', text: user.role_label }),
      el('div', { class: 'user-actions' }, [
        el('button', { class: 'link-btn', text: 'Change password', onclick: openChangePassword }),
        el('button', { class: 'link-btn', text: 'Sign out', onclick: onSignOut }),
      ]),
    ]));
  }
}

function openChangePassword() {
  const field = (label, input) => el('div', { class: 'field' }, [el('label', { text: label }), input]);
  const current = el('input', { type: 'password', autocomplete: 'current-password' });
  const pw = el('input', { type: 'password', autocomplete: 'new-password' });
  const pw2 = el('input', { type: 'password', autocomplete: 'new-password' });
  const save = el('button', { class: 'btn btn-primary', text: 'Save password' });
  const m = openModal({
    title: 'Change password',
    body: el('div', {}, [field('Current password', current), field('New password (at least 10 characters)', pw), field('Confirm new password', pw2)]),
    footer: [save],
  });
  save.addEventListener('click', async () => {
    if (pw.value !== pw2.value) { toast('Passwords do not match', 'error'); return; }
    save.disabled = true;
    try {
      await api.auth.changePassword(current.value, pw.value);
      toast('Password changed', 'success');
      m.close();
    } catch (e) { toast(e.message, 'error'); save.disabled = false; }
  });
}
