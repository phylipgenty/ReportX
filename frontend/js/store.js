/**
 * Tiny pub/sub store. Holds:
 *   - bootstrap (app info, entities, divisions, milestone defs, lookups, rates)
 *   - projects   (portfolio list, hydrated from server)
 *   - ui         (activeEntityId)
 */
import { api } from './api.js';
import { setCurrency } from './utils/currency.js';

const state = {
  user: null,        // signed-in user: { id, name, role, role_label, permissions, ... }
  bootstrap: null,
  projects: [],
  ui: {
    activeEntityId: 'all',
  },
};

const listeners = new Set();

export function getState() { return state; }

export function setState(patch) {
  deepMerge(state, patch);
  emit();
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  for (const fn of listeners) {
    try { fn(state); } catch (e) { console.error('[store] listener error', e); }
  }
}

function deepMerge(target, patch) {
  for (const [k, v] of Object.entries(patch)) {
    if (v && typeof v === 'object' && !Array.isArray(v) && !(v instanceof Date)) {
      if (!target[k] || typeof target[k] !== 'object') target[k] = {};
      deepMerge(target[k], v);
    } else {
      target[k] = v;
    }
  }
}

/** Loads reference data once (or again when `force` is set, e.g. after an import). */
export async function ensureBootstrap(force = false) {
  if (state.bootstrap && !force) return state.bootstrap;
  const boot = await api.bootstrap();
  state.bootstrap = boot;           // replace wholesale: lists must not merge
  setCurrency(boot.app.currency_symbol);
  emit();
  return boot;
}

export function setUser(user) {
  state.user = user;
  emit();
}

/** Mirrors the server's permission checks so the UI only offers what will succeed. */
export function can(permission) {
  return !!state.user?.permissions?.includes(permission);
}

export function canEditProject(project) {
  if (can('project.edit_all')) return true;
  return can('project.edit_own') && project?.identity?.manager_user_id === state.user?.id;
}

/* Convenience selectors */
export function filterProjectsByEntity() {
  const id = state.ui.activeEntityId;
  if (id === 'all') return state.projects;
  return state.projects.filter(p => p.identity.entity_id === id);
}

export function selectEntityName(entityId) {
  return state.bootstrap?.entities?.find(e => e.id === entityId)?.code || entityId;
}

export function selectDivisionName(divisionId) {
  return state.bootstrap?.divisions?.find(d => d.id === divisionId)?.code || divisionId;
}

export function selectMilestoneDefs() {
  const defs = state.bootstrap?.milestone_definitions || [];
  return [...defs].sort((a, b) => a.order - b.order);
}
