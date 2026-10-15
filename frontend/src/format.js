// Appointment states, in the fixed order their chart colors are assigned.
export const STATUSES = [
  { key: 'SCHEDULED', label: 'Scheduled', color: 'var(--series-1)' },
  { key: 'CHECKED_IN', label: 'Checked in', color: 'var(--series-2)' },
  { key: 'COMPLETED', label: 'Completed', color: 'var(--series-3)' },
  { key: 'CANCELLED', label: 'Cancelled', color: 'var(--series-4)' },
  { key: 'NO_SHOW', label: 'No-show', color: 'var(--series-5)' },
];

export const STATUS_BY_KEY = Object.fromEntries(STATUSES.map((s) => [s.key, s]));

// Mirrors STATUS_TRANSITIONS in backend/app/models.py.
export const NEXT_ACTIONS = {
  SCHEDULED: [
    { to: 'CHECKED_IN', label: 'Check in', primary: true },
    { to: 'NO_SHOW', label: 'No-show' },
    { to: 'CANCELLED', label: 'Cancel' },
  ],
  CHECKED_IN: [
    { to: 'COMPLETED', label: 'Complete', primary: true },
    { to: 'CANCELLED', label: 'Cancel' },
  ],
};

const timeFormat = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' });
const dateFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
});
const longDateFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
});

export const formatTime = (iso) => timeFormat.format(new Date(iso));
export const formatDate = (iso) => dateFormat.format(new Date(iso));
export const formatLongDate = (date) => longDateFormat.format(date);

/** yyyy-mm-dd for the browser's local day (what <input type="date"> uses). */
export function localISODate(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function initials(name) {
  return name
    .replace(/^Dr\.?\s+/i, '')
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

export function greeting(now = new Date()) {
  const hour = now.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export const shortSha = (sha) =>
  /^[0-9a-f]{8,40}$/.test(sha ?? '') ? sha.slice(0, 7) : (sha ?? '—');
