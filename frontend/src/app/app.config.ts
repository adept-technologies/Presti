import { ApplicationConfig, provideZoneChangeDetection, APP_INITIALIZER } from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { provideHttpClient, withInterceptorsFromDi, HTTP_INTERCEPTORS } from '@angular/common/http';
import { AppConfigService } from './core/services/app-config.service';
import { provideAuth0, AuthHttpInterceptor, AuthClientConfig } from '@auth0/auth0-angular';

function initConfig(cfg: AppConfigService, authConfig: AuthClientConfig) {
  return () =>
    cfg.load().then(() => {
      authConfig.set({
        domain: 'dev-2685h5q7efjt6peh.us.auth0.com',
        clientId: 'zTRfFNkrnSE0gP5toS0ujcMHAM9wHUnA',
        useRefreshTokens: true,
        cacheLocation: 'localstorage',
        authorizationParams: {
          redirect_uri: window.location.origin,
          audience: 'https://api.presti',
          scope: 'openid profile email offline_access',
        },
        httpInterceptor: {
          allowedList: [
            {
              uri: `${cfg.apiUrl}/*`,
              tokenOptions: {
                authorizationParams: {
                  audience: 'https://api.presti',
                  scope: 'openid profile email offline_access',
                },
              },
            },
          ],
        },
      });
    });
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }), 
    provideRouter(routes), 
  
    provideHttpClient(withInterceptorsFromDi()),
    { provide: HTTP_INTERCEPTORS, useClass: AuthHttpInterceptor, multi: true },
    
    {
      provide: APP_INITIALIZER,
      useFactory: initConfig,
      deps: [AppConfigService, AuthClientConfig],
      multi: true
    },

    provideAuth0({
      domain: 'dev-2685h5q7efjt6peh.us.auth0.com',
      clientId: 'zTRfFNkrnSE0gP5toS0ujcMHAM9wHUnA',
      cacheLocation: 'localstorage',
      useRefreshTokens: true,
      authorizationParams: {
        redirect_uri: window.location.origin,
        audience: 'https://api.presti',
        scope: 'openid profile email offline_access'
      }
    }),
  ]
};