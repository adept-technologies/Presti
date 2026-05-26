import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '@auth0/auth0-angular';
import { filter, map, switchMap } from 'rxjs/operators';

export const customAuthGuard = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  return auth.isLoading$.pipe(
    filter(loading => !loading), // Wait until Auth0 SDK is done loading
    switchMap(() => auth.isAuthenticated$),
    map(isAuthenticated => {
      if (isAuthenticated) {
        return true;
      } else {
        router.navigate(['/login']);
        return false;
      }
    })
  );
};
