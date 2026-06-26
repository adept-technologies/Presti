import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Chart, registerables } from 'chart.js';
import { Subscription } from 'rxjs';
import { CompaniesService } from '../../@shared/Services/companies.service';
import { SettingsService } from '../../@shared/Services/settings.service';

Chart.register(...registerables);

// ─── Tab type ─────────────────────────────────────────────────────────────────
type Tab = 'overview' | 'pipeline' | 'icp' | 'people' | 'outreach' | 'geographic';

// ─── Chart colour palettes ────────────────────────────────────────────────────
const PALETTE = [
  '#3b82f6', '#a855f7', '#22c55e', '#facc15', '#f97316',
  '#ef4444', '#06b6d4', '#84cc16', '#ec4899', '#8b5cf6',
  '#14b8a6', '#fb923c', '#f43f5e', '#a3e635', '#38bdf8',
];

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule, DecimalPipe],
  selector: 'app-analytics',
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.scss'],
})
export class AnalyticsComponent implements OnInit, OnDestroy {

  private companiesService = inject(CompaniesService);
  private settingsService = inject(SettingsService);
  private themeSub?: Subscription;

  // ── State ──────────────────────────────────────────────────────────────────
  metrics: any = null;
  activeTab: Tab = 'overview';
  startDate: string = '';
  endDate: string = '';
  private charts: Chart[] = [];

  // ── Computed rate helpers ───────────────────────────────────────────────────
  get openRate():     string { return this.rate('opened'); }
  get clickRate():    string { return this.rate('clicked'); }
  get replyRate():    string { return this.rate('replied'); }
  get positiveRate(): string { return this.rate('positive_replies'); }

  private rate(field: string): string {
    const kpis = this.metrics?.outreach_kpis;
    if (!kpis || !kpis.total_sent) return '0.0';
    return ((kpis[field] / kpis.total_sent) * 100).toFixed(1);
  }

