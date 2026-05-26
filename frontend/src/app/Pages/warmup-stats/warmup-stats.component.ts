import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CompaniesService } from '../../@shared/Services/companies.service';

@Component({
  standalone: true,
  imports: [CommonModule],
  selector: 'app-warmup-stats',
  templateUrl: './warmup-stats.component.html',
  styleUrls: ['./warmup-stats.component.scss']
})
export class WarmupStatsComponent implements OnInit {

  private companiesService = inject(CompaniesService);
  public stats: any = null;

  private readonly EXCLUDED_DATES = ['2026-05-19', '2026-05-20'];

  get statsByDateReversed(): any[] {
    if (!this.stats?.stats_by_date) return [];
    return [...this.stats.stats_by_date]
      .filter((row: any) => !this.EXCLUDED_DATES.includes(row.date))
      .reverse();
  }

  ngOnInit(): void {
    this.loadStats();
  }

  loadStats() {
    this.companiesService.fetchWarmupStats().subscribe({
      next: (data) => {
        this.stats = data;
      },
      error: (err) => console.error('Failed to load warmup stats', err)
    });
  }
}
