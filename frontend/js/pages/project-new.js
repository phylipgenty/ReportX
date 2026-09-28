import { el, mount } from '../utils/dom.js';
import { api } from '../api.js';
import { ensureBootstrap, canEditProject } from '../store.js';
import { renderTopbar } from '../components/topbar.js';
import { ProjectForm } from '../components/project-form.js';

export async function ProjectNewPage({ topbar, view }) {
  renderTopbar(topbar, {
    eyebrow: 'Project data entry',
    title: 'New project',
    actions: [el('a', { class: 'btn btn-outline', text: 'Back to dashboard', href: '#/dashboard' })],
  });
  mount(view, el('div', { class: 'loader', text: 'Loading…' }));
  await ensureBootstrap();
  const users = await api.users.directory().catch(() => []);
  mount(view, ProjectForm({ project: null, users, onSaved: (saved) => { location.hash = `#/project/${saved.id}`; } }));
}

export async function ProjectEditPage({ topbar, view, params }) {
  renderTopbar(topbar, { eyebrow: 'Project data entry', title: 'Loading…', actions: [] });
  mount(view, el('div', { class: 'loader', text: 'Loading…' }));
  try {
    await ensureBootstrap();
    const [project, users] = await Promise.all([api.projects.get(params.id), api.users.directory().catch(() => [])]);
    if (!canEditProject(project)) {
      mount(view, el('div', { class: 'empty', text: "Only this project's manager, PMO or Admin can edit it." }));
      return;
    }
    renderTopbar(topbar, {
      eyebrow: `Edit · ${project.id}`,
      title: project.identity.name,
      actions: [el('a', { class: 'btn btn-outline', text: 'Back to project', href: `#/project/${project.id}` })],
    });
    mount(view, ProjectForm({ project, users, onSaved: () => { location.hash = `#/project/${project.id}`; } }));
  } catch (e) {
    mount(view, el('div', { class: 'empty', text: `Failed: ${e.message}` }));
  }
}
