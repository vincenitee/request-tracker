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

/** GET /requests/{id}/, and the response of POST/PATCH */
export interface RequestDetail extends RequestListItem {
  description: string;
  updated_at: string;
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
  status?: RequestStatus | null;
  category?: number | null;
}
