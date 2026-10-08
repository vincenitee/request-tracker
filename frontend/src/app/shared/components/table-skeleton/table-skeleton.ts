import { Component, computed, input } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';

/** Placeholder rows shown while a list loads for the first time. */
@Component({
  selector: 'app-table-skeleton',
  imports: [Skeleton],
  template: `
    <div class="skeleton" aria-busy="true" aria-label="Loading">
      @for (row of rowList(); track row) {
        <div class="row">
          @for (col of colList(); track col) {
            <p-skeleton [width]="col === 0 ? '40%' : '100%'" height="1rem" />
          }
        </div>
      }
    </div>
  `,
  styles: `
    .skeleton {
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 16px;
    }
    .row {
      display: grid;
      grid-template-columns: 2fr repeat(auto-fit, minmax(60px, 1fr));
      gap: 16px;
    }
  `,
})
export class TableSkeleton {
  readonly rows = input(5);
  readonly cols = input(5);
  protected readonly rowList = computed(() => Array.from({ length: this.rows() }, (_, i) => i));
  protected readonly colList = computed(() => Array.from({ length: this.cols() }, (_, i) => i));
}
