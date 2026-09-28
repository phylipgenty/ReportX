/**
 * On narrow screens the sidebar is an off-canvas drawer. It opens from the
 * top bar's menu button and closes on navigation, the backdrop, the close
 * button or Escape. On wide screens none of this has any visible effect.
 */
const OPEN = 'nav-open';
let lastFocus = null;

export function openNav() {
  lastFocus = document.activeElement;
  document.body.classList.add(OPEN);
  document.getElementById('sidebar')?.querySelector('a, button')?.focus();
}

export function closeNav() {
  if (!document.body.classList.contains(OPEN)) return;
  document.body.classList.remove(OPEN);
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
}

export function initNavDrawer() {
  document.getElementById('nav-backdrop')?.addEventListener('click', closeNav);
  window.addEventListener('hashchange', () => {
    closeNav();
    // Dialogs belong to the page that opened them (e.g. the browser Back button).
    const modals = document.getElementById('modal-root');
    if (modals) modals.innerHTML = '';
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeNav(); });
  // Leaving the narrow layout (rotating a tablet, resizing) never leaves the page locked.
  window.matchMedia('(min-width: 901px)').addEventListener('change', (e) => { if (e.matches) closeNav(); });
}