  // ── Theme helper ────────────────────────────────────────────────────────────
  private getChartOptions() {
    const isLight = document.body.classList.contains('light-theme');
    const textColor = isLight ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255, 255, 255, 0.6)';
    const gridColor = isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.07)';
    const legendColor = isLight ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.7)';

    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: legendColor, font: { family: 'Inter', size: 11 } } },
      },
      scales: {
        x: { ticks: { color: textColor, font: { family: 'Inter' } }, grid: { color: gridColor } },
        y: { ticks: { color: textColor, font: { family: 'Inter' } }, grid: { color: gridColor } },
      },
    };
  }

  // ── Lifecycle ───────────────────────────────────────────────────────────────
  ngOnInit(): void {
    this.loadMetrics();
    this.themeSub = this.settingsService.settings$.subscribe(() => {
      if (this.metrics) {
        setTimeout(() => this.renderTabCharts(), 50);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroyCharts();
    if (this.themeSub) {
      this.themeSub.unsubscribe();
    }
  }

  // ── Tab navigation ──────────────────────────────────────────────────────────
  setTab(tab: Tab): void {
    this.activeTab = tab;
    // Destroy only the charts for the previous tab before re-rendering new ones
    this.destroyCharts();
    setTimeout(() => this.renderTabCharts(), 80);
  }

  // ── Date filter ─────────────────────────────────────────────────────────────
  applyDateFilter(): void { this.loadMetrics(); }

  resetDateFilter(): void {
    this.startDate = '';
    this.endDate = '';
    this.loadMetrics();
  }

  // ── Data loading ────────────────────────────────────────────────────────────
  loadMetrics(): void {
    const sd = this.startDate || undefined;
    const ed = this.endDate   || undefined;

    this.companiesService.fetchEngagementMetrics(sd, ed).subscribe({
      next: (data) => {
        this.metrics = data;
        setTimeout(() => this.renderTabCharts(), 100);
      },
      error: (err) => console.error('Failed to load metrics', err),
    });
  }

  // ── Chart orchestration ─────────────────────────────────────────────────────
  private renderTabCharts(): void {
    this.destroyCharts();
    switch (this.activeTab) {
      case 'overview':   this.renderOverview();   break;
      case 'pipeline':   this.renderPipeline();   break;
      case 'icp':        this.renderICP();         break;
      case 'people':     this.renderPeople();      break;
      case 'outreach':   this.renderOutreach();    break;
      case 'geographic': this.renderGeographic();  break;
    }
  }

  private destroyCharts(): void {
    this.charts.forEach(c => c.destroy());
    this.charts = [];
  }

  private push(chart: Chart | null): void {
    if (chart) this.charts.push(chart);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // TAB: OVERVIEW
  // ─────────────────────────────────────────────────────────────────────────────
  private renderOverview(): void {
    this.push(this.renderPipelineOverTime('pipelineTimeChart'));
    this.push(this.renderFunnelChart('funnelChart'));
    this.push(this.renderServiceTractionChart('serviceTractionChart'));
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // TAB: PIPELINE
  // ─────────────────────────────────────────────────────────────────────────────
  private renderPipeline(): void {
    this.push(this.renderFunnelChart('funnelChartPipeline'));
    this.push(this.renderSizeMetrics());
    this.push(this.renderFundingChart());
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // TAB: ICP INTELLIGENCE
  // ─────────────────────────────────────────────────────────────────────────────
  private renderICP(): void {
    this.push(this.renderICPDistribution());
    this.push(this.renderICPRadar());
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // TAB: PEOPLE
  // ─────────────────────────────────────────────────────────────────────────────
  private renderPeople(): void {
    this.push(this.renderSeniorityChart());
    this.push(this.renderDeptChart());
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // TAB: OUTREACH
  // ─────────────────────────────────────────────────────────────────────────────
  private renderOutreach(): void {
    this.push(this.renderEngagementBreakdown());
    this.push(this.renderSequenceChart());
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // TAB: GEOGRAPHIC
  // ─────────────────────────────────────────────────────────────────────────────
  private renderGeographic(): void {
    this.push(this.renderGeoChart());
    this.push(this.renderIndustryChart());
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // INDIVIDUAL CHART RENDERERS
  // ═══════════════════════════════════════════════════════════════════════════

  /** Pipeline growth over time (area line) */
  private renderPipelineOverTime(canvasId: string): Chart | null {
    const ctx = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!ctx || !this.metrics?.pipeline_over_time?.length) return null;

    const data = this.metrics.pipeline_over_time;
    const options = this.getChartOptions();
    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map((d: any) => d.month),
        datasets: [{
          label: 'New Leads',
          data: data.map((d: any) => d.new_leads),
          borderColor: '#facc15',
          backgroundColor: 'rgba(250, 204, 21, 0.12)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointBackgroundColor: '#facc15',
          pointRadius: 4,
        }],
      },
      options: {
        ...options,
        plugins: { ...options.plugins, legend: { display: false } },
      },
    });
  }

  /** Lead lifecycle funnel (horizontal bar) */
  private renderFunnelChart(canvasId: string): Chart | null {
    const ctx = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!ctx || !this.metrics?.lifecycle) return null;

    const stageOrder = ['uncontacted', 'contacted', 'opened', 'engaged', 'replied', 'opted_out', 'failed', 'pending'];
    const stageColors: Record<string, string> = {
      uncontacted: '#64748b', contacted: '#3b82f6', opened: '#a855f7',
      engaged: '#22c55e', replied: '#facc15', opted_out: '#f97316',
      failed: '#ef4444', pending: '#94a3b8',
    };
    const data = this.metrics.lifecycle;
    const labels = stageOrder.filter(s => data[s] !== undefined);
    const values = labels.map(l => data[l]);
    const colors = labels.map(l => stageColors[l] || '#94a3b8');

    const options = this.getChartOptions();
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels.map(l => l.toUpperCase().replace('_', ' ')),
        datasets: [{ label: 'Leads', data: values, backgroundColor: colors, borderRadius: 4 }],
      },
      options: {
        ...options,
        indexAxis: 'y',
        plugins: { ...options.plugins, legend: { display: false } },
      },
    });
  }

  /** Service traction (grouped bar) */
  private renderServiceTractionChart(canvasId: string): Chart | null {
    const ctx = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!ctx || !this.metrics?.service_traction?.length) return null;

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this.metrics.service_traction.map((s: any) => s.service),
        datasets: [
          { label: 'Total Leads', data: this.metrics.service_traction.map((s: any) => s.count), backgroundColor: 'rgba(59,130,246,0.6)', borderRadius: 4 },
          { label: 'Replies',     data: this.metrics.service_traction.map((s: any) => s.replies), backgroundColor: '#facc15', borderRadius: 4 },
        ],
      },
      options: this.getChartOptions(),
    });
  }

  /** Company size vs response rate (line) */
  private renderSizeMetrics(): Chart | null {
    const ctx = document.getElementById('sizeMetricsChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.size_metrics?.length) return null;

    const data = this.metrics.size_metrics;
    const order = ['1-10', '11-50', '51-200', '200+'];
    const sorted = [...data].sort((a: any, b: any) => order.indexOf(a.size_range) - order.indexOf(b.size_range));

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sorted.map((s: any) => s.size_range + ' employees'),
        datasets: [
          { label: 'Total', data: sorted.map((s: any) => s.total), backgroundColor: 'rgba(59,130,246,0.5)', borderRadius: 4 },
          { label: 'Replies', data: sorted.map((s: any) => s.replies), backgroundColor: '#22c55e', borderRadius: 4 },
        ],
      },
      options: this.getChartOptions(),
    });
  }

  /** Funding stage breakdown */
  private renderFundingChart(): Chart | null {
    const ctx = document.getElementById('fundingChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.funding_breakdown?.length) return null;

    const data = this.metrics.funding_breakdown;
    const options = this.getChartOptions();
    const isLight = document.body.classList.contains('light-theme');
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map((d: any) => d.stage),
        datasets: [
          { label: 'Leads', data: data.map((d: any) => d.total), backgroundColor: PALETTE.slice(0, data.length), borderRadius: 4 },
          { label: 'Avg ICP Score', data: data.map((d: any) => d.avg_icp), backgroundColor: 'rgba(250,204,21,0.15)', borderColor: '#facc15', borderWidth: 1.5, borderRadius: 4, type: 'line' as any, yAxisID: 'y1', tension: 0.4 },
        ],
      },
      options: {
        ...options,
        scales: {
          ...options.scales,
          y1: {
            position: 'right' as const,
            ticks: { color: isLight ? 'rgba(15, 23, 42, 0.5)' : 'rgba(255,255,255,0.5)' },
            grid: { drawOnChartArea: false }
          },
        },
      },
    });
  }

  /** ICP score distribution (bucketed bar) */
  private renderICPDistribution(): Chart | null {
    const ctx = document.getElementById('icpDistChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.icp_score_distribution?.length) return null;

    const data = this.metrics.icp_score_distribution;
    const bucketColors: Record<string, string> = {
      '0-20': '#ef4444', '20-40': '#f97316', '40-60': '#eab308', '60-80': '#22c55e', '80-100': '#3b82f6',
    };
    const options = this.getChartOptions();
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map((d: any) => d.bucket),
        datasets: [{
          label: 'Companies',
          data: data.map((d: any) => d.count),
          backgroundColor: data.map((d: any) => bucketColors[d.bucket] || '#94a3b8'),
          borderRadius: 6,
        }],
      },
      options: {
        ...options,
        plugins: { ...options.plugins, legend: { display: false } },
      },
    });
  }

  /** ICP sub-score radar */
  private renderICPRadar(): Chart | null {
    const ctx = document.getElementById('icpRadarChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.icp_subscores) return null;

    const s = this.metrics.icp_subscores;
    const isLight = document.body.classList.contains('light-theme');
    return new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['Geography', 'Funding Stage', 'Employee Count', 'Company Age', 'Industry', 'Keywords', 'Contactability'],
        datasets: [{
          label: 'Avg Sub-Score',
          data: [s.avg_geography, s.avg_funding, s.avg_employee, s.avg_age, s.avg_industry, s.avg_keyword, s.avg_contactability],
          backgroundColor: 'rgba(250, 204, 21, 0.15)',
          borderColor: '#facc15',
          borderWidth: 2,
          pointBackgroundColor: '#facc15',
          pointRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: { color: isLight ? 'rgba(15, 23, 42, 0.5)' : 'rgba(255,255,255,0.5)', backdropColor: 'transparent', stepSize: 25 },
            grid:         { color: isLight ? 'rgba(15, 23, 42, 0.1)' : 'rgba(255,255,255,0.1)' },
            angleLines:   { color: isLight ? 'rgba(15, 23, 42, 0.1)' : 'rgba(255,255,255,0.1)' },
            pointLabels:  { color: isLight ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255,255,255,0.7)', font: { family: 'Inter', size: 11 } },
          },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  /** Seniority doughnut */
  private renderSeniorityChart(): Chart | null {
    const ctx = document.getElementById('seniorityChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.people_seniority?.length) return null;

    const data = this.metrics.people_seniority;
    const isLight = document.body.classList.contains('light-theme');
    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map((d: any) => d.seniority),
        datasets: [{ data: data.map((d: any) => d.count), backgroundColor: PALETTE, hoverOffset: 6 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: { legend: { position: 'right', labels: { color: isLight ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255,255,255,0.7)', font: { family: 'Inter', size: 11 }, boxWidth: 12 } } },
      },
    });
  }

  /** Departments horizontal bar */
  private renderDeptChart(): Chart | null {
    const ctx = document.getElementById('deptChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.people_departments?.length) return null;

    const data = this.metrics.people_departments;
    const options = this.getChartOptions();
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map((d: any) => d.department),
        datasets: [{ label: 'People', data: data.map((d: any) => d.count), backgroundColor: PALETTE.slice(0, data.length), borderRadius: 4 }],
      },
      options: {
        ...options,
        indexAxis: 'y',
        plugins: { ...options.plugins, legend: { display: false } },
      },
    });
  }

  /** Engagement breakdown doughnut */
  private renderEngagementBreakdown(): Chart | null {
    const ctx = document.getElementById('breakdownChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.outreach_kpis) return null;

    const kpis = this.metrics.outreach_kpis;
    const isLight = document.body.classList.contains('light-theme');
    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Opened', 'Engaged (Clicked)', 'Replied', 'Positive Reply', 'Unsubscribed', 'Bounced'],
        datasets: [{
          data: [kpis.opened, kpis.clicked, kpis.replied, kpis.positive_replies, kpis.unsubscribed, kpis.bounced],
          backgroundColor: ['#3b82f6', '#a855f7', '#22c55e', '#facc15', '#f97316', '#ef4444'],
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '55%',
        plugins: { legend: { position: 'bottom', labels: { color: isLight ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255,255,255,0.7)', font: { family: 'Inter', size: 11 }, boxWidth: 12 } } },
      },
    });
  }

  /** Email sequence performance (grouped bar) */
  private renderSequenceChart(): Chart | null {
    const ctx = document.getElementById('sequenceChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.sequence_performance?.length) return null;

    const data = this.metrics.sequence_performance;
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map((d: any) => `Seq #${d.sequence_number}`),
        datasets: [
          { label: 'Sent', data: data.map((d: any) => d.total_sent), backgroundColor: 'rgba(59,130,246,0.55)', borderRadius: 4 },
          { label: 'Replies', data: data.map((d: any) => d.replies), backgroundColor: '#facc15', borderRadius: 4 },
        ],
      },
      options: this.getChartOptions(),
    });
  }

  /** Geo breakdown horizontal bar */
  private renderGeoChart(): Chart | null {
    const ctx = document.getElementById('geoChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.geo_breakdown?.length) return null;

    const data = this.metrics.geo_breakdown;
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map((d: any) => d.country),
        datasets: [
          { label: 'Leads',   data: data.map((d: any) => d.total),   backgroundColor: 'rgba(59,130,246,0.55)', borderRadius: 4 },
          { label: 'Replies', data: data.map((d: any) => d.replies), backgroundColor: '#22c55e', borderRadius: 4 },
        ],
      },
      options: {
        ...this.getChartOptions(),
        indexAxis: 'y',
      },
    });
  }

  /** Industry breakdown horizontal bar */
  private renderIndustryChart(): Chart | null {
    const ctx = document.getElementById('industryChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.industry_breakdown?.length) return null;

    const data = this.metrics.industry_breakdown;
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map((d: any) => d.industry),
        datasets: [
          { label: 'Leads',   data: data.map((d: any) => d.total),   backgroundColor: PALETTE.slice(0, data.length), borderRadius: 4 },
          { label: 'Replies', data: data.map((d: any) => d.replies), backgroundColor: 'rgba(250,204,21,0.6)', borderRadius: 4 },
        ],
      },
      options: {
        ...this.getChartOptions(),
        indexAxis: 'y',
      },
    });
  }
}
