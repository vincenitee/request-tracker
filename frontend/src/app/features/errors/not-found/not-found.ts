import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';

import { EmptyState } from '../../../shared/components/empty-state/empty-state';

@Component({
  selector: 'app-not-found',
  imports: [RouterLink, Button, Card, EmptyState],
  template: `
    <p-card>
      <app-empty-state icon="pi-compass" title="Page not found" message="The page you are looking for does not exist or has moved.">
        <p-button label="Go to the dashboard" icon="pi pi-home" routerLink="/dashboard" />
      </app-empty-state>
    </p-card>
  `,
})
export class NotFound {}
