import { Component, OnInit } from '@angular/core';
import { AuthService } from '@auth0/auth0-angular';
import { NgIf } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [NgIf],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent implements OnInit {
  errorMessage: string | null = null;

  constructor(private auth: AuthService, private route: ActivatedRoute) {}

  ngOnInit(): void {
    // Check for error in query params
    this.route.queryParams.subscribe(params => {
      if (params['error_description']) {
        this.errorMessage = params['error_description'];
      } else if (params['error']) {
        this.errorMessage = "Access Denied. You do not have permission.";
      }
    });

    // Check for error in hash fragment just in case
    this.route.fragment.subscribe(fragment => {
      if (fragment && fragment.includes('error=')) {
        const params = new URLSearchParams(fragment);
        if (params.get('error_description')) {
          this.errorMessage = params.get('error_description');
        } else if (params.get('error')) {
          this.errorMessage = "Access Denied. You do not have permission.";
        }
      }
    });
  }

  login(): void {
    this.auth.loginWithRedirect({
      authorizationParams: {
        prompt: 'login'
      }
    });
  }
}
