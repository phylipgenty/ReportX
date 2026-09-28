/**
 * Thin fetch wrapper around the Python API. Every backend path lives here
 * so pages never touch URLs directly.
 */

const BASE = '/api';

/** Fired when the session has expired or the user signed out elsewhere. */
export const UNAUTHORIZED_EVENT = 'reportx:unauthorized';

async function request(path, { method = 'GET', body, raw } = {}) {
  // X-ReportX marks requests as coming from this app (CSRF protection on the server).
  const opts = { method, headers: { 'X-ReportX': '1' }, credentials: 'same-origin' };
  if (body !== undefined && !raw) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  } else if (raw) {
    opts.body = body;   // FormData
  }

  const res = await fetch(BASE + path, opts);

  if (res.status === 401 && !path.startsWith('/auth/')) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') detail = j.detail;
      else if (Array.isArray(j.detail)) detail = j.detail.map(d => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ');
    } catch {}
    throw new Error(detail);
  }

  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

function form(fields) {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) {
    if (v !== undefined && v !== null && v !== '') fd.append(k, v);
  }
  return fd;
}

function query(params) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '' && v !== false) q.set(k, v);
  }
  return q.toString();
}

export const api = {
  bootstrap: () => request('/bootstrap'),

  auth: {
    status: () => request('/auth/status'),
    setup:  (payload) => request('/auth/setup', { method: 'POST', body: payload }),
    login:  (email, password) => request('/auth/login', { method: 'POST', body: { email, password } }),
    logout: () => request('/auth/logout', { method: 'POST' }),
    changePassword: (current_password, new_password) =>
      request('/auth/change-password', { method: 'POST', body: { current_password, new_password } }),
  },

  users: {
    directory: () => request('/users/directory'),
  },

  admin: {
    users:         () => request('/admin/users'),
    createUser:    (payload) => request('/admin/users', { method: 'POST', body: payload }),
    updateUser:    (id, payload) => request(`/admin/users/${id}`, { method: 'PUT', body: payload }),
    resetPassword: (id) => request(`/admin/users/${id}/reset-password`, { method: 'POST' }),

    reference:     () => request('/admin/reference'),
    addRef:        (kind, payload) => request(`/admin/reference/${kind}`, { method: 'POST', body: payload }),
    editRef:       (kind, id, payload) => request(`/admin/reference/${kind}/${id}`, { method: 'PUT', body: payload }),
    deleteRef:     (kind, id) => request(`/admin/reference/${kind}/${id}`, { method: 'DELETE' }),
    editMilestone: (key, payload) => request(`/admin/milestones/${key}`, { method: 'PUT', body: payload }),
    addLookup:     (kind, payload) => request(`/admin/lookups/${kind}`, { method: 'POST', body: payload }),
    editLookup:    (kind, value, payload) => request(`/admin/lookups/${kind}/${encodeURIComponent(value)}`, { method: 'PUT', body: payload }),
    deleteLookup:  (kind, value) => request(`/admin/lookups/${kind}/${encodeURIComponent(value)}`, { method: 'DELETE' }),
    editImportField: (key, payload) => request(`/admin/import-fields/${key}`, { method: 'PUT', body: payload }),

    settings:      () => request('/admin/settings'),
    saveSettings:  (payload) => request('/admin/settings', { method: 'PUT', body: payload }),
  },

  portfolio: {
    summary: (entityId) => request(`/portfolio/summary?${query({ entity_id: entityId })}`),
  },

  projects: {
    list:   () => request('/projects'),
    get:    (id) => request(`/projects/${id}`),
    create: (payload) => request('/projects', { method: 'POST', body: payload }),
    update: (id, patch) => request(`/projects/${id}`, { method: 'PATCH', body: patch }),
  },

  milestones: {
    update: (projectId, key, payload) =>
      request(`/projects/${projectId}/milestones/${key}`, { method: 'PATCH', body: payload }),
  },

  costs: {
    get:       () => request('/cost-assumptions'),
    update:    (payload) => request('/cost-assumptions', { method: 'PUT', body: payload }),
    byProject: () => request('/cost-assumptions/by-project'),
  },

  issues: {
    add:    (projectId, payload)     => request(`/projects/${projectId}/issues`, { method: 'POST', body: payload }),
    update: (projectId, id, payload) => request(`/projects/${projectId}/issues/${id}`, { method: 'PUT', body: payload }),
    remove: (projectId, id)          => request(`/projects/${projectId}/issues/${id}`, { method: 'DELETE' }),
  },

  risks: {
    add:    (projectId, payload)     => request(`/projects/${projectId}/risks`, { method: 'POST', body: payload }),
    update: (projectId, id, payload) => request(`/projects/${projectId}/risks/${id}`, { method: 'PUT', body: payload }),
    remove: (projectId, id)          => request(`/projects/${projectId}/risks/${id}`, { method: 'DELETE' }),
  },

  documents: {
    upload: (projectId, file, { milestoneKey, replaces } = {}) =>
      request(`/projects/${projectId}/documents`, {
        method: 'POST', raw: true,
        body: form({ file, milestone_key: milestoneKey, replaces }),
      }),
    remove: (projectId, id) => request(`/projects/${projectId}/documents/${id}`, { method: 'DELETE' }),
  },

  states: {
    save: (projectId, label) => request(`/projects/${projectId}/states`, { method: 'POST', body: { label } }),
    list: (projectId) => request(`/projects/${projectId}/states`),
    get:  (projectId, stateId) => request(`/projects/${projectId}/states/${stateId}`),
    changes: (projectId) => request(`/projects/${projectId}/changes`),
  },

  reports: {
    review: (projectId, req) => request(`/projects/${projectId}/report`, { method: 'POST', body: req }),
    wordUrl: (projectId, req) => `${BASE}/projects/${projectId}/report/word?${query(req)}`,
    pdfUrl:  (projectId, req) => `${BASE}/projects/${projectId}/report/pdf?${query(req)}`,
  },

  imports: {
    preview: (file) => request('/imports/preview', { method: 'POST', raw: true, body: form({ file }) }),
    review: ({ file, sheet, mapping, onExisting }) => request('/imports/review', {
      method: 'POST', raw: true,
      body: form({ file, sheet, mapping: JSON.stringify(mapping), on_existing: onExisting }),
    }),
    commit: ({ file, sheet, mapping, onExisting }) => request('/imports/commit', {
      method: 'POST', raw: true,
      body: form({ file, sheet, mapping: JSON.stringify(mapping), on_existing: onExisting }),
    }),
  },
};
