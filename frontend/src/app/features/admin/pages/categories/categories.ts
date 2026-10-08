import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ConfirmationService, MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { Tag } from 'primeng/tag';
import { ToggleSwitch } from 'primeng/toggleswitch';

import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { TableSkeleton } from '../../../../shared/components/table-skeleton/table-skeleton';
import { ApiError } from '../../../../shared/models/api-error.model';
import { Category } from '../../../../shared/models/category.model';
import { notifyError } from '../../../../shared/utils/notify';
import { NameDialog } from '../../components/name-dialog/name-dialog';
import { AdminCategoriesService } from '../../services/admin-categories.service';

@Component({
  selector: 'app-categories',
  imports: [FormsModule, Button, Card, TableModule, Tag, ToggleSwitch, EmptyState, PageHeader, TableSkeleton, NameDialog],
  templateUrl: './categories.html',
})
export class Categories implements OnInit {
  private readonly categoriesService = inject(AdminCategoriesService);
  private readonly confirmation = inject(ConfirmationService);
  private readonly messages = inject(MessageService);

  protected readonly categories = signal<Category[]>([]);
  protected readonly loading = signal(true);
  protected readonly loadFailed = signal(false);
  /** Id of the category whose active flag is being saved. */
  protected readonly toggling = signal<number | null>(null);

  protected readonly dialogOpen = signal(false);
  protected readonly editing = signal<Category | null>(null);
  protected readonly saving = signal(false);
  protected readonly nameError = signal<string | null>(null);

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.loadFailed.set(false);
    this.categoriesService.listAll().subscribe({
      next: (list) => {
        this.categories.set(list);
        this.loading.set(false);
      },
      error: (error) => {
        this.loading.set(false);
        this.loadFailed.set(true);
        notifyError(this.messages, 'Could not load categories', error);
      },
    });
  }

  protected openCreate(): void {
    this.editing.set(null);
    this.nameError.set(null);
    this.dialogOpen.set(true);
  }

  protected openEdit(category: Category): void {
    this.editing.set(category);
    this.nameError.set(null);
    this.dialogOpen.set(true);
  }

  protected save(name: string): void {
    const editing = this.editing();
    this.saving.set(true);
    const call = editing ? this.categoriesService.update(editing.id, { name }) : this.categoriesService.create(name);
    call.subscribe({
      next: (saved) => {
        this.saving.set(false);
        this.dialogOpen.set(false);
        this.messages.add({ severity: 'success', summary: editing ? 'Category renamed' : 'Category created', detail: saved.name });
        this.load();
      },
      error: (error: HttpErrorResponse) => {
        this.saving.set(false);
        const nameErrors = (error.error as Partial<ApiError> | null)?.errors?.['name'];
        if (error.status === 400 && nameErrors) {
          this.nameError.set(Array.isArray(nameErrors) ? nameErrors.join(' ') : String(nameErrors));
        } else {
          notifyError(this.messages, 'Could not save category', error);
        }
      },
    });
  }

  protected setActive(category: Category, isActive: boolean): void {
    this.toggling.set(category.id);
    this.categoriesService.update(category.id, { is_active: isActive }).subscribe({
      next: (saved) => {
        this.toggling.set(null);
        this.categories.update((list) => list.map((c) => (c.id === saved.id ? saved : c)));
        this.messages.add({
          severity: 'success',
          summary: isActive ? 'Category activated' : 'Category deactivated',
          detail: isActive ? saved.name : `${saved.name} can no longer be chosen for new requests.`,
        });
      },
      error: (error) => {
        this.toggling.set(null);
        this.load(); // put the switch back to the server's value
        notifyError(this.messages, 'Could not update category', error);
      },
    });
  }

  protected confirmDelete(category: Category, event: Event): void {
    this.confirmation.confirm({
      target: event.target as EventTarget,
      header: 'Delete category',
      message: `Delete "${category.name}"?`,
      icon: 'pi pi-exclamation-triangle',
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      acceptButtonProps: { label: 'Delete', severity: 'danger' },
      accept: () =>
        this.categoriesService.delete(category.id).subscribe({
          next: () => {
            this.messages.add({ severity: 'success', summary: 'Category deleted', detail: category.name });
            this.load();
          },
          // e.g. "This category is used by existing requests. Deactivate it instead."
          error: (error) => notifyError(this.messages, 'Cannot delete category', error),
        }),
    });
  }
}
