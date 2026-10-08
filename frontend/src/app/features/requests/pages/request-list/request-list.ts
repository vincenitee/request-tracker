import { DatePipe } from '@angular/common';
import { Component, computed, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ConfirmationService, MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { IconField } from 'primeng/iconfield';
import { InputIcon } from 'primeng/inputicon';
import { InputText } from 'primeng/inputtext';
import { Select } from 'primeng/select';
import { SelectButton } from 'primeng/selectbutton';
import { TableLazyLoadEvent, TableModule } from 'primeng/table';
import { catchError, debounceTime, distinctUntilChanged, map, of, Subject, switchMap, tap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import {
  REQUEST_PRIORITY_LABELS,
  REQUEST_STATUS_OPTIONS,
  RequestPriority,
  RequestStatus,
} from '../../../../shared/models/request-status.model';
import { RelativeDatePipe } from '../../../../shared/pipes/relative-date-pipe';
import { apiErrorMessage } from '../../../../shared/utils/api-errors';
import { Category, RequestListItem, RequestQuery } from '../../models/request.model';
import { CategoriesService } from '../../services/categories.service';
import { RequestsService } from '../../services/requests.service';

const PAGE_SIZE = 10; // matches DRF PAGE_SIZE

type Preset = 'all' | 'needs_review';
const PRESET_STATUSES: Record<Preset, RequestStatus[]> = {
  all: [],
  needs_review: ['submitted', 'in_review'],
};

@Component({
  selector: 'app-request-list',
  imports: [
    DatePipe,
    FormsModule,
    RouterLink,
    TableModule,
    Button,
    IconField,
    InputIcon,
    InputText,
    Select,
    SelectButton,
    StatusBadge,
    RelativeDatePipe,
  ],
  templateUrl: './request-list.html',
  styleUrl: './request-list.scss',
})
export class RequestList implements OnInit {
  private readonly requestsService = inject(RequestsService);
  private readonly categoriesService = inject(CategoriesService);
  private readonly confirmation = inject(ConfirmationService);
  private readonly messages = inject(MessageService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly currentUser = inject(AuthService).currentUser;

  /** Quick tabs for the people who review requests. */
  protected readonly showPresets = computed(() => ['reviewer', 'admin'].includes(this.currentUser()?.role ?? ''));
  protected readonly presetOptions = [
    { label: 'All', value: 'all' as Preset },
    { label: 'Needs review', value: 'needs_review' as Preset },
  ];
  protected readonly preset = signal<Preset>('all');

  protected readonly pageSize = PAGE_SIZE;
  protected readonly statusOptions = REQUEST_STATUS_OPTIONS;

  protected readonly items = signal<RequestListItem[]>([]);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly first = signal(0); // index of the first row shown, bound to p-table
  protected readonly categories = signal<Category[]>([]);

  protected readonly search = signal('');
  protected readonly status = signal<RequestStatus | null>(null);
  protected readonly category = signal<number | null>(null);
  private ordering = '-created_at';

  private readonly reload$ = new Subject<void>();
  private readonly searchInput$ = new Subject<string>();

  ngOnInit(): void {
    // switchMap cancels an in-flight request when a newer one starts (fast typing, quick paging).
    this.reload$
      .pipe(
        map(() => this.currentQuery()),
        tap(() => this.loading.set(true)),
        switchMap((query) =>
          this.requestsService.list(query).pipe(
            catchError((error) => {
              this.messages.add({ severity: 'error', summary: 'Could not load requests', detail: apiErrorMessage(error) });
              return of({ count: 0, next: null, previous: null, results: [] });
            }),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.items.set(page.results);
        this.total.set(page.count);
        this.loading.set(false);
      });

    this.searchInput$
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe((term) => {
        this.search.set(term.trim());
        this.resetToFirstPage();
      });

    this.categoriesService.listActive().subscribe({
      next: (categories) => this.categories.set(categories),
      error: () => this.categories.set([]),
    });
  }

  /** p-table fires this on init, page change and sort change. */
  protected onLazyLoad(event: TableLazyLoadEvent): void {
    this.first.set(event.first ?? 0);
    const field = Array.isArray(event.sortField) ? event.sortField[0] : event.sortField;
    if (field) {
      this.ordering = (event.sortOrder === -1 ? '-' : '') + field;
    }
    this.reload$.next();
  }

  protected onSearchInput(term: string): void {
    this.searchInput$.next(term);
  }

  protected onStatusChange(value: RequestStatus | null): void {
    this.status.set(value);
    if (value) {
      this.preset.set('all'); // an explicit status replaces the preset
    }
    this.resetToFirstPage();
  }

  protected onPresetChange(value: Preset | null): void {
    this.preset.set(value ?? 'all');
    if (this.preset() !== 'all') {
      this.status.set(null); // the preset replaces an explicit status
    }
    this.resetToFirstPage();
  }

  protected onCategoryChange(value: number | null): void {
    this.category.set(value);
    this.resetToFirstPage();
  }

  protected priorityLabel(priority: RequestPriority): string {
    return REQUEST_PRIORITY_LABELS[priority];
  }

  protected canModify(item: RequestListItem): boolean {
    return item.status === 'draft' && item.requester.id === this.currentUser()?.id;
  }

  protected confirmDelete(item: RequestListItem, event: Event): void {
    this.confirmation.confirm({
      target: event.target as EventTarget,
      header: 'Delete draft',
      message: `Delete "${item.title}"? This cannot be undone.`,
      icon: 'pi pi-exclamation-triangle',
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      acceptButtonProps: { label: 'Delete', severity: 'danger' },
      accept: () => this.delete(item),
    });
  }

  private delete(item: RequestListItem): void {
    this.requestsService.delete(item.id).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Draft deleted', detail: item.title });
        // If that was the only row on a later page, step back one page.
        if (this.items().length === 1 && this.first() > 0) {
          this.first.set(this.first() - PAGE_SIZE);
        }
        this.reload$.next();
      },
      error: (error) =>
        this.messages.add({ severity: 'error', summary: 'Delete failed', detail: apiErrorMessage(error) }),
    });
  }

  private resetToFirstPage(): void {
    this.first.set(0);
    this.reload$.next();
  }

  private currentQuery(): RequestQuery {
    return {
      page: Math.floor(this.first() / PAGE_SIZE) + 1,
      ordering: this.ordering,
      search: this.search(),
      status: this.status() ? [this.status()!] : PRESET_STATUSES[this.preset()],
      category: this.category(),
    };
  }
}
