import { Routes } from '@angular/router';

// Lazy-loaded by app.routes.ts; the parent route already applies authGuard.
export const REQUESTS_ROUTES: Routes = [
  {
    path: '',
    title: 'Requests',
    loadComponent: () => import('./pages/request-list/request-list').then((m) => m.RequestList),
  },
  {
    path: 'new',
    title: 'New request',
    loadComponent: () => import('./pages/request-form/request-form').then((m) => m.RequestForm),
  },
  {
    path: ':id',
    title: 'Request details',
    loadComponent: () => import('./pages/request-detail/request-detail').then((m) => m.RequestDetail),
  },
  {
    path: ':id/edit',
    title: 'Edit request',
    loadComponent: () => import('./pages/request-form/request-form').then((m) => m.RequestForm),
  },
];
