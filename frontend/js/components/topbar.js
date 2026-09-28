import { el, svg } from '../utils/dom.js';
import { openNav } from './nav-drawer.js';

export function renderTopbar(container, { eyebrow, title, actions = [] }) {
  container.innerHTML = '';
  // Shown only on narrow screens, where the sidebar becomes a drawer.
  container.appendChild(
    el('button', {
      class: 'menu-btn', type: 'button', 'aria-label': 'Open menu', 'aria-controls': 'sidebar',
      onclick: openNav,
    }, [svg('M4 6h16M4 12h16M4 18h16', 22)])
  );
  container.appendChild(
    el('div', { class: 'topbar-title' }, [
      eyebrow ? el('div', { class: 'eyebrow', text: eyebrow }) : null,
      el('h1', { text: title || '' }),
    ])
  );
  const right = el('div', { class: 'actions' });
  for (const a of actions) if (a) right.appendChild(a);
  container.appendChild(right);
}
