import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Tag } from 'primeng/tag';
import { Toolbar } from 'primeng/toolbar';

import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Toolbar, Tag, Button],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss',
})
export class MainLayout {
  protected readonly auth = inject(AuthService);
  private readonly messages = inject(MessageService);

  protected logout(): void {
    this.auth.logout();
    this.messages.add({ severity: 'info', summary: 'Logged out', detail: 'See you next time.' });
  }
}
