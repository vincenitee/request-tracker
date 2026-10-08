import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter, TitleStrategy } from '@angular/router';
import Aura from '@primeuix/themes/aura';
import { ConfirmationService, MessageService } from 'primeng/api';
import { providePrimeNG } from 'primeng/config';
import { firstValueFrom } from 'rxjs';

import { routes } from './app.routes';
import { AuthService } from './core/auth/auth.service';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { AppTitleStrategy } from './core/title-strategy';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    // errorInterceptor is outermost, so it only sees errors that survive authInterceptor's 401 refresh/retry.
    provideHttpClient(withInterceptors([errorInterceptor, authInterceptor])),
    { provide: TitleStrategy, useClass: AppTitleStrategy },
    // PrimeNG 21 uses native CSS animations, so provideAnimationsAsync() is not needed.
    // Light mode only until something adds .app-dark to <html> (room for a theme toggle later).
    providePrimeNG({ theme: { preset: Aura, options: { darkModeSelector: '.app-dark' } } }),
    // App-wide so any component or service can raise toasts and confirmations; rendered once in app.html.
    MessageService,
    ConfirmationService,
    // Runs before the first navigation, so the guard already knows who is logged in after a reload.
    provideAppInitializer(() => firstValueFrom(inject(AuthService).restoreSession())),
  ],
};
