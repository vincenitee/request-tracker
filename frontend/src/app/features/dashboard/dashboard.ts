import { Component, inject } from '@angular/core';
import { Card } from 'primeng/card';
import { Tag } from 'primeng/tag';

import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-dashboard',
  imports: [Card, Tag],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard {
  protected readonly user = inject(AuthService).currentUser;
}
