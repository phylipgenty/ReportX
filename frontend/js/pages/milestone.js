import { el, mount } from '../utils/dom.js';
import { api } from '../api.js';
import { getState, filterProjectsByEntity, ensureBootstrap, can } from '../store.js';
import { renderTopbar } from '../components/topbar.js';
import { renderEntityTabs } from '../components/entity-tabs.js';
import { MilestoneTrackerGrid } from '../components/milestone-tracker-grid.js';

export async function MilestonesPage({ topbar, view }) {
  renderTopbar(topbar, {
    eyebrow: 'Delivery lifecycle',
    title: 'Milestone tracker',
    actions: [
      can('import') ? el('a', { class: 'btn btn-outline', text: 'Sync from Excel', href: '#/import' }) : null,
      can('project.create') ? el('a', { class: 'btn btn-primary', text: '+ New project', href: '#/project/new' }) : null,
    ].filter(Boolean),
  });

  mount(view, el('div', { class: 'loader', text: 'Loading milestones…' }));

  try {
    await ensureBootstrap();
    getState().projects = await api.projects.list();
    render();
  } catch (e) {
    mount(view, el('div', { class: 'empty', text: `Failed: ${e.message}` }));
  }

  function render() {
    const filtered = filterProjectsByEntity();
    const tabs = el('div', {});
    renderEntityTabs(tabs);

    const card = el('div', { class: 'card tracker-wrap' }, [
      MilestoneTrackerGrid(filtered),
    ]);

    mount(view, el('div', {}, [tabs, card]));
  }
}