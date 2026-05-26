import { Component, OnInit } from '@angular/core';
import { SearchBarComponent } from "../search-bar/search-bar.component";
import { RouterLink } from '@angular/router';
import { SearchService } from '../../Services/search.service';
import { MatIconModule } from '@angular/material/icon';
import { SettingsService } from '../../Services/settings.service';
import { AuthService } from '@auth0/auth0-angular';
import { AsyncPipe, NgIf } from '@angular/common';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [SearchBarComponent, RouterLink, MatIconModule, AsyncPipe, NgIf],
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.scss']
})
export class NavbarComponent implements OnInit {
  searchText: string = '';
  theme: string = 'dark';

  constructor(
    private searchService: SearchService,
    private settingsService: SettingsService,
    public auth: AuthService
  ) {}

  ngOnInit() {
    this.settingsService.settings$.subscribe(settings => {
      this.theme = settings.theme;
    });
  }

  toggleTheme() {
    const newTheme = this.theme === 'dark' ? 'light' : 'dark';
    this.settingsService.updateSettings({ theme: newTheme });
  }

  login() {
    this.auth.loginWithRedirect();
  }

  logout() {
    this.auth.logout({ logoutParams: { returnTo: document.location.origin } });
  }

  onSearchChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchText = input.value;
    this.searchService.setSearchTerm(this.searchText.trim());
  }
}
