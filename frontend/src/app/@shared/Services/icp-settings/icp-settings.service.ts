import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AppConfigService } from '../../../core/services/app-config.service';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class IcpSettingsService {

  private http = inject(HttpClient);
  private appConfig = inject(AppConfigService);

  private get baseUrl(): string {
    return `${this.appConfig.apiUrl}/settings/icp`;
  }

  getSettings(): Observable<any> {
    return this.http.get<any>(this.baseUrl);
  }

  saveSettings(data: any, name: string = 'Default', settingId?: number): Observable<any> {
    return this.http.put<any>(this.baseUrl, {
      "icp": data,
      "name": name,
      "setting_id": settingId
    });
  }

  deleteSetting(settingId: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/${settingId}`);
  }

  activateSetting(settingId: number): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/${settingId}/activate`, {});
  }
}
