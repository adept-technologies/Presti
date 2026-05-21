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
        if (!isPlatformBrowser(this.platformId)) {
            const serverApiUrl = (typeof process !== 'undefined' && process.env ? process.env['API_URL'] || process.env['SERVER_URL'] : null) || 'http://127.0.0.1:5050';
            this.config = { apiUrl: serverApiUrl };
            return Promise.resolve();
        }

        let configUrl = '/config';
        const hostname = window.location.hostname;
        const port = window.location.port;

        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            if (port !== '5050') {
                configUrl = 'http://127.0.0.1:5050/config';
            }
        }

        return firstValueFrom(
            this.http.get<{ apiUrl: string }>(configUrl),
        ).then((cfg) => {
            this.config = cfg;
        }).catch((err) => {
            console.error('Could not load configuration, using fallback API URL', err);
            this.config = { apiUrl: 'http://127.0.0.1:5050' };
        });
    }

    get apiUrl(): string {
        return this.config?.apiUrl || 'http://127.0.0.1:5050';
    }
}