import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Drawer } from 'primeng/drawer';
import { Tag } from 'primeng/tag';
import { Toolbar } from 'primeng/toolbar';
import { filter } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';

interface NavItem {
  label: string;
  icon: string;
  link: string;
}

const MAIN_NAV: NavItem[] = [
  { label: 'Dashboard', icon: 'pi pi-home', link: '/dashboard' },
  { label: 'Requests', icon: 'pi pi-list', link: '/requests' },
];

const ADMIN_NAV: NavItem[] = [
  { label: 'Users', icon: 'pi pi-users', link: '/admin/users' },
  { label: 'Departments', icon: 'pi pi-building', link: '/admin/departments' },
  { label: 'Categories', icon: 'pi pi-tags', link: '/admin/categories' },
];

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Toolbar, Tag, Button, Drawer],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss',
})
export class MainLayout {
  protected readonly auth = inject(AuthService);
  private readonly messages = inject(MessageService);

  protected readonly mainNav = MAIN_NAV;
  /** Admin links are only rendered for admins (the routes are also guarded by roleGuard). */
  protected readonly adminNav = computed(() => (this.auth.currentUser()?.role === 'admin' ? ADMIN_NAV : []));
  protected readonly menuOpen = signal(false);

  constructor() {
    // Close the tablet/phone drawer after navigating.
    inject(Router)
      .events.pipe(
        filter((e) => e instanceof NavigationEnd),
        takeUntilDestroyed(),
      )
      .subscribe(() => this.menuOpen.set(false));
  }

  protected logout(): void {
    this.auth.logout();
    this.messages.add({ severity: 'info', summary: 'Logged out', detail: 'See you next time.' });
  }
}
