import { DatePipe } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';
import { ProgressBar } from 'primeng/progressbar';
import { Skeleton } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';

import { AuthService } from '../../core/auth/auth.service';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../shared/components/page-header/page-header';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import {
  REQUEST_STATUS_LABELS,
  REQUEST_STATUS_SEVERITY,
  RequestStatus,
  SEVERITY_COLOR,
} from '../../shared/models/request-status.model';
import { Role } from '../../shared/models/user.model';
import { RelativeDatePipe } from '../../shared/pipes/relative-date-pipe';
import { apiErrorMessage } from '../../shared/utils/api-errors';
import { DashboardSummary } from './models/dashboard.model';
import { DashboardService } from './services/dashboard.service';

const STATUSES = Object.keys(REQUEST_STATUS_LABELS) as RequestStatus[];

const WORDING: Record<Role, { scope: string; subtitle: string; action: (n: number) => string; actionHint: string }> = {
  staff: {
    scope: 'My requests',
    subtitle: 'Everything you have created.',
    action: (n) => `${n} draft${n === 1 ? '' : 's'} waiting to be submitted`,
    actionHint: 'Drafts are not visible to reviewers until you submit them.',
  },
  reviewer: {
    scope: 'Department requests',
    subtitle: 'Requests from your department, plus your own.',
    action: (n) => `${n} request${n === 1 ? '' : 's'} waiting for your review`,
    actionHint: 'Submitted or in review, from your department, not created by you.',
  },
  admin: {
    scope: 'All requests',
    subtitle: 'Every request in the system.',
    action: (n) => `${n} request${n === 1 ? '' : 's'} waiting for review`,
    actionHint: 'Submitted or in review, not created by you.',
  },
};

@Component({
  selector: 'app-dashboard',
  imports: [DatePipe, RouterLink, Button, Card, ProgressBar, Skeleton, TableModule, EmptyState, PageHeader, StatusBadge, RelativeDatePipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private readonly dashboardService = inject(DashboardService);
  protected readonly user = inject(AuthService).currentUser;

  protected readonly statuses = STATUSES;
  protected readonly skeletonCards = Array.from({ length: 8 }, (_, i) => i);
  protected readonly summary = signal<DashboardSummary | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly wording = computed(() => WORDING[this.user()?.role ?? 'staff']);

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.dashboardService.summary().subscribe({
      next: (summary) => {
        this.summary.set(summary);
        this.loading.set(false);
      },
      error: (error) => {
        this.loading.set(false);
        this.error.set(apiErrorMessage(error, 'Could not load the dashboard.'));
      },
    });
  }

  protected label(status: RequestStatus): string {
    return REQUEST_STATUS_LABELS[status];
  }

  protected color(status: RequestStatus): string {
    return SEVERITY_COLOR[REQUEST_STATUS_SEVERITY[status]];
  }

  protected percent(count: number): number {
    const total = this.summary()?.total ?? 0;
    return total ? Math.round((count / total) * 100) : 0;
  }
}
