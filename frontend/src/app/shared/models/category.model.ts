/** GET /categories/ item. Shared: used by the requests feature and the admin pages. */
export interface Category {
  id: number;
  name: string;
  is_active: boolean;
}
