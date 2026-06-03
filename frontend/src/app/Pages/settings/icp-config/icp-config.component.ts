import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-icp-config',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule],
    template: `
    <div style="width:100%; margin: 0; padding: 24px;">
        <h2 style="color: var(--text-primary); font-size: 1.5rem; font-weight: 700; margin-bottom: 12px;">Configure ICP</h2>

        <form [formGroup]="form" (ngSubmit)="onSubmit()" style="margin-top: 8px;">
            <!-- Age -->
            <div style="display:flex; align-items:center; gap:16px;">
                <div style="flex:0 0 120px; font-weight:600;">Age</div>
                <div style="flex:1 1 auto; display:flex; gap:12px; align-items:center; flex-wrap:nowrap; overflow-x:auto;">
                    <ng-container *ngFor="let c of ageControls">
                        <div style="display:flex; flex-direction:column; align-items:flex-start; flex:1 1 0; min-width:140px;">
                            <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">{{c.label}}</small>
                            <select [formControlName]="c.control" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                                <option *ngFor="let opt of ageOptions" [value]="opt.value">{{opt.label}}</option>
                            </select>
                        </div>
                    </ng-container>
                </div>
            </div>

            <!-- Employee Count -->
            <div style="margin-top:18px; display:flex; align-items:center; gap:16px;">
                <div style="flex:0 0 120px; font-weight:600;">Employee Count</div>
                <div style="flex:1 1 auto; display:flex; gap:12px; align-items:center; flex-wrap:nowrap; overflow-x:auto;">
                    <ng-container *ngFor="let c of employeeControls">
                        <div style="display:flex; flex-direction:column; align-items:flex-start; flex:1 1 0; min-width:140px;">
                            <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">{{c.label}}</small>
                            <select [formControlName]="c.control" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                                <option *ngFor="let opt of employeeOptions" [value]="opt.value">{{opt.label}}</option>
                            </select>
                        </div>
                    </ng-container>
                </div>
            </div>

            <!-- Funding Stage -->
            <div style="margin-top:18px; display:flex; align-items:center; gap:16px;">
                <div style="flex:0 0 120px; font-weight:600;">Funding Stage</div>
                <div style="flex:1 1 auto; display:flex; gap:12px; align-items:center; flex-wrap:nowrap; overflow-x:auto;">
                    <ng-container *ngFor="let c of fundingControls">
                        <div style="display:flex; flex-direction:column; align-items:flex-start; flex:1 1 0; min-width:140px;">
                            <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">{{c.label}}</small>
                            <select [formControlName]="c.control" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                                <option *ngFor="let opt of fundingOptions" [value]="opt.value">{{opt.label}}</option>
                            </select>
                        </div>
                    </ng-container>
                </div>
            </div>

            <!-- Industry -->
            <div style="margin-top:18px; display:flex; align-items:center; gap:16px;">
                <div style="flex:0 0 120px; font-weight:600;">Industry</div>
                <div style="flex:1 1 auto; display:flex; gap:12px; align-items:center; flex-wrap:nowrap; overflow-x:auto;">
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:140px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Tier 1 (100)</small>
                        <select formControlName="industry_100" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of industryTier1Options" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:140px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Tier 2 (70)</small>
                        <select formControlName="industry_70" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of industryTier2Options" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:140px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Tier 3 (30)</small>
                        <select formControlName="industry_30" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of industryTier3Options" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Geography -->
            <div style="margin-top:18px; display:flex; align-items:center; gap:16px;">
                <div style="flex:0 0 120px; font-weight:600;">Geography</div>
                <div style="flex:1 1 auto; display:flex; gap:12px; align-items:center; flex-wrap:nowrap; overflow-x:auto;">
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:140px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Primary (100)</small>
                        <select formControlName="geo_primary" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of geographyPrimaryOptions" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:140px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Eastern EU (85)</small>
                        <select formControlName="geo_eastern" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of geographyEasternOptions" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:140px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">North America (60)</small>
                        <select formControlName="geo_na" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of geographyNorthAmericaOptions" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:140px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Western EU (50)</small>
                        <select formControlName="geo_west" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of geographyWesternOptions" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Keywords -->
            <div style="margin-top:18px; display:flex; align-items:center; gap:16px;">
                <div style="flex:0 0 120px; font-weight:600;">Keywords</div>
                <div style="flex:1 1 auto; display:flex; gap:12px; align-items:center; flex-wrap:nowrap; overflow-x:auto;">
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:180px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Outsourcing (100)</small>
                        <select formControlName="kw_outsource" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of keywordsOutsourcingOptions" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:180px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Remote hiring (70)</small>
                        <select formControlName="kw_remote" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of keywordsRemoteOptions" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                    <div style="display:flex; flex-direction:column; flex:1 1 0; min-width:180px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Generic (30)</small>
                        <select formControlName="kw_generic" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;">
                            <option *ngFor="let opt of keywordsGenericOptions" [value]="opt.value">{{opt.label}}</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Weights -->
            <div style="margin-top:18px; display:flex; gap:16px; align-items:center;">
                <div style="flex:0 0 120px; font-weight:600;">Weights</div>
                <div style="flex:1 1 auto; display:flex; gap:12px; align-items:center; flex-wrap:nowrap; overflow-x:auto;">
                    <div style="display:flex; flex-direction:column; min-width:120px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Geography</small>
                        <input formControlName="weight_geography" type="number" step="0.01" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;" />
                    </div>
                    <div style="display:flex; flex-direction:column; min-width:120px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Funding</small>
                        <input formControlName="weight_funding_stage" type="number" step="0.01" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;" />
                    </div>
                    <div style="display:flex; flex-direction:column; min-width:120px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Employees</small>
                        <input formControlName="weight_employee_count" type="number" step="0.01" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;" />
                    </div>
                    <div style="display:flex; flex-direction:column; min-width:120px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Age</small>
                        <input formControlName="weight_age" type="number" step="0.01" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;" />
                    </div>
                    <div style="display:flex; flex-direction:column; min-width:120px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Industry</small>
                        <input formControlName="weight_industry" type="number" step="0.01" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;" />
                    </div>
                    <div style="display:flex; flex-direction:column; min-width:120px;">
                        <small style="font-size:0.75rem; color: rgba(0,0,0,0.6); margin-bottom:6px;">Keywords</small>
                        <input formControlName="weight_keywords" type="number" step="0.01" style="width:100%; padding:8px; border-radius:6px; border:1px solid #ccc;" />
                    </div>
                </div>
            </div>

            <div style="margin-top:18px; display:flex; gap:8px;">
                <button type="submit" style="padding:8px 14px; background:var(--color-primary); color:white; border-radius:6px; border:none;">Save</button>
                <a routerLink="/settings" style="padding:8px 14px; background:transparent; color:var(--text-primary); border-radius:6px; border:1px solid rgba(0,0,0,0.08); text-decoration:none;">Back</a>
            </div>
        </form>
    </div>
    `
})
export class IcpConfigComponent {
    form: FormGroup;

