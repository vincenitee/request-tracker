import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Paginated } from '../../../shared/models/paginated.model';
import {
  RequestAction,
  RequestDetail,
  RequestListItem,
  RequestQuery,
  RequestWrite,
  StatusHistoryItem,
} from '../models/request.model';

@Injectable({ providedIn: 'root' })
export class RequestsService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/requests/`;

  list(query: RequestQuery): Observable<Paginated<RequestListItem>> {
    let params = new HttpParams().set('page', query.page);
    if (query.ordering) params = params.set('ordering', query.ordering);
    if (query.search) params = params.set('search', query.search);
    for (const status of query.status ?? []) params = params.append('status', status);
    if (query.category) params = params.set('category', query.category);
    if (query.needsMyAction) params = params.set('needs_my_action', true);
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

  history(id: number): Observable<StatusHistoryItem[]> {
    return this.http.get<StatusHistoryItem[]>(`${this.url}${id}/history/`);
  }

  submit(id: number): Observable<RequestDetail> {
    return this.transition(id, 'submit');
  }

  startReview(id: number): Observable<RequestDetail> {
    return this.transition(id, 'start_review');
  }

  approve(id: number, remarks = ''): Observable<RequestDetail> {
    return this.transition(id, 'approve', remarks);
  }

  reject(id: number, remarks: string): Observable<RequestDetail> {
    return this.transition(id, 'reject', remarks);
  }

  complete(id: number): Observable<RequestDetail> {
    return this.transition(id, 'complete');
  }

  /** POST /requests/{id}/<action>/ (URL segments are kebab-case: start_review -> start-review). */
  transition(id: number, action: RequestAction, remarks = ''): Observable<RequestDetail> {
    return this.http.post<RequestDetail>(`${this.url}${id}/${action.replace('_', '-')}/`, { remarks });
  }
}
