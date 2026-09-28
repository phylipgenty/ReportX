/**
 * Tiny hash router. Routes are declared once; each page is lazily imported.
 * `allowed` hides pages the signed-in user can't use (the server enforces it too).
 */
import { can } from './store.js';

const routes = [
  { pattern: /^#\/?(dashboard)?$/,          file: 'pages/dashboard.js',        exportName: 'DashboardPage' },
  { pattern: /^#\/milestones$/,             file: 'pages/milestone.js',        exportName: 'MilestonesPage' },
  { pattern: /^#\/project\/new$/,           file: 'pages/project-new.js',      exportName: 'ProjectNewPage',
    allowed: () => can('project.create') },
  { pattern: /^#\/project\/([^/]+)\/edit$/, file: 'pages/project-new.js',      exportName: 'ProjectEditPage',
    params: (m) => ({ id: decodeURIComponent(m[1]) }) },
  { pattern: /^#\/project\/([^/]+)$/,       file: 'pages/project-detail.js',   exportName: 'ProjectDetailPage',
    params: (m) => ({ id: decodeURIComponent(m[1]) }) },
  { pattern: /^#\/import$/,                 file: 'pages/import.js',           exportName: 'ImportPage',
    allowed: () => can('import') },
  { pattern: /^#\/cost-assumptions$/,       file: 'pages/cost-assumptions.js', exportName: 'CostAssumptionsPage' },
  { pattern: /^#\/admin(?:\/(\w+))?$/,      file: 'pages/admin.js',            exportName: 'AdminPage',
    params: (m) => ({ tab: m[1] }), allowed: () => can('users') || can('reference_data') || can('settings') },
];

function message(topbar, view, text) {
  topbar.innerHTML = '';
  view.innerHTML = '';
  view.appendChild(Object.assign(document.createElement('div'), { className: 'empty', textContent: text }));
}

export async function handleRoute({ topbar, view }) {
  const hash = location.hash || '#/dashboard';

  for (const r of routes) {
    const m = hash.match(r.pattern);
    if (!m) continue;
    if (r.allowed && !r.allowed()) return message(topbar, view, "You don't have access to this page.");
    const mod = await import('./' + r.file);
    return mod[r.exportName]({ topbar, view, params: r.params ? r.params(m) : {} });
  }
  message(topbar, view, 'Page not found.');
}

export function activeNavId() {
  const h = location.hash || '#/dashboard';
  if (h.startsWith('#/milestones'))       return 'milestones';
  if (h === '#/project/new')              return 'project-new';
  if (h.startsWith('#/project/'))         return 'project-detail';
  if (h.startsWith('#/import'))           return 'import';
  if (h.startsWith('#/cost-assumptions')) return 'cost-assumptions';
  if (h.startsWith('#/admin'))            return 'admin';
  return 'dashboard';
}
