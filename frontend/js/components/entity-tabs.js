import { el } from '../utils/dom.js';
import { getState, setState } from '../store.js';

/**
 * Renders "All entities" + one tab per entity from bootstrap.
 * Purely data-driven — no hard-coded entity codes.
 */
export function renderEntityTabs(container) {
  const { bootstrap, ui } = getState();
  if (!bootstrap) return;

  container.innerHTML = '';
  container.className = 'tabs';

  container.appendChild(
    el('button', {
      class: `tab ${ui.activeEntityId === 'all' ? 'active' : ''}`,
      text: 'All entities',
      onclick: () => setState({ ui: { activeEntityId: 'all' } }),
    })
  );

  for (const e of bootstrap.entities) {
    container.appendChild(
      el('button', {
        class: `tab ${ui.activeEntityId === e.id ? 'active' : ''}`,
        text: e.code,
        title: e.name,
        onclick: () => setState({ ui: { activeEntityId: e.id } }),
      })
    );
  }
}