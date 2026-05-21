import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AppConfigService } from '../../core/services/app-config.service';

@Injectable({
  providedIn: 'root'
})
export class UnsubscribeService {
  private appConfig = inject(AppConfigService);
  private get apiUrl(): string {
    return this.appConfig.apiUrl;
  }

  constructor(private http: HttpClient) {}

  unsubscribe(token: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/unsubscribe`, { token });
  }
}
