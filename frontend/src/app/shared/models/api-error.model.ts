/** Error body for every API error (see backend apps/core/exceptions.py). */
export interface ApiError {
  detail: string;
  errors: Record<string, string[] | string>;
}
