import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConfirmationService, MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';
import { Dialog } from 'primeng/dialog';
import { Message } from 'primeng/message';
import { Textarea } from 'primeng/textarea';
import { Timeline } from 'primeng/timeline';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { REQUEST_PRIORITY_LABELS, REQUEST_STATUS_LABELS, RequestStatus } from '../../../../shared/models/request-status.model';
import { RelativeDatePipe } from '../../../../shared/pipes/relative-date-pipe';
import { apiErrorMessage } from '../../../../shared/utils/api-errors';
import { RequestAction, RequestDetail as RequestDetailModel, StatusHistoryItem } from '../../models/request.model';
import { RequestsService } from '../../services/requests.service';

type ButtonSeverity = 'primary' | 'secondary' | 'success' | 'info' | 'warn' | 'danger' | 'contrast';

interface ActionConfig {
  label: string;
  icon: string;
  severity: ButtonSeverity;
  confirm: string; // ConfirmDialog question (reject uses its own dialog instead)
  done: string; // toast summary after success
}

/** How each workflow action looks. Which ones show is decided by the server (available_actions). */
const ACTIONS: Record<RequestAction, ActionConfig> = {
  submit: { label: 'Submit', icon: 'pi pi-send', severity: 'primary', confirm: 'Submit this request for review? You will not be able to edit it afterwards.', done: 'Request submitted' },
  start_review: { label: 'Start review', icon: 'pi pi-eye', severity: 'info', confirm: 'Start reviewing this request?', done: 'Review started' },
  approve: { label: 'Approve', icon: 'pi pi-check', severity: 'success', confirm: 'Approve this request?', done: 'Request approved' },
  reject: { label: 'Reject', icon: 'pi pi-times', severity: 'danger', confirm: '', done: 'Request rejected' },
  complete: { label: 'Mark completed', icon: 'pi pi-flag', severity: 'contrast', confirm: 'Mark this request as completed? This is final.', done: 'Request completed' },
};

/** Required and not just whitespace (the server trims too). */
const notBlank = Validators.pattern(/\S/);

@Component({
  selector: 'app-request-detail',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    Card,
    Button,
    Dialog,
    Message,
    Textarea,
    Timeline,
    StatusBadge,
    RelativeDatePipe,
  ],
  templateUrl: './request-detail.html',
  styleUrl: './request-detail.scss',
})
export class RequestDetail implements OnInit {
  private readonly requestsService = inject(RequestsService);
  private readonly confirmation = inject(ConfirmationService);
  private readonly messages = inject(MessageService);
  private readonly route = inject(ActivatedRoute);
  private readonly currentUser = inject(AuthService).currentUser;

  protected readonly actions = ACTIONS;
  /** Pass-through: drop the empty "opposite" column so events use the full card width. */
  protected readonly timelinePt = { eventOpposite: { style: { display: 'none' } } };

  protected readonly priorityLabels = REQUEST_PRIORITY_LABELS;

  private id = 0;
  protected readonly request = signal<RequestDetailModel | null>(null);
  protected readonly history = signal<StatusHistoryItem[]>([]);
  protected readonly loading = signal(true);
  protected readonly notFound = signal(false);
  protected readonly loadError = signal<string | null>(null);
  /** The action currently being sent, so its button shows a spinner and the others are disabled. */
  protected readonly acting = signal<RequestAction | null>(null);

  protected readonly rejectVisible = signal(false);
  protected readonly rejectRemarks = new FormControl('', { nonNullable: true, validators: [Validators.required, notBlank] });

  protected statusLabel(status: RequestStatus): string {
    return REQUEST_STATUS_LABELS[status];
  }

  protected readonly canEdit = computed(() => {
    const r = this.request();
    return !!r && r.status === 'draft' && r.requester.id === this.currentUser()?.id;
  });

  ngOnInit(): void {
    this.id = Number(this.route.snapshot.paramMap.get('id'));
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.loadError.set(null);
    forkJoin({
      request: this.requestsService.get(this.id),
      history: this.requestsService.history(this.id),
    }).subscribe({
      next: ({ request, history }) => {
        this.request.set(request);
        this.history.set(history);
        this.loading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.loading.set(false);
        if (error.status === 404 || !this.id) {
          this.notFound.set(true);
        } else {
          this.loadError.set(apiErrorMessage(error, 'Could not load this request.'));
        }
      },
    });
  }

  protected onAction(action: RequestAction, event: Event): void {
    if (action === 'reject') {
      this.rejectRemarks.reset();
      this.rejectVisible.set(true);
      return;
    }
    const config = ACTIONS[action];
    this.confirmation.confirm({
      target: event.target as EventTarget,
      header: config.label,
      message: config.confirm,
      icon: config.icon,
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      acceptButtonProps: { label: config.label, severity: config.severity },
      accept: () => this.perform(action),
    });
  }

  protected confirmReject(): void {
    if (this.rejectRemarks.invalid) {
      this.rejectRemarks.markAsTouched();
      return;
    }
    this.perform('reject', this.rejectRemarks.value.trim());
  }

  private perform(action: RequestAction, remarks = ''): void {
    this.acting.set(action);
    this.requestsService.transition(this.id, action, remarks).subscribe({
      next: () => {
        this.acting.set(null);
        this.rejectVisible.set(false);
        this.messages.add({ severity: 'success', summary: ACTIONS[action].done });
        this.load();
      },
      error: (error) => {
        this.acting.set(null);
        this.messages.add({ severity: 'error', summary: `${ACTIONS[action].label} failed`, detail: apiErrorMessage(error) });
        // The request may have changed under us (e.g. someone else acted first): refresh what is allowed.
        if (action !== 'reject' || (error as HttpErrorResponse).status !== 400) {
          this.rejectVisible.set(false);
          this.load();
        }
      },
    });
  }
}
