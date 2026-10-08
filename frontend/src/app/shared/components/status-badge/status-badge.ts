import { Component, computed, input } from '@angular/core';
import { Tag } from 'primeng/tag';

import { REQUEST_STATUS_LABELS, RequestStatus } from '../../models/request-status.model';

type TagSeverity = 'secondary' | 'info' | 'warn' | 'success' | 'danger' | 'contrast';

/** The one place that decides how a status looks. */
const STATUS_SEVERITY: Record<RequestStatus, TagSeverity> = {
  draft: 'secondary',
  submitted: 'info',
  in_review: 'warn',
  approved: 'success',
  rejected: 'danger',
  completed: 'contrast',
};

@Component({
  selector: 'app-status-badge',
  imports: [Tag],
  template: `<p-tag [value]="label()" [severity]="severity()" />`,
})
export class StatusBadge {
  readonly status = input.required<RequestStatus>();

  protected readonly label = computed(() => REQUEST_STATUS_LABELS[this.status()]);
  protected readonly severity = computed(() => STATUS_SEVERITY[this.status()]);
}
