import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormControl, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';
import { InputText } from 'primeng/inputtext';
import { Message } from 'primeng/message';
import { Select } from 'primeng/select';
import { Textarea } from 'primeng/textarea';

import { AuthService } from '../../../../core/auth/auth.service';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { REQUEST_PRIORITY_OPTIONS, RequestPriority, RequestStatus } from '../../../../shared/models/request-status.model';
import { apiErrorMessage, applyServerErrors } from '../../../../shared/utils/api-errors';
import { Category, RequestDetail, RequestWrite } from '../../models/request.model';
import { CategoriesService } from '../../services/categories.service';
import { RequestsService } from '../../services/requests.service';

export const TITLE_MAX = 200;

@Component({
  selector: 'app-request-form',
  imports: [ReactiveFormsModule, RouterLink, Card, InputText, Textarea, Select, Button, Message, StatusBadge],
  templateUrl: './request-form.html',
  styleUrl: './request-form.scss',
})
export class RequestForm implements OnInit {
  private readonly requestsService = inject(RequestsService);
  private readonly categoriesService = inject(CategoriesService);
  private readonly messages = inject(MessageService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly currentUser = inject(AuthService).currentUser;

  protected readonly titleMax = TITLE_MAX;
  protected readonly priorityOptions = REQUEST_PRIORITY_OPTIONS;

  /** null while creating, the id while editing */
  protected readonly requestId = signal<number | null>(null);
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly categories = signal<Category[]>([]);
  protected readonly status = signal<RequestStatus | null>(null);
  /** Set when the loaded request may not be edited; the form is then read-only. */
  protected readonly readOnlyReason = signal<string | null>(null);

  protected readonly form = inject(NonNullableFormBuilder).group({
    title: ['', [Validators.required, Validators.maxLength(TITLE_MAX)]],
    description: ['', Validators.required],
    category: new FormControl<number | null>(null, Validators.required),
    priority: ['medium' as RequestPriority, Validators.required],
  });

  ngOnInit(): void {
    this.categoriesService.listActive().subscribe({
      next: (categories) => this.categories.set(categories),
      error: (error) =>
        this.messages.add({ severity: 'error', summary: 'Could not load categories', detail: apiErrorMessage(error) }),
    });

    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (id) {
      this.requestId.set(id);
      this.load(id);
    }
  }

  protected showError(control: 'title' | 'description' | 'category' | 'priority'): boolean {
    const c = this.form.controls[control];
    return c.invalid && c.touched;
  }

  protected save(): void {
    if (this.readOnlyReason()) {
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    const body = this.form.getRawValue() as RequestWrite;
    const id = this.requestId();
    const call = id ? this.requestsService.update(id, body) : this.requestsService.create(body);

    call.subscribe({
      next: (saved) => {
        this.messages.add({ severity: 'success', summary: id ? 'Draft updated' : 'Draft created', detail: saved.title });
        this.router.navigate(['/requests']);
      },
      error: (error) => {
        this.saving.set(false);
        const message = applyServerErrors(this.form, error);
        this.messages.add({
          severity: 'error',
          summary: 'Could not save',
          detail: message ?? 'Please fix the highlighted fields.',
        });
      },
    });
  }

  private load(id: number): void {
    this.loading.set(true);
    this.requestsService.get(id).subscribe({
      next: (request) => {
        this.fill(request);
        this.loading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.loading.set(false);
        this.messages.add({
          severity: 'error',
          summary: error.status === 404 ? 'Request not found' : 'Could not load request',
          detail: error.status === 404 ? undefined : apiErrorMessage(error),
        });
        this.router.navigate(['/requests']);
      },
    });
  }

  private fill(request: RequestDetail): void {
    this.status.set(request.status);
    this.form.setValue({
      title: request.title,
      description: request.description,
      category: request.category.id,
      priority: request.priority,
    });

    if (request.requester.id !== this.currentUser()?.id) {
      this.readOnlyReason.set('Only the person who created this request can edit it.');
    } else if (request.status !== 'draft') {
      this.readOnlyReason.set('This request has been submitted, so it can no longer be edited.');
    }
    if (this.readOnlyReason()) {
      this.form.disable();
    }
  }
}
