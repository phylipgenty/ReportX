/** ISO string (yyyy-mm-dd) <-> display helpers. Safe on null. */

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

export function parseISO(s) {
  if (!s) return null;
  const d = new Date(s + 'T00:00:00');
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "1 Apr 2025"; non-date values such as TBD / N/A pass through. */
export function formatDate(s) {
  if (!s) return '—';
  const d = parseISO(s);
  if (!d) return String(s);
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

/** "16 to 19 Dec 2025" style range; falls back gracefully */
export function formatDateRange(a, b) {
  if (!a && !b) return 'Not set';
  if (a && !b) return formatDate(a);
  if (!a && b) return formatDate(b);
  if (a === b) return formatDate(a);
  const da = parseISO(a), db = parseISO(b);
  if (da && db && da.getMonth() === db.getMonth() && da.getFullYear() === db.getFullYear()) {
    return `${da.getDate()} to ${db.getDate()} ${MONTHS[db.getMonth()]} ${db.getFullYear()}`;
  }
  return `${formatDate(a)} to ${formatDate(b)}`;
}

/** "1 Apr 2025, 14:05" from an ISO timestamp */
export function formatDateTime(s) {
  if (!s) return '—';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return String(s);
  const hh = String(d.getHours()).padStart(2, '0'), mm = String(d.getMinutes()).padStart(2, '0');
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}, ${hh}:${mm}`;
}

/** "+262 days" | "On date" | "Not set" */
export function formatVariance(days) {
  if (days == null) return 'Not set';
  if (days === 0) return 'On date';
  return (days > 0 ? '+' : '') + days + ' days';
}

export function varianceClass(days) {
  if (days == null) return 'muted';
  if (days === 0) return '';
  return days > 0 ? 'late' : 'early';
}

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function firstOfMonthISO() {
  return todayISO().slice(0, 8) + '01';
}