import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AppConfigService {
    private config: { apiUrl: string } | null = null;
    private http = inject(HttpClient);
    private platformId = inject(PLATFORM_ID);

    load(): Promise<void> {
        // SSR: no window available — use empty string (relative) as safe default
        if (!isPlatformBrowser(this.platformId)) {
            this.config = { apiUrl: '' };
            return Promise.resolve();
        }

        const hostname = window.location.hostname;
        const port = window.location.port;

        // Local dev: frontend runs on :4200, backend on :5050.
        // Inject the backend URL directly — no network call needed.
        if ((hostname === 'localhost' || hostname === '127.0.0.1') && port !== '5050') {
            this.config = { apiUrl: `http://${hostname}:5050` };
            return Promise.resolve();
        }

        // Production / staging: frontend & backend share the same origin.
        // /config returns "" (API_URL not set) → all API calls become relative paths.
        return firstValueFrom(
            this.http.get<{ apiUrl: string }>('/config'),
        ).then((cfg) => {
            // Treat missing or empty apiUrl as "use relative URLs"
            this.config = { apiUrl: cfg.apiUrl || '' };
        }).catch((err) => {
            console.error('Could not load /config, falling back to relative URLs', err);
            this.config = { apiUrl: '' };
        });
    }

    /** Empty string means "same origin" — services build relative URLs like /fetch-companies */
    get apiUrl(): string {
        return this.config?.apiUrl ?? '';
    }
}