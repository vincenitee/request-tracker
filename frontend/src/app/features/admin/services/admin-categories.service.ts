import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Category } from '../../../shared/models/category.model';

/** Category management (the requests feature has its own read-only CategoriesService for dropdowns). */
@Injectable({ providedIn: 'root' })
export class AdminCategoriesService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/categories/`;

  listAll(): Observable<Category[]> {
    return this.http.get<Category[]>(this.url, { params: new HttpParams().set('include_inactive', true) });
  }

  create(name: string): Observable<Category> {
    return this.http.post<Category>(this.url, { name });
  }

  update(id: number, body: Partial<Pick<Category, 'name' | 'is_active'>>): Observable<Category> {
    return this.http.patch<Category>(`${this.url}${id}/`, body);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.url}${id}/`);
  }
}
