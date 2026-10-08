import { DatePipe } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';
import { FileUpload, FileUploadHandlerEvent } from 'primeng/fileupload';
import { ProgressBar } from 'primeng/progressbar';
import { catchError, concatMap, filter, finalize, from, of, tap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import {
  ATTACHMENT_ALLOWED_EXTENSIONS,
  ATTACHMENT_MAX_BYTES,
  ATTACHMENT_MAX_PER_REQUEST,
  fileExtension,
  validateAttachment,
} from '../../../../shared/constants/attachments';
import { FileSizePipe } from '../../../../shared/pipes/file-size-pipe';
import { RelativeDatePipe } from '../../../../shared/pipes/relative-date-pipe';
import { blobApiErrorMessage } from '../../../../shared/utils/api-errors';
import { notifyError } from '../../../../shared/utils/notify';
import { Attachment, RequestDetail } from '../../models/request.model';
import { AttachmentsService } from '../../services/attachments.service';

const ICONS: Record<string, string> = {
  pdf: 'pi pi-file-pdf',
  png: 'pi pi-image',
  jpg: 'pi pi-image',
  jpeg: 'pi pi-image',
  docx: 'pi pi-file-word',
  xlsx: 'pi pi-file-excel',
};

@Component({
  selector: 'app-request-attachments',
  imports: [DatePipe, Card, Button, FileUpload, ProgressBar, FileSizePipe, RelativeDatePipe],
  templateUrl: './request-attachments.html',
  styleUrl: './request-attachments.scss',
})
export class RequestAttachments {
  private readonly attachmentsService = inject(AttachmentsService);
  private readonly confirmation = inject(ConfirmationService);
  private readonly messages = inject(MessageService);
  private readonly currentUser = inject(AuthService).currentUser;

  readonly request = input.required<RequestDetail>();

  protected readonly maxFiles = ATTACHMENT_MAX_PER_REQUEST;
  protected readonly limitsText =
    `Up to ${ATTACHMENT_MAX_PER_REQUEST} files, ${ATTACHMENT_MAX_BYTES / (1024 * 1024)} MB each: ` +
    ATTACHMENT_ALLOWED_EXTENSIONS.join(', ');

  protected readonly attachments = signal<Attachment[]>([]);
  protected readonly loading = signal(true);
  /** Name of the file being sent and its progress (0-100), or null when idle. */
  protected readonly uploading = signal<string | null>(null);
  protected readonly progress = signal(0);
  protected readonly downloading = signal<number | null>(null);

  /** Same rule as services.can_manage_attachments; the server enforces it regardless. */
  protected readonly canUpload = computed(() => {
    const user = this.currentUser();
    const r = this.request();
    return user?.role === 'admin' || (r.requester.id === user?.id && r.status === 'draft');
  });
  protected readonly isRequester = computed(() => this.request().requester.id === this.currentUser()?.id);
  protected readonly full = computed(() => this.attachments().length >= ATTACHMENT_MAX_PER_REQUEST);

  constructor() {
    // (Re)load whenever the request or its status changes: can_delete depends on the status,
    // so a list loaded while the request was a draft is stale once it is submitted.
    effect(() => {
      const id = this.request().id;
      this.request().status; // tracked on purpose
      untracked(() => this.load(id));
    });
  }

  private load(requestId: number): void {
    this.attachmentsService.list(requestId).subscribe({
      next: (attachments) => {
        this.attachments.set(attachments);
        this.loading.set(false);
      },
      error: (error) => {
        this.loading.set(false);
        notifyError(this.messages, 'Could not load attachments', error);
      },
    });
  }

  protected icon(attachment: Attachment): string {
    return ICONS[fileExtension(attachment.original_name)] ?? 'pi pi-file';
  }

  /** p-fileupload (basic + auto + customUpload) hands us the picked files; we upload them one by one. */
  protected onFilesPicked(event: FileUploadHandlerEvent, uploader: FileUpload): void {
    const requestId = this.request().id;
    let accepted = this.attachments().length;

    const valid = event.files.filter((file) => {
      const error = validateAttachment(file, accepted);
      if (error) {
        this.messages.add({ severity: 'error', summary: `${file.name} was not uploaded`, detail: error });
        return false;
      }
      accepted++;
      return true;
    });

    from(valid)
      .pipe(
        concatMap((file) => {
          this.uploading.set(file.name);
          this.progress.set(0);
          return this.attachmentsService.upload(requestId, file).pipe(
            tap((evt) => {
              if (evt.type === HttpEventType.UploadProgress && evt.total) {
                this.progress.set(Math.round((100 * evt.loaded) / evt.total));
              }
            }),
            filter((evt) => evt.type === HttpEventType.Response),
            tap((evt) => {
              if (evt.type === HttpEventType.Response && evt.body) {
                this.attachments.update((list) => [...list, evt.body!]);
              }
            }),
            // One failure must not stop the remaining files.
            catchError((error) => {
              notifyError(this.messages, `${file.name} was not uploaded`, error);
              return of(null);
            }),
          );
        }),
        finalize(() => {
          this.uploading.set(null);
          uploader.clear(); // lets the same file be picked again
        }),
      )
      .subscribe();
  }

  protected download(attachment: Attachment): void {
    this.downloading.set(attachment.id);
    this.attachmentsService.download(this.request().id, attachment.id).subscribe({
      next: (blob) => {
        this.downloading.set(null);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = attachment.original_name;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      },
      error: async (error) => {
        this.downloading.set(null);
        notifyError(this.messages, 'Download failed', error, await blobApiErrorMessage(error));
      },
    });
  }

  protected confirmDelete(attachment: Attachment, event: Event): void {
    this.confirmation.confirm({
      target: event.target as EventTarget,
      header: 'Delete file',
      message: `Delete "${attachment.original_name}"? This cannot be undone.`,
      icon: 'pi pi-exclamation-triangle',
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      acceptButtonProps: { label: 'Delete', severity: 'danger' },
      accept: () =>
        this.attachmentsService.delete(this.request().id, attachment.id).subscribe({
          next: () => {
            this.attachments.update((list) => list.filter((a) => a.id !== attachment.id));
            this.messages.add({ severity: 'success', summary: 'File deleted', detail: attachment.original_name });
          },
          error: (error) =>
            notifyError(this.messages, 'Could not delete file', error),
        }),
    });
  }
}
