import { el, mount } from '../utils/dom.js';
import { renderTopbar } from '../components/topbar.js';
import { ImportWizard } from '../components/import-wizard.js';

export function ImportPage({ topbar, view }) {
  renderTopbar(topbar, {
    eyebrow: 'Bring your data in',
    title: 'Import from Excel',
    actions: [
      el('a', { class: 'btn btn-outline', text: 'Back to dashboard', href: '#/dashboard' }),
    ],
  });

  const host = el('div', {});
  mount(view, host);
  ImportWizard(host);
}