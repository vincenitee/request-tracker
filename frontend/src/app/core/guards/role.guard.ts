import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { MessageService } from 'primeng/api';

import { AuthService } from '../auth/auth.service';
import { Role } from '../../shared/models/user.model';

/**
 * Allows the route only for the roles in route data, e.g. `data: { roles: ['admin'] }`.
 * Use after authGuard. Denied users go to /dashboard with a toast.
 */
export const roleGuard: CanActivateFn = (route) => {
  const allowed = (route.data['roles'] as Role[] | undefined) ?? [];
  const role = inject(AuthService).currentUser()?.role;
  if (role && allowed.includes(role)) {
    return true;
  }
  inject(MessageService).add({ severity: 'warn', summary: 'You do not have access', detail: 'That page is for admins only.' });
  return inject(Router).createUrlTree(['/dashboard']);
};
