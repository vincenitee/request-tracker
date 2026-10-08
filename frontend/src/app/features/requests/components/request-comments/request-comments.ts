import { DatePipe } from '@angular/common';
import { Component, computed, inject, input, OnInit, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ConfirmationService, MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';
import { Message } from 'primeng/message';
import { Textarea } from 'primeng/textarea';

import { COMMENT_MAX_LENGTH } from '../../../../shared/constants/attachments';
import { RequestStatus } from '../../../../shared/models/request-status.model';
import { RelativeDatePipe } from '../../../../shared/pipes/relative-date-pipe';
import { notifyError } from '../../../../shared/utils/notify';
import { Comment } from '../../models/request.model';
import { CommentsService } from '../../services/comments.service';

@Component({
  selector: 'app-request-comments',
  imports: [DatePipe, ReactiveFormsModule, Card, Button, Message, Textarea, RelativeDatePipe],
  templateUrl: './request-comments.html',
  styleUrl: './request-comments.scss',
})
export class RequestComments implements OnInit {
  private readonly commentsService = inject(CommentsService);
  private readonly confirmation = inject(ConfirmationService);
  private readonly messages = inject(MessageService);

  readonly requestId = input.required<number>();
  readonly status = input.required<RequestStatus>();

  protected readonly maxLength = COMMENT_MAX_LENGTH;
  protected readonly comments = signal<Comment[]>([]);
  protected readonly loading = signal(true);
  protected readonly posting = signal(false);
  /** Same rule as services.can_comment: anyone who can see the request, once it is not a draft. */
  protected readonly canPost = computed(() => this.status() !== 'draft');

  protected readonly body = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.pattern(/\S/), Validators.maxLength(COMMENT_MAX_LENGTH)],
  });
  /** A FormGroup on the <form> is what makes (ngSubmit) fire instead of a native, page-reloading submit. */
  protected readonly form = new FormGroup({ body: this.body });
  protected readonly length = toSignal(this.body.valueChanges, { initialValue: '' });

  ngOnInit(): void {
    this.commentsService.list(this.requestId()).subscribe({
      next: (comments) => {
        this.comments.set(comments);
        this.loading.set(false);
      },
      error: (error) => {
        this.loading.set(false);
        notifyError(this.messages, 'Could not load comments', error);
      },
    });
  }

  protected post(): void {
    if (this.body.invalid) {
      this.body.markAsTouched();
      return;
    }
    this.posting.set(true);
    this.commentsService.add(this.requestId(), this.body.value.trim()).subscribe({
      next: (comment) => {
        this.comments.update((list) => [...list, comment]);
        this.body.reset();
        this.posting.set(false);
      },
      error: (error) => {
        this.posting.set(false);
        notifyError(this.messages, 'Comment not posted', error);
      },
    });
  }

  protected confirmDelete(comment: Comment, event: Event): void {
    this.confirmation.confirm({
      target: event.target as EventTarget,
      header: 'Delete comment',
      message: 'Delete this comment? This cannot be undone.',
      icon: 'pi pi-exclamation-triangle',
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      acceptButtonProps: { label: 'Delete', severity: 'danger' },
      accept: () =>
        this.commentsService.delete(this.requestId(), comment.id).subscribe({
          next: () => this.comments.update((list) => list.filter((c) => c.id !== comment.id)),
          error: (error) =>
            notifyError(this.messages, 'Could not delete comment', error),
        }),
    });
  }
}
