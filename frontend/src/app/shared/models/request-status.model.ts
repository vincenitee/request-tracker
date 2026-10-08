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
