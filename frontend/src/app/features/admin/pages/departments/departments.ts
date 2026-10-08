import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';
import { TableModule } from 'primeng/table';

import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { TableSkeleton } from '../../../../shared/components/table-skeleton/table-skeleton';
import { ApiError } from '../../../../shared/models/api-error.model';
import { notifyError } from '../../../../shared/utils/notify';
import { NameDialog } from '../../components/name-dialog/name-dialog';
import { Department } from '../../models/admin.model';
import { DepartmentsService } from '../../services/departments.service';

@Component({
  selector: 'app-departments',
  imports: [Button, Card, TableModule, EmptyState, PageHeader, TableSkeleton, NameDialog],
  templateUrl: './departments.html',
})
export class Departments implements OnInit {
  private readonly departmentsService = inject(DepartmentsService);
  private readonly confirmation = inject(ConfirmationService);
  private readonly messages = inject(MessageService);

  protected readonly departments = signal<Department[]>([]);
  protected readonly loading = signal(true);
  protected readonly loadFailed = signal(false);

  protected readonly dialogOpen = signal(false);
  protected readonly editing = signal<Department | null>(null);
  protected readonly saving = signal(false);
  protected readonly nameError = signal<string | null>(null);

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.loadFailed.set(false);
    this.departmentsService.list().subscribe({
      next: (list) => {
        this.departments.set(list);
        this.loading.set(false);
      },
      error: (error) => {
        this.loading.set(false);
        this.loadFailed.set(true);
        notifyError(this.messages, 'Could not load departments', error);
      },
    });
  }

  protected openCreate(): void {
    this.editing.set(null);
    this.nameError.set(null);
    this.dialogOpen.set(true);
  }

  protected openEdit(department: Department): void {
    this.editing.set(department);
    this.nameError.set(null);
    this.dialogOpen.set(true);
  }

  protected save(name: string): void {
    const editing = this.editing();
    this.saving.set(true);
    const call = editing ? this.departmentsService.update(editing.id, name) : this.departmentsService.create(name);
    call.subscribe({
      next: (saved) => {
        this.saving.set(false);
        this.dialogOpen.set(false);
        this.messages.add({ severity: 'success', summary: editing ? 'Department renamed' : 'Department created', detail: saved.name });
        this.load();
      },
      error: (error: HttpErrorResponse) => {
        this.saving.set(false);
        const nameErrors = (error.error as Partial<ApiError> | null)?.errors?.['name'];
        if (error.status === 400 && nameErrors) {
          this.nameError.set(Array.isArray(nameErrors) ? nameErrors.join(' ') : String(nameErrors));
        } else {
          notifyError(this.messages, 'Could not save department', error);
        }
      },
    });
  }

  protected confirmDelete(department: Department, event: Event): void {
    this.confirmation.confirm({
      target: event.target as EventTarget,
      header: 'Delete department',
      message: `Delete "${department.name}"?`,
      icon: 'pi pi-exclamation-triangle',
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      acceptButtonProps: { label: 'Delete', severity: 'danger' },
      accept: () =>
        this.departmentsService.delete(department.id).subscribe({
          next: () => {
            this.messages.add({ severity: 'success', summary: 'Department deleted', detail: department.name });
            this.load();
          },
          // e.g. "2 users are assigned to this department. Move them to another department first."
          error: (error) => notifyError(this.messages, 'Cannot delete department', error),
        }),
    });
  }
}
