import { RequestPriority, RequestStatus } from '../../../shared/models/request-status.model';

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
  comments_count: number;
  attachments_count: number;
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
  needsMyAction?: boolean; // ?needs_my_action=true
}

/** GET /requests/{id}/comments/ item (oldest first) */
export interface Comment {
  id: number;
  author: Requester;
  body: string;
  created_at: string;
  can_delete: boolean;
}

/** GET /requests/{id}/attachments/ item */
export interface Attachment {
  id: number;
  original_name: string;
  content_type: string;
  size: number;
  uploaded_by: Requester;
  uploaded_at: string;
  can_delete: boolean;
}
