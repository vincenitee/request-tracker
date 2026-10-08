import { HttpErrorResponse } from '@angular/common/http';
import { FormGroup } from '@angular/forms';

import { ApiError } from '../models/api-error.model';

/** A user-facing message for any failed HTTP call. */
export function apiErrorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (!(error instanceof HttpErrorResponse)) {
    return fallback;
  }
  if (error.status === 0) {
    return 'Could not reach the server. Please try again.';
  }
  const body = error.error as Partial<ApiError> | null;
  return body?.detail ?? fallback;
}

/**
 * Puts DRF field errors on matching form controls as `{ server: message }`.
 * Returns a message for a toast when something could not be shown on a field, otherwise null.
 */
export function applyServerErrors(form: FormGroup, error: unknown): string | null {
  const fieldErrors = error instanceof HttpErrorResponse && error.status === 400
    ? (error.error as Partial<ApiError> | null)?.errors
    : undefined;

  if (!fieldErrors) {
    return apiErrorMessage(error);
  }

  const unmatched: string[] = [];
  for (const [field, messages] of Object.entries(fieldErrors)) {
    const message = Array.isArray(messages) ? messages.join(' ') : String(messages);
    const control = form.get(field);
    if (control) {
      control.setErrors({ ...control.errors, server: message });
      control.markAsTouched();
    } else {
      unmatched.push(message);
    }
  }
  return unmatched.length ? unmatched.join(' ') : null;
}
