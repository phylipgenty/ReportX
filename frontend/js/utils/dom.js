/**
 * Tiny DOM helpers. No framework.
 */

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on') && typeof v === 'function') {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (k === 'dataset') {
      Object.assign(node.dataset, v);
    } else if (k === 'style' && typeof v === 'object') {
      Object.assign(node.style, v);
    } else {
      node.setAttribute(k, v);
    }
  }
  const list = Array.isArray(children) ? children : [children];
  for (const c of list) {
    if (c == null || c === false) continue;
    node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

export function mount(node, children) {
  clear(node);
  const list = Array.isArray(children) ? children : [children];
  for (const c of list) {
    if (c == null || c === false) continue;
    node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return node;
}

export function qs(sel, root = document) { return root.querySelector(sel); }
export function qsa(sel, root = document) { return [...root.querySelectorAll(sel)]; }

export function svg(path, size = 18) {
  const ns = 'http://www.w3.org/2000/svg';
  const s = document.createElementNS(ns, 'svg');
  s.setAttribute('viewBox', '0 0 24 24');
  s.setAttribute('width', size);
  s.setAttribute('height', size);
  s.setAttribute('fill', 'none');
  s.setAttribute('stroke', 'currentColor');
  s.setAttribute('stroke-width', '1.75');
  s.setAttribute('stroke-linecap', 'round');
  s.setAttribute('stroke-linejoin', 'round');
  const p = document.createElementNS(ns, 'path');
  p.setAttribute('d', path);
  s.appendChild(p);
  return s;
}

/** Confirmation dialog; resolves true when confirmed. */
export function confirmDialog(message, { confirmText = 'Confirm' } = {}) {
  return new Promise((resolve) => {
    const yes = el('button', { class: 'btn btn-primary', text: confirmText });
    const no = el('button', { class: 'btn btn-outline', text: 'Cancel' });
    const m = openModal({ title: 'Please confirm', body: el('p', { text: message }), footer: [no, yes] });
    yes.addEventListener('click', () => { m.close(); resolve(true); });
    no.addEventListener('click', () => { m.close(); resolve(false); });
  });
}

/** Show a toast. type: '', 'success', 'error' */
export function toast(message, type = '') {
  const root = document.getElementById('toast-root');
  if (!root) return;
  const node = el('div', { class: `toast ${type}`, text: message });
  root.appendChild(node);
  setTimeout(() => {
    node.style.transition = 'opacity .25s';
    node.style.opacity = '0';
    setTimeout(() => node.remove(), 300);
  }, 2600);
}

/** Simple modal. Returns { close, node }. size: '' | 'wide' */
export function openModal({ title, body, footer, size = '' }) {
  const root = document.getElementById('modal-root');
  const backdrop = el('div', { class: 'modal-backdrop' });
  const close = () => backdrop.remove();

  const modal = el('div', { class: `modal ${size}` }, [
    el('div', { class: 'modal-header' }, [
      el('h3', { text: title || '' }),
      el('button', { class: 'btn btn-ghost btn-sm', text: 'Close', onclick: close }),
    ]),
    el('div', { class: 'modal-body' }, [body]),
    footer ? el('div', { class: 'modal-footer' }, footer) : null,
  ]);
  backdrop.appendChild(modal);
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
  root.appendChild(backdrop);
  return { close, node: modal };
}