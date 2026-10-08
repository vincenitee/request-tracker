import { Routes } from '@angular/router';

// Lazy-loaded by app.routes.ts; the parent route already applies authGuard.
export const REQUESTS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./request-list/request-list').then((m) => m.RequestList),
  },
  {
    path: 'new',
    loadComponent: () => import('./request-form/request-form').then((m) => m.RequestForm),
  },
  {
    path: ':id/edit',
    loadComponent: () => import('./request-form/request-form').then((m) => m.RequestForm),
  },
];
