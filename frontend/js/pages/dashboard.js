import { el, mount } from '../utils/dom.js';
import { api } from '../api.js';
import { getState, filterProjectsByEntity, ensureBootstrap, can } from '../store.js';
import { renderTopbar } from '../components/topbar.js';
import { renderEntityTabs } from '../components/entity-tabs.js';
import { KpiCard } from '../components/kpi-card.js';
import { SchedulePerformanceRow, CostPerformanceRow } from '../components/performance-bar.js';
import { PortfolioTable } from '../components/portfolio-table.js';
import { formatMoney } from '../utils/currency.js';

/** README §28 / §45: portfolio KPIs, schedule & cost performance, project table. */
export async function DashboardPage({ topbar, view }) {
  renderTopbar(topbar, {
    eyebrow: 'Portfolio',
    title: 'Project portfolio',
    actions: [
      can('import') ? el('a', { class: 'btn btn-outline', text: 'Import from Excel', href: '#/import' }) : null,
      can('project.create') ? el('a', { class: 'btn btn-primary', text: '+ New project', href: '#/project/new' }) : null,
    ].filter(Boolean),
  });

  mount(view, el('div', { class: 'loader', text: 'Loading portfolio…' }));

  try {
    await ensureBootstrap();
    const [projects, summary] = await Promise.all([
      api.projects.list(),
      api.portfolio.summary(getState().ui.activeEntityId),
    ]);
    getState().projects = projects;
    render(summary);
  } catch (e) {
    mount(view, el('div', { class: 'empty', text: `Failed to load portfolio: ${e.message}` }));
  }

  function render(k) {
    const filtered = filterProjectsByEntity();
    const live = filtered.filter(p => !p.is_draft);

    const tabs = el('div', {});
    renderEntityTabs(tabs);

    const kpis = el('div', { class: 'kpi-grid' }, [
      KpiCard({ label: 'Completed', value: String(k.completed), foot: `of ${k.projects} projects${k.drafts ? ` · ${k.drafts} draft` : ''}` }),
      KpiCard({ label: 'Average completion', value: `${Math.round(k.average_completion)}%`, barPct: k.average_completion }),
      KpiCard({ label: 'Not started', value: String(k.not_started) }),
      KpiCard({ label: 'Needs attention', value: String(k.needs_attention), foot: 'Any RAG flagged for attention' }),
      KpiCard({ label: 'At risk / delayed', value: String(k.at_risk_delayed), foot: 'Late forecast or delayed milestone' }),
      KpiCard({
        label: 'Spend vs budget',
        value: `${Math.round(k.spend_pct)}%`,
        foot: `${formatMoney(k.total_actual, { compact: true })} of ${formatMoney(k.total_budget, { compact: true })}`,
      }),
    ]);

    const panel = (title, subtitle, rows) => el('div', { class: 'card' }, [
      el('div', { class: 'card-header' }, [el('div', {}, [
        el('div', { class: 'card-title', text: title }),
        el('div', { class: 'card-subtitle', text: subtitle }),
      ])]),
      el('div', { class: 'perf-list' }, rows.length ? rows : [el('div', { class: 'empty', text: 'No projects.' })]),
    ]);

    const schedulePanel = panel('Schedule performance', 'Actual or forecast delivery vs TSC-approved date',
      live.map(p => SchedulePerformanceRow({ label: p.identity.name, days: p.schedule.variance_days })));
    const costPanel = panel('Cost performance', 'Actual cost vs planned budget',
      live.map(p => CostPerformanceRow({ label: p.identity.name, budget: p.resources.planned_budget, actual: p.resources.actual_cost_to_date })));

    const portfolio = el('div', { class: 'card portfolio-card' }, [
      el('div', { class: 'card-header' }, [
        el('div', { class: 'card-title', text: 'All projects' }),
        can('project.create') ? el('a', { class: 'btn btn-outline btn-sm', text: '+ Add project', href: '#/project/new' }) : null,
      ]),
      PortfolioTable(filtered),
    ]);

    mount(view, el('div', {}, [tabs, kpis, el('div', { class: 'dash-grid' }, [schedulePanel, costPanel]), portfolio]));
  }
}

