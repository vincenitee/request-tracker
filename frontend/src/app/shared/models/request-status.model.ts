// Shared because the status badge (shared/) and several features need the same values.
export type RequestStatus = 'draft' | 'submitted' | 'in_review' | 'approved' | 'rejected' | 'completed';
export type RequestPriority = 'low' | 'medium' | 'high';

export const REQUEST_STATUS_LABELS: Record<RequestStatus, string> = {
  draft: 'Draft',
  submitted: 'Submitted',
  in_review: 'In review',
  approved: 'Approved',
  rejected: 'Rejected',
  completed: 'Completed',
};

export const REQUEST_PRIORITY_LABELS: Record<RequestPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

/** [{label, value}] lists for p-select. */
export const REQUEST_STATUS_OPTIONS = Object.entries(REQUEST_STATUS_LABELS).map(([value, label]) => ({
  value: value as RequestStatus,
  label,
}));
export const REQUEST_PRIORITY_OPTIONS = Object.entries(REQUEST_PRIORITY_LABELS).map(([value, label]) => ({
  value: value as RequestPriority,
  label,
}));

export type StatusSeverity = 'secondary' | 'info' | 'warn' | 'success' | 'danger' | 'contrast';

/** The one place that decides how a status looks (badge, dashboard cards, bars). */
export const REQUEST_STATUS_SEVERITY: Record<RequestStatus, StatusSeverity> = {
  draft: 'secondary',
  submitted: 'info',
  in_review: 'warn',
  approved: 'success',
  rejected: 'danger',
  completed: 'contrast',
};

/** Solid colour per severity, from the Aura palette, for bars and accents. */
export const SEVERITY_COLOR: Record<StatusSeverity, string> = {
  secondary: 'var(--p-surface-400)',
  info: 'var(--p-sky-500)',
  warn: 'var(--p-orange-500)',
  success: 'var(--p-green-500)',
  danger: 'var(--p-red-500)',
  contrast: 'var(--p-surface-800)',
};
