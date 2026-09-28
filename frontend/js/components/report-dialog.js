import { el, openModal, toast, mount } from '../utils/dom.js';
import { api } from '../api.js';
import { can, getState } from '../store.js';
import { formatDate, formatDateTime, formatVariance, todayISO, firstOfMonthISO } from '../utils/dates.js';
import { badge, labelOf } from '../utils/lookups.js';

/**
 * README §38: Select Project → Select Reporting Period → Load Project State →
 * Review Report Data → Generate Report → Export Word/PDF.
 */
export async function openReportDialog(project) {
  let states = [];
  try { states = await api.states.list(project.id); } catch {}

  const start = el('input', { type: 'date', value: firstOfMonthISO() });
  const end = el('input', { type: 'date', value: todayISO() });
  const author = el('input', { type: 'text', value: getState().user?.name || project.identity.project_manager || '' });
  const sponsor = el('input', { type: 'text', value: project.identity.executive_sponsor || '', placeholder: 'Where applicable' });
  const source = el('select', {}, [
    el('option', { value: 'auto', text: 'Latest saved state on or before the period end (else current)' }),
    el('option', { value: 'current', text: 'Current project data' }),
    ...states.map(s => el('option', { value: s.id, text: `Saved: ${s.label || 'Untitled'} — ${formatDateTime(s.saved_at)}` })),
  ]);

  const preview = el('div', { class: 'report-preview' });
  const reviewBtn = el('button', { class: 'btn btn-ghost', text: 'Preview here' });
  const wordBtn = el('a', { class: 'btn btn-outline', text: 'Word' });
  const pdfBtn = el('a', { class: 'btn btn-outline', text: 'Download PDF' });
  const generateBtn = el('button', { class: 'btn btn-primary', text: 'Generate PDF' });

  const request = () => ({
    start_date: start.value,
    end_date: end.value,
    state_id: !['auto', 'current'].includes(source.value) ? source.value : undefined,
    use_current: source.value === 'current',
    report_author: author.value,
    executive_sponsor: sponsor.value,
  });

  // Export links always reflect the current choices.
  const refreshLinks = () => {
    wordBtn.href = api.reports.wordUrl(project.id, request());
    pdfBtn.href = api.reports.pdfUrl(project.id, request());
  };
  [start, end, author, sponsor, source].forEach(n => n.addEventListener('change', refreshLinks));
  refreshLinks();

  // Opens the formal PDF (April 2025 format) in a new tab.
  generateBtn.addEventListener('click', () => {
    if (!start.value || !end.value) { toast('Choose a reporting period', 'error'); return; }
    if (start.value > end.value) { toast('The period start must be before its end', 'error'); return; }
    window.open(api.reports.pdfUrl(project.id, { ...request(), inline: true }), '_blank', 'noopener');
  });

  reviewBtn.addEventListener('click', async () => {
    if (!start.value || !end.value) { toast('Choose a reporting period', 'error'); return; }
    reviewBtn.disabled = true;
    try {
      const req = request();
      const report = await api.reports.review(project.id, req);
      mount(preview, renderPreview(report));
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      reviewBtn.disabled = false;
    }
  });

  openModal({
    title: `Project Status Report · ${project.identity.name}`,
    size: 'wide',
    body: el('div', {}, [
      el('div', { class: 'form-grid' }, [
        field('Reporting period start', start),
        field('Reporting period end', end),
        field('Report author', author),
        field('Executive sponsor', sponsor),
      ]),
      field('Project state', source),
      preview,
    ]),
    footer: can('report.export') ? [reviewBtn, wordBtn, pdfBtn, generateBtn] : [reviewBtn],
  });
}

function renderPreview(r) {
  const m = r.metadata;
  const rows = (headers, data) => el('div', { class: 'table-wrap' }, [el('table', { class: 'data' }, [
    el('thead', {}, [el('tr', {}, headers.map(h => el('th', { text: h })))]),
    el('tbody', {}, data.map(row => el('tr', {}, row.map(c => el('td', { class: 'wrap' }, [c]))))),
  ])]);
  const list = (xs) => xs.length ? el('ul', {}, xs.map(x => el('li', { text: x }))) : el('p', { class: 'text-muted', text: 'None recorded.' });

  return el('div', {}, [
    el('div', { class: 'report-meta' }, [
      el('strong', { text: m.project_title }), ` · ${m.project_id} · ${formatDate(m.reporting_period.start_date)} to ${formatDate(m.reporting_period.end_date)}`,
      el('div', { class: 'text-xs text-muted', text: m.source.kind === 'state'
        ? `Using saved state “${m.source.label || m.source.state_id}” (${formatDateTime(m.source.saved_at)})`
        : 'Using current project data' }),
    ]),
    el('h4', { text: '1. Executive Summary' }),
    el('p', { text: r.executive_summary || 'No executive summary entered.' }),
    el('div', { class: 'flex gap-2' }, [
      'Schedule ', badge('rag', r.rag.schedule), ' Budget ', badge('rag', r.rag.budget), ' Issues ', badge('rag', r.rag.issues),
    ]),
    el('p', { class: 'text-sm', text: `Completion ${r.completion_pct}% · Variance ${formatVariance(r.variance_days)}` }),
    el('p', { text: r.narrative || '' }),
    el('h4', { text: '2. Project Milestone Status Review' }),
    rows(['Milestone', 'Status', 'Baseline', 'Expected', 'Actual', 'Issues'], r.milestone_status_review.map(x => [
      x.label, badge('milestone_status', x.status), formatDate(x.baseline_date), formatDate(x.expected_date),
      formatDate(x.actual_date), x.has_issues ? 'Yes' : 'No',
    ])),
    el('h4', { text: '3. Status of Planned Activities' }),
    el('div', { class: 'text-sm text-muted', text: 'Planned accomplishments' }), list(r.planned_activities.accomplishments),
    el('div', { class: 'text-sm text-muted', text: 'Planned but not accomplished' }), list(r.planned_activities.not_accomplished),
    el('div', { class: 'text-sm text-muted', text: 'Planned actions for next period' }), list(r.planned_activities.next_period),
    el('h4', { text: '4. Project Issues Summary' }),
    r.issues.length ? rows(['Priority', 'Issue', 'Impact', 'Action steps'], r.issues.map(i => [
      labelOf('issue_priority', i.priority), i.description, i.impact_summary, i.action_steps,
    ])) : el('p', { class: 'text-muted', text: 'No issues recorded.' }),
    el('h4', { text: '5. Project Risk Summary' }),
    r.risks.length ? rows(['Priority', 'Probability', 'Risk', 'Impact summary', 'Response', 'Status', 'Score'], r.risks.map(k => [
      labelOf('issue_priority', k.priority), `${k.probability} – ${labelOf('probability', k.probability)}`,
      k.description, k.impact_summary, k.response_strategy, labelOf('risk_status', k.status), String(k.risk_score),
    ])) : el('p', { class: 'text-muted', text: 'No risks recorded.' }),
  ]);
}

function field(label, node) {
  return el('div', { class: 'field' }, [el('label', { text: label }), node]);
}
