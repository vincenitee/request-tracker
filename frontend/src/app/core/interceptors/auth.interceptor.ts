import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, finalize, Observable, shareReplay, switchMap, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from '../auth/auth.service';

// One refresh call shared by every request that hits a 401 at the same time.
let refreshInFlight$: Observable<string> | null = null;

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith(environment.apiUrl)) {
    return next(req); // never leak the token to third-party URLs
  }

  const auth = inject(AuthService);
  const isAuthEndpoint = req.url.startsWith(`${environment.apiUrl}/auth/`);
  const token = auth.getAccessToken();

  return next(token && !isAuthEndpoint ? withToken(req, token) : req).pipe(
    catchError((error: unknown) => {
      const canRefresh =
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        !isAuthEndpoint &&
        auth.getRefreshToken() !== null;

      if (!canRefresh) {
        return throwError(() => error);
      }

      return refreshOnce(auth).pipe(
        catchError((refreshError: unknown) => {
          auth.logout(); // refresh token expired or invalid: back to /login
          return throwError(() => refreshError);
        }),
        // The retry goes straight to `next`, so a second 401 is not refreshed again.
        switchMap((newToken) => next(withToken(req, newToken))),
      );
    }),
  );
};

function withToken(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

function refreshOnce(auth: AuthService): Observable<string> {
  refreshInFlight$ ??= auth.refresh().pipe(
    finalize(() => (refreshInFlight$ = null)),
    shareReplay(1),
  );
  return refreshInFlight$;
}
