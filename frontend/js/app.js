import { handleRoute, activeNavId } from './router.js';
import { renderSidebar } from './components/sidebar.js';
import { getState, subscribe, ensureBootstrap, setUser } from './store.js';
import { api, UNAUTHORIZED_EVENT } from './api.js';
import { el, mount } from './utils/dom.js';
import { setupScreen, loginScreen, changePasswordScreen } from './components/auth-screens.js';
import { initNavDrawer, closeNav } from './components/nav-drawer.js';

const appEl     = document.getElementById('app');
const authEl    = document.getElementById('auth-root');
const sidebarEl = document.getElementById('sidebar');
const topbarEl  = document.getElementById('topbar');
const viewEl    = document.getElementById('view');

let started = false;

/** Resolves once someone is signed in with a usable (non-temporary) password. */
async function signIn(message = '') {
  appEl.hidden = true;
  authEl.hidden = false;
  let status;
  try {
    status = await api.auth.status();
  } catch (e) {
    mount(authEl, el('div', { class: 'empty', text: `Could not reach the ReportX API: ${e.message}` }));
    throw e;
  }
  let user = status.user;
  if (status.setup_required) user = await setupScreen(authEl, status);
  else if (!user) user = await loginScreen(authEl, status, message);
  if (user.must_change_password) user = await changePasswordScreen(authEl, status, { forced: true });

  setUser(user);
  authEl.hidden = true;
  mount(authEl, []);
  appEl.hidden = false;
}

async function boot() {
  await signIn();
  await ensureBootstrap(true);
  document.title = `${getState().bootstrap.app.name} — Project Reporting`;

  if (!started) {
    started = true;
    initNavDrawer();
    let entityId = getState().ui.activeEntityId;
    subscribe(() => {
      renderSidebar(sidebarEl, { active: activeNavId(), onSignOut: signOut });
      // Entity tabs filter the current view, so re-render it when the filter changes.
      if (getState().ui.activeEntityId !== entityId) {
        entityId = getState().ui.activeEntityId;
        route();
      }
    });
    window.addEventListener('hashchange', route);
    window.addEventListener(UNAUTHORIZED_EVENT, () => restart('Your session has ended. Please sign in again.'));
  }
  route();
}

async function restart(message) {
  if (authEl.hidden === false) return;   // already on a sign-in screen
  setUser(null);
  closeNav();
  // Don't let the previous user's page linger behind the next sign-in.
  mount(topbarEl, []);
  mount(viewEl, []);
  mount(sidebarEl, []);
  await signIn(message);
  await ensureBootstrap(true);
  route();
}

async function signOut() {
  try { await api.auth.logout(); } catch {}
  restart('You have signed out.');
}

async function route() {
  if (!getState().user) return;
  renderSidebar(sidebarEl, { active: activeNavId(), onSignOut: signOut });
  await handleRoute({ topbar: topbarEl, view: viewEl });
}

boot();
