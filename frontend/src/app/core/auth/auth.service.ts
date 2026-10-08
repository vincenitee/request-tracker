import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, map, Observable, of, switchMap, tap } from 'rxjs';

import { environment } from '../../../environments/environment';
import { TokenPair, User } from '../../shared/models/user.model';

const ACCESS_KEY = 'rt_access';
const REFRESH_KEY = 'rt_refresh';

// TODO(security): localStorage is readable by any script on the page (XSS risk).
// Production should keep tokens in httpOnly, Secure, SameSite cookies set by Django,
// or serve Angular and the API from one domain. See CLAUDE.md section 9.
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly apiUrl = environment.apiUrl;

  private readonly user = signal<User | null>(null);
  readonly currentUser = this.user.asReadonly();
  readonly isLoggedIn = computed(() => this.user() !== null);

  login(username: string, password: string): Observable<User> {
    return this.http
      .post<TokenPair>(`${this.apiUrl}/auth/token/`, { username, password })
      .pipe(
        tap((tokens) => this.storeTokens(tokens)),
        switchMap(() => this.loadMe()),
      );
  }

  logout(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    this.user.set(null);
    this.router.navigate(['/login']);
  }

  /** Exchanges the refresh token for a new access token and returns it. */
  refresh(): Observable<string> {
    return this.http
      .post<{ access: string }>(`${this.apiUrl}/auth/token/refresh/`, {
        refresh: this.getRefreshToken(),
      })
      .pipe(
        map((res) => res.access),
        tap((access) => localStorage.setItem(ACCESS_KEY, access)),
      );
  }

  loadMe(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/me/`).pipe(tap((user) => this.user.set(user)));
  }

  /** Runs once at app start: restores the session after a page reload. Never fails. */
  restoreSession(): Observable<unknown> {
    if (!this.getAccessToken()) {
      return of(null);
    }
    return this.loadMe().pipe(catchError(() => of(null)));
  }

  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  private storeTokens(tokens: TokenPair): void {
    localStorage.setItem(ACCESS_KEY, tokens.access);
    localStorage.setItem(REFRESH_KEY, tokens.refresh);
  }
}
