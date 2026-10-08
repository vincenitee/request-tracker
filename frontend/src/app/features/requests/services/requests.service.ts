import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Paginated } from '../../../shared/models/paginated.model';
import { RequestDetail, RequestListItem, RequestQuery, RequestWrite } from '../models/request.model';

@Injectable({ providedIn: 'root' })
export class RequestsService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/requests/`;

  list(query: RequestQuery): Observable<Paginated<RequestListItem>> {
    let params = new HttpParams().set('page', query.page);
    if (query.ordering) params = params.set('ordering', query.ordering);
    if (query.search) params = params.set('search', query.search);
    if (query.status) params = params.set('status', query.status);
    if (query.category) params = params.set('category', query.category);
    return this.http.get<Paginated<RequestListItem>>(this.url, { params });
  }

  get(id: number): Observable<RequestDetail> {
    return this.http.get<RequestDetail>(`${this.url}${id}/`);
  }

  create(body: RequestWrite): Observable<RequestDetail> {
    return this.http.post<RequestDetail>(this.url, body);
  }

  update(id: number, body: Partial<RequestWrite>): Observable<RequestDetail> {
    return this.http.patch<RequestDetail>(`${this.url}${id}/`, body);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.url}${id}/`);
  }
}
