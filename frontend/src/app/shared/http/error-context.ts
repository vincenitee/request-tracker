import { HttpContext, HttpContextToken } from '@angular/common/http';

/** When true, the global error interceptor stays quiet for this request (the caller shows its own message). */
export const SKIP_GLOBAL_ERROR_TOAST = new HttpContextToken<boolean>(() => false);

/** Usage: http.get(url, { context: skipGlobalErrorToast() }) */
export function skipGlobalErrorToast(context = new HttpContext()): HttpContext {
  return context.set(SKIP_GLOBAL_ERROR_TOAST, true);
}

/** Status codes the global interceptor turns into a toast (network error, forbidden, throttled, server). */
export function isGloballyHandled(status: number): boolean {
  return status === 0 || status === 403 || status === 429 || status >= 500;
}
