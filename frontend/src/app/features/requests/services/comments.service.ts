import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Comment } from '../models/request.model';

@Injectable({ providedIn: 'root' })
export class CommentsService {
  private readonly http = inject(HttpClient);

  private url(requestId: number): string {
    return `${environment.apiUrl}/requests/${requestId}/comments/`;
  }

  list(requestId: number): Observable<Comment[]> {
    return this.http.get<Comment[]>(this.url(requestId));
  }

  add(requestId: number, body: string): Observable<Comment> {
    return this.http.post<Comment>(this.url(requestId), { body });
  }

  delete(requestId: number, commentId: number): Observable<void> {
    return this.http.delete<void>(`${this.url(requestId)}${commentId}/`);
  }
}
