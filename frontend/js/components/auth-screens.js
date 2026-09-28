import { el, mount } from '../utils/dom.js';
import { api } from '../api.js';

/**
 * Full-screen sign-in flows: first-run Admin setup, sign in, and the
 * mandatory password change after an Admin issues a temporary password.
 * Each resolves with the signed-in user.
 */
function screen(root, { app, title, intro, fields, submitText, onSubmit, footer }) {
  const error = el('div', { class: 'auth-error', role: 'alert' });
  const submit = el('button', { class: 'btn btn-primary auth-submit', type: 'submit', text: submitText });
  const form = el('form', { class: 'auth-card' }, [
    el('div', { class: 'auth-brand' }, [app?.app_name || '', el('small', { text: app?.organisation || '' })]),
    el('h1', { text: title }),
    intro ? el('p', { class: 'text-muted text-sm', text: intro }) : null,
    ...fields.map(([label, input]) => el('div', { class: 'field' }, [el('label', { text: label }), input])),
    error,
    submit,
    footer || null,
  ]);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    error.textContent = '';
    submit.disabled = true;
    try { await onSubmit(); }
    catch (err) { error.textContent = err.message || 'Something went wrong'; }
    finally { submit.disabled = false; }
  });
  mount(root, el('div', { class: 'auth-screen' }, [form]));
  fields[0]?.[1]?.focus();
}

const input = (type, attrs = {}) => el('input', { type, required: 'required', ...attrs });

export function setupScreen(root, app) {
  return new Promise((resolve) => {
    const name = input('text', { autocomplete: 'name' });
    const email = input('email', { autocomplete: 'username' });
    const pw = input('password', { autocomplete: 'new-password' });
    const pw2 = input('password', { autocomplete: 'new-password' });
    screen(root, {
      app,
      title: 'Set up ReportX',
      intro: 'Create the first Administrator account. You can add everyone else from the Admin area afterwards.',
      fields: [['Your name', name], ['Work email', email], ['Password (at least 10 characters)', pw], ['Confirm password', pw2]],
      submitText: 'Create Admin account',
      onSubmit: async () => {
        if (pw.value !== pw2.value) throw new Error('Passwords do not match');
        const { user } = await api.auth.setup({ name: name.value, email: email.value, password: pw.value });
        resolve(user);
      },
    });
  });
}

export function loginScreen(root, app, message = '') {
  return new Promise((resolve) => {
    const email = input('email', { autocomplete: 'username' });
    const pw = input('password', { autocomplete: 'current-password' });
    screen(root, {
      app,
      title: 'Sign in',
      intro: message,
      fields: [['Email', email], ['Password', pw]],
      submitText: 'Sign in',
      onSubmit: async () => {
        const { user } = await api.auth.login(email.value, pw.value);
        resolve(user);
      },
      footer: el('p', { class: 'text-xs text-muted auth-foot', text: 'Forgotten your password? Ask a ReportX Admin to reset it.' }),
    });
  });
}

export function changePasswordScreen(root, app, { forced = true } = {}) {
  return new Promise((resolve) => {
    const current = input('password', { autocomplete: 'current-password' });
    const pw = input('password', { autocomplete: 'new-password' });
    const pw2 = input('password', { autocomplete: 'new-password' });
    screen(root, {
      app,
      title: 'Choose a new password',
      intro: forced ? 'You signed in with a temporary password. Please choose your own to continue.' : '',
      fields: [[forced ? 'Temporary password' : 'Current password', current], ['New password (at least 10 characters)', pw], ['Confirm new password', pw2]],
      submitText: 'Save password',
      onSubmit: async () => {
        if (pw.value !== pw2.value) throw new Error('Passwords do not match');
        const { user } = await api.auth.changePassword(current.value, pw.value);
        resolve(user);
      },
    });
  });
}
