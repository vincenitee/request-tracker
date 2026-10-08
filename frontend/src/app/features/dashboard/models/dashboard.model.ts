import { RequestPriority, RequestStatus } from '../../../shared/models/request-status.model';

/** One row of "recent" (same shape as a request list item; declared here because features do not import each other). */
export interface RecentRequest {
  id: number;
  title: string;
  category: { id: number; name: string };
  requester: { id: number; name: string };
  status: RequestStatus;
  priority: RequestPriority;
  created_at: string;
  comments_count: number;
  attachments_count: number;
}

/** GET /dashboard/summary/ */
export interface DashboardSummary {
  total: number;
  by_status: Record<RequestStatus, number>;
  by_priority: Record<RequestPriority, number>;
  needs_my_action: number;
  recent: RecentRequest[];
}
