import { el, openModal, toast } from '../utils/dom.js';
import { api } from '../api.js';
import { lookupSelect, milestoneLabel } from '../utils/lookups.js';
import { DateField } from './date-field.js';

/** README §12: Milestone · Start (baseline) · End (expected/actual) · Status · Note. */
export function openMilestoneUpdateForm(project, milestoneKey, onDone) {
  const current = project.milestones.find(m => m.key === milestoneKey) || {};

  const statusSel = lookupSelect('milestone_status', current.status);
  const baseline = DateField(current.baseline_date);
  const expected = DateField(current.expected_date);
  const actual   = DateField(current.actual_date);
  const note     = el('textarea', { placeholder: 'Milestone note' });
  note.value = current.note || '';
  const why      = el('input', { type: 'text', placeholder: 'Optional: why this changed (kept in history)' });

  const body = el('div', {}, [
    el('div', { class: 'form-grid' }, [
      el('div', { class: 'field' }, [el('label', { text: 'Status' }), statusSel]),
      el('div', { class: 'field' }, [el('label', { text: 'Baseline date' }), baseline.node]),
      el('div', { class: 'field' }, [el('label', { text: 'Expected date' }), expected.node]),
      el('div', { class: 'field' }, [el('label', { text: 'Actual date' }), actual.node]),
    ]),
    el('div', { class: 'field' }, [el('label', { text: 'Note' }), note]),
    el('div', { class: 'field' }, [el('label', { text: 'Change reason' }), why]),
  ]);

  const saveBtn = el('button', { class: 'btn btn-primary', text: 'Save update' });
  const modal = openModal({ title: `Update ${milestoneLabel(milestoneKey, { short: false })}`, body, footer: [saveBtn] });

  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    try {
      await api.milestones.update(project.id, milestoneKey, {
        status:        statusSel.value,
        baseline_date: baseline.value(),
        expected_date: expected.value(),
        actual_date:   actual.value(),
        note:          note.value,
        change_note:   why.value,
      });
      toast('Milestone updated', 'success');
      modal.close();
      onDone && onDone();
    } catch (e) {
      toast(e.message || 'Update failed', 'error');
    } finally {
      saveBtn.disabled = false;
    }
  });
}
