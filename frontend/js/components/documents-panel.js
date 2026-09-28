import { el, openModal, toast, confirmDialog } from '../utils/dom.js';
import { api } from '../api.js';
import { selectMilestoneDefs } from '../store.js';
import { formatDateTime } from '../utils/dates.js';
import { section } from './issues-panel.js';

/**
 * README §25–§27: optional attachments per lifecycle document, quick PDF
 * viewing in-app, and replace. Attachments are supporting artefacts only.
 */
export function DocumentsPanel(project, reload, editable) {
  const docs = project.documents;
  const rows = selectMilestoneDefs().map(d => docRow(project, d.short_label, d.key, docs.filter(x => x.milestone_key === d.key), reload, editable));
  rows.push(docRow(project, 'Other', null, docs.filter(x => !x.milestone_key), reload, editable));

  return section('Documents', el('div', {}, [
    el('p', { class: 'text-sm text-muted', text: 'Attachments are optional.' }),
    el('div', { class: 'doc-list' }, rows),
  ]));
}

function docRow(project, label, milestoneKey, docs, reload, editable) {
  const upload = (replaces) => pickFile(async (file) => {
    try {
      await api.documents.upload(project.id, file, { milestoneKey, replaces });
      toast(replaces ? 'Attachment replaced' : 'Attachment uploaded', 'success');
      reload();
    } catch (e) { toast(e.message, 'error'); }
  });

  return el('div', { class: 'doc-row' }, [
    el('div', { class: 'doc-label', text: label }),
    el('div', { class: 'doc-files' }, [
      ...docs.map(d => el('div', { class: 'doc-file' }, [
        el('div', {}, [
          el('div', { class: 'doc-name', text: d.filename }),
          el('div', { class: 'text-xs text-muted', text: `${formatDateTime(d.uploaded_at)} · ${d.uploaded_by}` }),
        ]),
        el('div', { class: 'row-actions' }, [
          el('button', { class: 'btn btn-ghost btn-sm', text: isPdf(d) ? 'View PDF' : 'Open', onclick: () => viewDocument(d) }),
          editable ? el('button', { class: 'btn btn-ghost btn-sm', text: 'Replace', onclick: () => upload(d.id) }) : null,
          !editable ? null : el('button', {
            class: 'btn btn-ghost btn-sm', text: 'Remove',
            onclick: async () => {
              if (!(await confirmDialog(`Remove ${d.filename}?`, { confirmText: 'Remove' }))) return;
              try { await api.documents.remove(project.id, d.id); reload(); }
              catch (e) { toast(e.message, 'error'); }
            },
          }),
        ]),
      ])),
      editable && (!docs.length || !milestoneKey)
        ? el('button', { class: 'btn btn-outline btn-sm', text: 'Upload', onclick: () => upload(null) })
        : (!docs.length ? el('span', { class: 'text-sm text-muted', text: '—' }) : null),
    ]),
  ]);
}

function isPdf(d) {
  return d.mime_type === 'application/pdf' || d.filename.toLowerCase().endsWith('.pdf');
}

/** In-app viewer for PDFs; other types open in a new tab. */
export function viewDocument(d) {
  if (!isPdf(d)) { window.open(d.url, '_blank', 'noopener'); return; }
  openModal({
    title: d.filename,
    size: 'wide',
    body: el('iframe', { class: 'pdf-frame', src: d.url, title: d.filename }),
    // Phones often can't show a PDF inside the page, so offer the browser's own viewer too.
    footer: [
      el('a', { class: 'btn btn-outline', text: 'Open in new tab', href: d.url, target: '_blank', rel: 'noopener' }),
      el('a', { class: 'btn btn-outline', text: 'Download', href: `${d.url}?download=true` }),
    ],
  });
}

function pickFile(onPick) {
  const input = el('input', { type: 'file', style: { display: 'none' } });
  input.addEventListener('change', () => { if (input.files[0]) onPick(input.files[0]); input.remove(); });
  document.body.appendChild(input);
  input.click();
}
