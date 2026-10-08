import { RequestPriority, RequestStatus } from '../../../shared/models/request-status.model';

export interface Category {
  id: number;
  name: string;
  is_active: boolean;
}

export interface CategorySummary {
  id: number;
  name: string;
}

export interface Requester {
  id: number;
  name: string;
}

/** GET /requests/ item */
export interface RequestListItem {
  id: number;
  title: string;
  category: CategorySummary;
  requester: Requester;
  status: RequestStatus;
  priority: RequestPriority;
  created_at: string;
}

/** Workflow actions; the server lists the ones the current user may take in available_actions. */
export type RequestAction = 'submit' | 'start_review' | 'approve' | 'reject' | 'complete';

/** GET /requests/{id}/, and the response of POST/PATCH and every workflow action */
export interface RequestDetail extends RequestListItem {
  description: string;
  updated_at: string;
  available_actions: RequestAction[];
}

/** GET /requests/{id}/history/ item (newest first) */
export interface StatusHistoryItem {
  id: number;
  from_status: RequestStatus;
  to_status: RequestStatus;
  changed_by: Requester;
  remarks: string;
  changed_at: string;
}

/** Body for POST /requests/ and PATCH /requests/{id}/ */
export interface RequestWrite {
  title: string;
  description: string;
  category: number;
  priority: RequestPriority;
}

/** Query params for GET /requests/ */
export interface RequestQuery {
  page: number;
  ordering?: string; // e.g. "-created_at", "priority"
  search?: string;
  status?: RequestStatus[]; // repeated ?status= params; empty means any
  category?: number | null;
}
