import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';

export interface ModalPayload {
  type: string; // e.g., 'icp'
  data?: any;
}

@Injectable({ providedIn: 'root' })
export class ModalService {
  private _visible$ = new BehaviorSubject<boolean>(false);
  private _payload$ = new BehaviorSubject<ModalPayload | null>(null);
  private _saved$ = new Subject<void>();

  get visible$(): Observable<boolean> { return this._visible$.asObservable(); }
  get payload$(): Observable<ModalPayload | null> { return this._payload$.asObservable(); }
  get saved$(): Observable<void> { return this._saved$.asObservable(); }

  show(payload: ModalPayload) {
    this._payload$.next(payload);
    this._visible$.next(true);
  }

  hide() {
    this._visible$.next(false);
    this._payload$.next(null);
  }

  notifySaved() {
    this._saved$.next();
  }
}