    ageOptions = [
        { label: '0-2', value: '0,2' },
        { label: '3-5', value: '3,5' },
        { label: '6-10', value: '6,10' },
        { label: '11-20', value: '11,20' }
    ];

    employeeOptions = [
        { label: '6-15', value: '6,15' },
        { label: '1-5', value: '1,5' },
        { label: '16-20', value: '16,20' },
        { label: '21-50', value: '21,50' },
        { label: '51-100', value: '51,100' }
    ];

    fundingOptions = [
        { label: 'series_a', value: 'series_a' },
        { label: 'seed', value: 'seed' },
        { label: 'pre_seed', value: 'pre_seed' },
        { label: 'grant', value: 'grant' },
        { label: 'bootstrapped', value: 'bootstrapped' },
        { label: 'series_b', value: 'series_b' }
    ];

    industryTier1Options = [
        { label: 'fintech', value: 'fintech' },
        { label: 'ecommerce', value: 'ecommerce' },
        { label: 'saas', value: 'saas' },
        { label: 'information technology', value: 'information technology' },
    ];

    industryTier2Options = [
        { label: 'healthtech', value: 'healthtech' },
        { label: 'marketplace', value: 'marketplace' },
        { label: 'insurtech', value: 'insurtech' },
    ];

    industryTier3Options = [
        { label: 'education', value: 'education' },
        { label: 'government', value: 'government' },
        { label: 'manufacturing', value: 'manufacturing' },
    ];

    geographyPrimaryOptions = [
        { label: 'United Kingdom', value: 'united kingdom' },
        { label: 'Ireland', value: 'ireland' },
        { label: 'Netherlands', value: 'netherlands' },
        { label: 'Germany', value: 'germany' }
    ];

    geographyEasternOptions = [
        { label: 'Poland', value: 'poland' },
        { label: 'Romania', value: 'romania' },
        { label: 'Czech Republic', value: 'czech republic' }
    ];

    geographyNorthAmericaOptions = [
        { label: 'United States', value: 'united states' },
        { label: 'Canada', value: 'canada' }
    ];

    geographyWesternOptions = [
        { label: 'France', value: 'france' },
        { label: 'Spain', value: 'spain' }
    ];

    keywordsOutsourcingOptions = [
        { label: 'contract', value: 'contract' },
        { label: 'agency', value: 'agency' },
        { label: 'outsource', value: 'outsource' }
    ];

    keywordsRemoteOptions = [
        { label: 'remote team', value: 'remote team' },
        { label: 'distributed', value: 'distributed' }
    ];

    keywordsGenericOptions = [
        { label: 'hiring', value: 'hiring' },
        { label: 'talent', value: 'talent' }
    ];

    ageControls = [
        { label: '100', control: 'age_100' },
        { label: '70', control: 'age_70' },
        { label: '50', control: 'age_50' },
        { label: '30', control: 'age_30' }
    ];

    employeeControls = [
        { label: '100', control: 'emp_100' },
        { label: '80', control: 'emp_80' },
        { label: '70', control: 'emp_70' },
        { label: '40', control: 'emp_40' },
        { label: '20', control: 'emp_20' }
    ];

    fundingControls = [
        { label: '100', control: 'fund_100' },
        { label: '90', control: 'fund_90' },
        { label: '50', control: 'fund_50' },
        { label: '40', control: 'fund_40' },
        { label: '30', control: 'fund_30' },
        { label: '10', control: 'fund_10' }
    ];

    constructor(private fb: FormBuilder) {
        this.form = this.fb.group({
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

            industry_100: ['fintech'],
            industry_70: ['healthtech'],
            industry_30: ['education'],

            geo_primary: ['united kingdom'],
            geo_eastern: ['poland'],
            geo_na: ['united states'],
            geo_west: ['france'],

            kw_outsource: ['contract'],
            kw_remote: ['remote team'],
            kw_generic: ['hiring'],

            weight_geography: [0.30],
            weight_funding_stage: [0.20],
            weight_employee_count: [0.15],
            weight_age: [0.15],
            weight_industry: [0.15],
            weight_keywords: [0.05]
        });
    }

    onSubmit() {
        console.log('ICP settings submitted', this.form.value);
        alert('ICP settings saved (local preview)');
    }
}
