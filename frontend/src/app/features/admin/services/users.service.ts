import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Paginated } from '../../../shared/models/paginated.model';
import { AdminUser, UserQuery, UserWrite } from '../models/admin.model';

@Injectable({ providedIn: 'root' })
export class UsersService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/users/`;

  list(query: UserQuery): Observable<Paginated<AdminUser>> {
    let params = new HttpParams().set('page', query.page);
    if (query.ordering) params = params.set('ordering', query.ordering);
    if (query.search) params = params.set('search', query.search);
    if (query.role) params = params.set('role', query.role);
    if (query.department) params = params.set('department', query.department);
    if (query.isActive != null) params = params.set('is_active', query.isActive);
    return this.http.get<Paginated<AdminUser>>(this.url, { params });
  }

  create(body: UserWrite): Observable<AdminUser> {
    return this.http.post<AdminUser>(this.url, body);
  }

  update(id: number, body: Partial<UserWrite>): Observable<AdminUser> {
    return this.http.patch<AdminUser>(`${this.url}${id}/`, body);
  }

  setPassword(id: number, password: string): Observable<void> {
    return this.http.post<void>(`${this.url}${id}/set-password/`, { password });
  }
}
