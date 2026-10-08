export type Role = 'staff' | 'reviewer' | 'admin';

export interface DepartmentSummary {
  id: number;
  name: string;
}

/** Shape of GET /api/v1/me/ */
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  department: DepartmentSummary | null;
}

export interface TokenPair {
  access: string;
  refresh: string;
}
