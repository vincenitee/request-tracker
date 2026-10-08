import { Role } from '../../../shared/models/user.model';

export interface Department {
  id: number;
  name: string;
  user_count: number;
}

/** GET /users/ item (never includes a password). */
export interface AdminUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  department: { id: number; name: string } | null;
  is_active: boolean;
  last_login: string | null;
  date_joined: string;
}

/** POST /users/ (password required) and PATCH /users/{id}/ (password not allowed). */
export interface UserWrite {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  department: number | null;
  is_active: boolean;
  password?: string;
}

export interface UserQuery {
  page: number;
  ordering?: string;
  search?: string;
  role?: Role | null;
  department?: number | null;
  isActive?: boolean | null;
}

export const ROLE_OPTIONS: { label: string; value: Role }[] = [
  { label: 'Staff', value: 'staff' },
  { label: 'Reviewer', value: 'reviewer' },
  { label: 'Admin', value: 'admin' },
];
