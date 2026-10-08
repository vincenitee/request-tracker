import { HttpErrorResponse } from '@angular/common/http';
import { MessageService } from 'primeng/api';

import { isGloballyHandled } from '../http/error-context';
import { apiErrorMessage } from './api-errors';

/**
 * Toast for errors a page handles itself (400 validation, 404, business rules).
 * Network / 403 / 429 / 5xx are already toasted by the global error interceptor, so they are skipped
 * here to avoid double toasts.
 */
export function notifyError(messages: MessageService, summary: string, error: unknown, detail?: string): void {
  if (error instanceof HttpErrorResponse && isGloballyHandled(error.status)) {
    return;
  }
  messages.add({ severity: 'error', summary, detail: detail ?? apiErrorMessage(error) });
}
