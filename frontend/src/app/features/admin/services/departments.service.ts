import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Department } from '../models/admin.model';

@Injectable({ providedIn: 'root' })
export class DepartmentsService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/departments/`;

  list(): Observable<Department[]> {
    return this.http.get<Department[]>(this.url);
  }

  create(name: string): Observable<Department> {
    return this.http.post<Department>(this.url, { name });
  }

  update(id: number, name: string): Observable<Department> {
    return this.http.patch<Department>(`${this.url}${id}/`, { name });
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.url}${id}/`);
  }
}
