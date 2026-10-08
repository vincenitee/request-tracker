import { HttpClient, HttpEvent } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Attachment } from '../models/request.model';

@Injectable({ providedIn: 'root' })
export class AttachmentsService {
  private readonly http = inject(HttpClient);

  private url(requestId: number): string {
    return `${environment.apiUrl}/requests/${requestId}/attachments/`;
  }

  list(requestId: number): Observable<Attachment[]> {
    return this.http.get<Attachment[]>(this.url(requestId));
  }

  /** multipart/form-data with field "file"; emits progress events, then the HttpResponse. */
  upload(requestId: number, file: File): Observable<HttpEvent<Attachment>> {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http.post<Attachment>(this.url(requestId), form, { reportProgress: true, observe: 'events' });
  }

  delete(requestId: number, attachmentId: number): Observable<void> {
    return this.http.delete<void>(`${this.url(requestId)}${attachmentId}/`);
  }

  /** Fetched as a Blob so the auth interceptor can attach the token (a plain link cannot). */
  download(requestId: number, attachmentId: number): Observable<Blob> {
    return this.http.get(`${this.url(requestId)}${attachmentId}/download/`, { responseType: 'blob' });
  }
}
