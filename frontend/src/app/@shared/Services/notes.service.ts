import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { AppConfigService } from '../../core/services/app-config.service';
import { INote } from '../../Libs/interfaces/note.interface';

@Injectable({
    providedIn: 'root'
})
export class NotesService {
    private appConfig = inject(AppConfigService);
    private get backend_url(): string {
        return this.appConfig.apiUrl;
    }
    private http = inject(HttpClient);

    saveNote(companyId: number, note: string): Observable<INote> {
        return this.http.post<INote>(`${this.backend_url}/save-note/${companyId}`, { note });
    }

    deleteNote(noteId: string): Observable<any> {
        return this.http.delete(`${this.backend_url}/delete-note/${noteId}`);
    }
}
