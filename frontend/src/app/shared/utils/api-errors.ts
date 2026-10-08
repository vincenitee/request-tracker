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
  const detail = body?.detail ?? fallback;
  // Append field messages (e.g. a failed submit) so the toast says what to fix.
  const fields = Object.entries(body?.errors ?? {})
    .map(([field, messages]) => [field, Array.isArray(messages) ? messages.join(' ') : String(messages)] as const)
    .filter(([, text]) => text !== detail) // rule errors repeat the detail on their field
    .map(([field, text]) => `${humanize(field)}: ${text}`);
  return fields.length ? `${detail} ${fields.join(' ')}` : detail;
}

function humanize(field: string): string {
  return field === 'non_field_errors' ? 'Error' : field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, ' ');
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

/** Like apiErrorMessage, for requests made with responseType 'blob' (the JSON error body arrives as a Blob). */
export async function blobApiErrorMessage(error: unknown, fallback?: string): Promise<string> {
  if (error instanceof HttpErrorResponse && error.error instanceof Blob) {
    try {
      const body = JSON.parse(await error.error.text());
      return apiErrorMessage(new HttpErrorResponse({ error: body, status: error.status }), fallback);
    } catch {
      // not JSON: fall through to the generic message
    }
  }
  return apiErrorMessage(error, fallback);
}
