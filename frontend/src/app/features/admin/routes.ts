import { Routes } from '@angular/router';

// Lazy-loaded under /admin; the parent route applies authGuard + roleGuard (roles: ['admin']).
export const ADMIN_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'users' },
  {
    path: 'users',
    title: 'Users',
    loadComponent: () => import('./pages/users/users').then((m) => m.Users),
  },
  {
    path: 'departments',
    title: 'Departments',
    loadComponent: () => import('./pages/departments/departments').then((m) => m.Departments),
  },
  {
    path: 'categories',
    title: 'Categories',
    loadComponent: () => import('./pages/categories/categories').then((m) => m.Categories),
  },
];
