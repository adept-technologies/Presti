import { Routes } from '@angular/router';
import { HomeComponent } from './Pages/home/home.component';
import { AnalyticsComponent } from './Pages/analytics/analytics.component';
import { WarmupStatsComponent } from './Pages/warmup-stats/warmup-stats.component';
import { LeadsTableComponent } from './@shared/Components/leads/leads.component';
import { LeadsPageComponent } from './Pages/leads-page/leads-page.component';
import { EventsComponent } from './Pages/events/events.component';
import { EngagementComponent } from './Pages/engagement/engagement.component';
import { SettingsComponent } from './@shared/Components/settings/settings.component';
import { LoginComponent } from './Pages/login/login.component';
import { customAuthGuard } from './core/guards/auth.guard';

export const routes: Routes = [
    {
        path: 'login',
        component: LoginComponent
    },
    {
        path: '',
        component: HomeComponent,
        pathMatch: 'full',
        canActivate: [customAuthGuard]
    },
    {
        path: 'analytics',
        component: AnalyticsComponent,
        canActivate: [customAuthGuard]
    },

    {
        path: 'warmup-stats',
        component: WarmupStatsComponent
    },

    {
        path: 'company/:id',
        loadComponent: () =>
            import('./@shared/Components/company-details/company-details.component').then(m => m.CompanyDetailsComponent),
        canActivate: [customAuthGuard]
    },

    {
        path: 'emails/:company_id',
        loadComponent: () =>
            import('./Pages/emails/emails.component').then(m => m.EmailsComponent),
        canActivate: [customAuthGuard]
    },

    {
        path: 'leads',
        component: LeadsPageComponent,
        canActivate: [customAuthGuard]
    },

    {
        path: 'events',
        component: EventsComponent,
        canActivate: [customAuthGuard]
    },

    {
        path: 'engagement',
        component: EngagementComponent,
        canActivate: [customAuthGuard]
    },

    {
        path: 'settings',
        component: SettingsComponent,
        canActivate: [customAuthGuard]
    },

    {
        path: 'unsubscribe',
        loadComponent: () =>
            import('./Pages/unsubscribe/unsubscribe.component').then(m => m.UnsubscribeComponent)
    },
];

