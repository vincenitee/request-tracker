import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { MessageService } from 'primeng/api';
import { catchError, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { SKIP_GLOBAL_ERROR_TOAST } from '../../shared/http/error-context';
import { apiErrorMessage } from '../../shared/utils/api-errors';

let lastToast = { key: '', at: 0 };

/**
 * App-wide toasts for errors no page should have to handle one by one:
 * network failure, 403, 429 and 5xx. 400/401/404 are left to the caller (and to authInterceptor).
 * Opt out per request with skipGlobalErrorToast().
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const messages = inject(MessageService);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && req.url.startsWith(environment.apiUrl) && !req.context.get(SKIP_GLOBAL_ERROR_TOAST)) {
        const toast = toastFor(error);
        // Several calls failing the same way (server down, repeated throttled logins) produce one toast, not five.
        const key = `${error.status}|${toast?.summary}`;
        if (toast && (key !== lastToast.key || Date.now() - lastToast.at > 3000)) {
          lastToast = { key, at: Date.now() };
          messages.add({ severity: toast.severity, summary: toast.summary, detail: toast.detail, life: 6000 });
        }
      }
      return throwError(() => error);
    }),
  );
};

function toastFor(error: HttpErrorResponse): { severity: 'error' | 'warn'; summary: string; detail: string } | null {
  if (error.status === 0) {
    return { severity: 'error', summary: 'Cannot reach the server', detail: 'Check your connection and try again.' };
  }
  if (error.status === 403) {
    return { severity: 'warn', summary: 'You do not have access', detail: apiErrorMessage(error, 'You are not allowed to do this.') };
  }
  if (error.status === 429) {
    // The server says "Too many attempts. Please wait N seconds and try again."; the summary already says the first part.
    const detail = apiErrorMessage(error, 'Please wait a moment and try again.').replace(/^Too many attempts\.\s*/, '');
    return { severity: 'warn', summary: 'Too many attempts', detail };
  }
  if (error.status >= 500) {
    return { severity: 'error', summary: 'Something went wrong', detail: 'The server had a problem. Please try again in a moment.' };
  }
  return null;
}
