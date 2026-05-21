import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { IEvent } from '../../Libs/interfaces/event.interface';
import { AppConfigService } from '../../core/services/app-config.service';

@Injectable({
  providedIn: 'root'
})
export class EventService {
  private appConfig = inject(AppConfigService);
  private get backend_url(): string {
    return this.appConfig.apiUrl;
  }

  private http = inject(HttpClient);

  events(): Observable<IEvent[]> {
    console.log("Fetching events from backend...");
    return this.http.get<IEvent[]>(`${this.backend_url}/events`);
  }
}
