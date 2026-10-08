import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Category } from '../../../shared/models/category.model';

@Injectable({ providedIn: 'root' })
export class CategoriesService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/categories/`;

  /** Active categories only (admins would otherwise also get inactive ones). Not paginated. */
  listActive(): Observable<Category[]> {
    return this.http.get<Category[]>(this.url, { params: new HttpParams().set('is_active', true) });
  }
}
