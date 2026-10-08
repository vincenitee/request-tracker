import { Component, computed, input } from '@angular/core';
import { Tag } from 'primeng/tag';

import { REQUEST_STATUS_LABELS, REQUEST_STATUS_SEVERITY, RequestStatus } from '../../models/request-status.model';

@Component({
  selector: 'app-status-badge',
  imports: [Tag],
  template: `<p-tag [value]="label()" [severity]="severity()" />`,
})
export class StatusBadge {
  readonly status = input.required<RequestStatus>();

  protected readonly label = computed(() => REQUEST_STATUS_LABELS[this.status()]);
  protected readonly severity = computed(() => REQUEST_STATUS_SEVERITY[this.status()]);
}
