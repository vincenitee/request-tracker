import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import Aura from '@primeuix/themes/aura';
import { ConfirmationService, MessageService } from 'primeng/api';
import { providePrimeNG } from 'primeng/config';
import { firstValueFrom } from 'rxjs';

import { routes } from './app.routes';
import { AuthService } from './core/auth/auth.service';
import { authInterceptor } from './core/interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
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
