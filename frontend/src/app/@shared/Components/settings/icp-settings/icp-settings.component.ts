import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, FormArray } from '@angular/forms';
import { IcpSettingsService } from '../../../Services/icp-settings/icp-settings.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-icp-settings',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './icp-settings.component.html',
  styleUrls: ['./icp-settings.component.scss']
})
export class IcpSettingsComponent implements OnInit {
  icpForm: FormGroup;
  isNew = true;
  isLoading = true;

  // Predefined options
  ageRanges = [[0, 2], [3, 5], [6, 10], [11, 20], [21, 50], [51, 100]];
  employeeRanges = [[1, 5], [6, 15], [16, 20], [21, 50], [51, 100], [101, 200]];
  fundingStages = ['series_a', 'seed', 'pre_seed', 'grant', 'bootstrapped', 'series_b'];
  industryTiers = [
    ['fintech', 'ecommerce', 'saas', 'information technology'],
    ['healthtech', 'marketplace', 'insurtech'],
    ['education', 'government', 'manufacturing']
  ];
  geographyRegions = [
    { id: 'primary', label: 'Primary Targets (UK, Ireland, Netherlands, Germany)', countries: ['united kingdom', 'ireland', 'netherlands', 'germany'] },
    { id: 'eastern_eu', label: 'Eastern Europe Wedge', countries: ['albania', 'bulgaria', 'romania', 'poland', 'croatia', 'czech republic', 'hungary', 'slovakia', 'slovenia', 'estonia', 'latvia', 'lithuania', 'bosnia & herzegovina', 'kosovo', 'montenegro', 'north macedonia', 'serbia', 'ukraine', 'denmark', 'norway', 'finland', 'sweden'] },
    { id: 'north_america', label: 'North America', countries: ['united states', 'canada'] },
    { id: 'western_eu_rest', label: 'Rest of Western Europe', countries: ['france', 'spain', 'italy'] }
  ];

  constructor(
    private fb: FormBuilder,
    private icpService: IcpSettingsService,
    private router: Router
  ) {
    this.icpForm = this.fb.group({
      age_100: ['0,2'],
      age_70: ['3,5'],
      age_50: ['6,10'],
      age_30: ['11,20'],

      emp_100: ['6,15'],
      emp_80: ['1,5'],
      emp_70: ['16,20'],
      emp_40: ['21,50'],
      emp_20: ['51,100'],

      fund_100: ['series_a'],
      fund_90: ['seed'],
      fund_50: ['pre_seed'],
      fund_40: ['grant'],
      fund_30: ['bootstrapped'],
      fund_10: ['series_b'],

      // index of industryTiers
      ind_100: [this.industryTiers[0]],
      ind_70: [this.industryTiers[1]],
      ind_30: [this.industryTiers[2]],

      geo_100: ['primary'], // ID
      geo_85: ['eastern_eu'],
      geo_60: ['north_america'],
      geo_50: ['western_eu_rest'],

      keyword_100: [100],
      keyword_70: [70],
      keyword_30: [30]
    });
  }

  @Output() saved: EventEmitter<void> = new EventEmitter();

  ngOnInit() {
    this.icpService.getSettings().subscribe({
      next: (res: any) => {
        if (res && res.icp) {
          this.isNew = false;
          this.patchForm(res);
        }
        this.isLoading = false;
      },
      error: () => {
        this.isNew = true;
        this.isLoading = false;
      }
    });
  }

  patchForm(data: any) {
    // Reverse mapping from JSON to form can be complex, but for simplicity we rely on the defaults.
    // If we wanted to fully support editing an existing ICP, we would map the arrays back.
  }

  getRangeString(range: number[]) {
    return `${range[0]},${range[1]}`;
  }

  getIndustryString(tier: string[]) {
    return tier.join(', ');
  }

  onSubmit() {
    const v = this.icpForm.value;
    const parseRange = (val: string) => val.split(',').map(Number);
    
    const payload = {
      icp: {
        age: [
          [parseRange(v.age_100), 100],
          [parseRange(v.age_70), 70],
          [parseRange(v.age_50), 50],
          [parseRange(v.age_30), 30]
        ],
        employee_count: [
          [parseRange(v.emp_100), 100],
          [parseRange(v.emp_80), 80],
          [parseRange(v.emp_70), 70],
          [parseRange(v.emp_40), 40],
          [parseRange(v.emp_20), 20]
        ],
        funding_stage: {
          [v.fund_100]: 100,
          [v.fund_90]: 90,
          [v.fund_50]: 50,
          [v.fund_40]: 40,
          [v.fund_30]: 30,
          [v.fund_10]: 10
        },
        industry: {
          tier_1: [v.ind_100, 100],
          tier_2: [v.ind_70, 70],
          tier_3: [v.ind_30, 30]
        },
        geography: {
          primary: [this.geographyRegions.find(r => r.id === v.geo_100)?.countries, 100],
          tier_2: [this.geographyRegions.find(r => r.id === v.geo_85)?.countries, 85],
          tier_3: [this.geographyRegions.find(r => r.id === v.geo_60)?.countries, 60],
          tier_4: [this.geographyRegions.find(r => r.id === v.geo_50)?.countries, 50]
        },
        keywords: {
          outsourcing_terms: 100,
          remote_hiring_terms: 70,
          generic_terms: 30
        }
      },
      weights: {
        geography: 0.3,
        funding_stage: 0.2,
        employee_count: 0.15,
        age: 0.15,
        industry: 0.15,
        keywords: 0.05
      }
    };
    console.log('industry values:', {
      ind_100: v.ind_100,
      ind_70: v.ind_70,
      ind_30: v.ind_30
    });

console.log('payload:', JSON.stringify(payload, null, 2));
    console.log(JSON.stringify(payload, null, 2));
    const request = this.icpService.saveSettings(payload);

    request.subscribe({
      next: () => {
        // Notify parent that settings were saved so modal can be closed
        this.saved.emit();
      },
      error: (err: any) => {
        console.error(err);
        alert('Failed to save ICP settings');
      }
    });
  }
}
