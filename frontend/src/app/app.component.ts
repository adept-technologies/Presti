import { Component, OnInit, OnDestroy, Renderer2 } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from './@shared/Components/navbar/navbar.component';
import { SettingsService } from './@shared/Services/settings.service';
import { ModalService } from './@shared/Services/modal.service';
import { Subscription } from 'rxjs';
import { NgIf, AsyncPipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from '@auth0/auth0-angular';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent, NgIf, AsyncPipe, RouterModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit, OnDestroy {
  title = 'Lead Gen';
  currentTheme = 'dark-theme'; // default
  lightTheme = 'light-theme';
  darkTheme = 'dark-theme';
  private settingsSub?: Subscription;
  modalVisible: any;
  modalPayload: any;

  constructor(
    private settingsService: SettingsService,
    private renderer: Renderer2,
    public auth: AuthService
    , private modalService: ModalService
  ) {
    this.settingsService.loadSettings();
    this.modalVisible = this.modalService.visible$;
    this.modalPayload = this.modalService.payload$;
    
  }

  ngOnInit() {
    this.settingsSub = this.settingsService.settings$.subscribe(settings => {
      const newTheme = settings.theme === 'light' ? this.lightTheme : this.darkTheme;
      this.applyTheme(newTheme);
    });
  }

  ngOnDestroy() {
    if (this.settingsSub) {
      this.settingsSub.unsubscribe();
    }
  }

  hideModal() {
    this.modalService.hide();
  }



  applyTheme(theme: string) {
    // Remove old class and apply new
    if (this.currentTheme !== theme) {
      this.renderer.removeClass(document.body, this.currentTheme);
    }
    this.renderer.addClass(document.body, theme);
    this.currentTheme = theme;
  }
}
