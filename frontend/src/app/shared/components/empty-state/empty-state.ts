import { Component, input } from '@angular/core';

/** Icon + title + message, with projected content for an action button. */
@Component({
  selector: 'app-empty-state',
  template: `
    <div class="empty-state" role="status">
      <i [class]="'pi ' + icon() + ' icon'" aria-hidden="true"></i>
      <h3>{{ title() }}</h3>
      @if (message()) {
        <p>{{ message() }}</p>
      }
      <ng-content />
    </div>
  `,
  styles: `
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 32px 16px;
      text-align: center;
      color: var(--p-text-muted-color);
    }
    .icon {
      font-size: 2rem;
    }
    h3 {
      margin: 0;
      font-size: 1.05rem;
      color: var(--p-text-color);
    }
    p {
      margin: 0;
      max-width: 36rem;
    }
  `,
})
export class EmptyState {
  readonly icon = input('pi-inbox');
  readonly title = input.required<string>();
  readonly message = input<string>('');
}
