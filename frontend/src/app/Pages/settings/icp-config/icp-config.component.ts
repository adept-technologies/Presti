import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, FormArray, FormControl } from '@angular/forms';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-icp-config',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule],
    styles: [`
        :host {
            display: block;
            overflow-x: hidden;
            max-width: 100%;
        }
        .custom-select-container {
            position: relative;
            width: 100%;
            max-width: 100%;
        }
        .custom-select-trigger {
            width: 100%;
            padding: 10px 10px;
            border: 2px solid var(--border-color, #f9f9f9);
            background-color: var(--bg-filter, transparent);
            cursor: pointer;
            min-height: 38px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: var(--font-family-base, inherit);
            font-weight: var(--font-weight-header, normal);
            font-size: var(--font-size-header, 0.875rem);
            color: var(--text-primary);
            box-sizing: border-box;
            overflow: hidden;
        }
        .custom-select-trigger::after {
            content: "";
            display: inline-block;
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid var(--text-primary);
            margin-left: 8px;
            flex-shrink: 0;
        }
        .dropdown-text {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: block;
        }
        .custom-select-dropdown {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--bg-surface, #fff); /* Fallback for dark mode / light mode if vars missing */
            border: 1px solid #ccc;
            border-radius: 6px;
            margin-top: 4px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        /* Adjust for potential dark mode container */
        :host-context(body.dark-theme) .custom-select-dropdown {
            background: #1e1e1e;
            border-color: #333;
        }
        .custom-select-option {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            cursor: pointer;
            font-size: 0.875rem;
            color: var(--text-primary);
        }
        .custom-select-option:hover {
            background: rgba(0, 0, 0, 0.05);
        }
        :host-context(body.dark-theme) .custom-select-option:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        .custom-select-option input {
            margin-right: 8px;
            accent-color: var(--color-primary, #ffc107);
        }
        table {
            border: none !important;
            table-layout: fixed;
        }
        th, td {
            border: none !important;
            border-bottom: none !important;
        }
        tr:hover, td:hover {
            background-color: transparent !important;
        }
    `],
    template: `
    <div style="width:100%; margin: 0; padding: 24px; box-sizing: border-box; overflow-x: hidden;">
        <h2 style="color: var(--text-primary); font-size: 1.5rem; font-weight: 700; margin-bottom: 24px;">Configure ICP</h2>

        <form [formGroup]="form" (ngSubmit)="onSubmit()">
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; align-items: start;">
                
                <!-- Age -->
                <div style="background: var(--bg-surface, transparent); border-radius: 8px; padding: 16px;">
                    <div style="font-weight:600; font-size: 1.1rem; margin-bottom: 12px; color: var(--text-primary);">Age</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="color: var(--text-primary);">
                                <th style="padding: 8px; width: 60px;">Score</th>
                                <th style="padding: 8px;">Years</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr *ngFor="let c of ageControls">
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">{{c.label}}</td>
                                <td style="padding: 12px 8px;">
                                    <div class="custom-select-container" (mouseleave)="activeDropdown = null" style="width: 100%;">
                                        <div class="custom-select-trigger" (click)="toggleDropdown(c.control)">
                                            <span class="dropdown-text">{{ getSelectionLabel(c.control, allAges) }}</span>
                                        </div>
                                        <div class="custom-select-dropdown" *ngIf="activeDropdown === c.control">
                                            <label class="custom-select-option" *ngFor="let opt of allAges">
                                                <input type="checkbox" [checked]="isChecked(c.control, opt.value)" (change)="toggleSelection(c.control, opt.value)">
                                                {{opt.label}}
                                            </label>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Employee Count -->
                <div style="background: var(--bg-surface, transparent); border-radius: 8px; padding: 16px;">
                    <div style="font-weight:600; font-size: 1.1rem; margin-bottom: 12px; color: var(--text-primary);">Employee Count</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="color: var(--text-primary);">
                                <th style="padding: 8px; width: 60px;">Score</th>
                                <th style="padding: 8px;">Count</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr *ngFor="let c of employeeControls">
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">{{c.label}}</td>
                                <td style="padding: 12px 8px;">
                                    <div class="custom-select-container" (mouseleave)="activeDropdown = null" style="width: 100%;">
                                        <div class="custom-select-trigger" (click)="toggleDropdown(c.control)">
                                            <span class="dropdown-text">{{ getSelectionLabel(c.control, allEmployees) }}</span>
                                        </div>
                                        <div class="custom-select-dropdown" *ngIf="activeDropdown === c.control">
                                            <label class="custom-select-option" *ngFor="let opt of allEmployees">
                                                <input type="checkbox" [checked]="isChecked(c.control, opt.value)" (change)="toggleSelection(c.control, opt.value)">
                                                {{opt.label}}
                                            </label>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Funding Stage -->
                <div style="background: var(--bg-surface, transparent); border-radius: 8px; padding: 16px;">
                    <div style="font-weight:600; font-size: 1.1rem; margin-bottom: 12px; color: var(--text-primary);">Funding Stage</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="color: var(--text-primary);">
                                <th style="padding: 8px; width: 60px;">Score</th>
                                <th style="padding: 8px;">Stage</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr *ngFor="let c of fundingControls">
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">{{c.label}}</td>
                                <td style="padding: 12px 8px;">
                                    <div class="custom-select-container" (mouseleave)="activeDropdown = null" style="width: 100%;">
                                        <div class="custom-select-trigger" (click)="toggleDropdown(c.control)">
                                            <span class="dropdown-text">{{ getSelectionLabel(c.control, allFunding) }}</span>
                                        </div>
                                        <div class="custom-select-dropdown" *ngIf="activeDropdown === c.control">
                                            <label class="custom-select-option" *ngFor="let opt of allFunding">
                                                <input type="checkbox" [checked]="isChecked(c.control, opt.value)" (change)="toggleSelection(c.control, opt.value)">
                                                {{opt.label}}
                                            </label>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Industry -->
                <div style="background: var(--bg-surface, transparent); border-radius: 8px; padding: 16px;">
                    <div style="font-weight:600; font-size: 1.1rem; margin-bottom: 12px; color: var(--text-primary);">Industry</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="color: var(--text-primary);">
                                <th style="padding: 8px; width: 60px;">Score</th>
                                <th style="padding: 8px;">Industry</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr *ngFor="let c of industryControls">
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">{{c.label}}</td>
                                <td style="padding: 12px 8px;">
                                    <div class="custom-select-container" (mouseleave)="activeDropdown = null" style="width: 100%;">
                                        <div class="custom-select-trigger" (click)="toggleDropdown(c.control)">
                                            <span class="dropdown-text">{{ getSelectionLabel(c.control, allIndustries) }}</span>
                                        </div>
                                        <div class="custom-select-dropdown" *ngIf="activeDropdown === c.control">
                                            <label class="custom-select-option" *ngFor="let opt of allIndustries">
                                                <input type="checkbox" [checked]="isChecked(c.control, opt.value)" (change)="toggleSelection(c.control, opt.value)">
                                                {{opt.label}}
                                            </label>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Geography -->
                <div style="background: var(--bg-surface, transparent); border-radius: 8px; padding: 16px;">
                    <div style="font-weight:600; font-size: 1.1rem; margin-bottom: 12px; color: var(--text-primary);">Geography</div>

                    <!-- Primary Targets (Score 100) -->
                    <div style="font-weight:500; font-size: 0.9rem; margin-bottom: 8px; color: var(--text-primary); opacity: 0.7;">Primary Targets</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 16px;">
                        <thead>
                            <tr style="color: var(--text-primary);">
                                <th style="padding: 8px; width: 60px;">Score</th>
                                <th style="padding: 8px;">Country</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">100</td>
                                <td style="padding: 12px 8px;">
                                    <div class="custom-select-container" (mouseleave)="activeDropdown = null" style="width: 100%;">
                                        <div class="custom-select-trigger" (click)="toggleDropdown('geo_primary')">
                                            <span class="dropdown-text">{{ getSelectionLabel('geo_primary', primaryTargetCountries) }}</span>
                                        </div>
                                        <div class="custom-select-dropdown" *ngIf="activeDropdown === 'geo_primary'">
                                            <label class="custom-select-option" *ngFor="let opt of primaryTargetCountries">
                                                <input type="checkbox" [checked]="isChecked('geo_primary', opt.value)" (change)="toggleSelection('geo_primary', opt.value)">
                                                {{opt.label}}
                                            </label>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>

                    <!-- Regional Tiers (85, 60, 50) -->
                    <div style="font-weight:500; font-size: 0.9rem; margin-bottom: 8px; color: var(--text-primary); opacity: 0.7;">Regional Tiers</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="color: var(--text-primary);">
                                <th style="padding: 8px; width: 60px;">Score</th>
                                <th style="padding: 8px;">Region</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr *ngFor="let c of geographyRegionControls">
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">{{c.label}}</td>
                                <td style="padding: 12px 8px;">
                                    <div class="custom-select-container" (mouseleave)="activeDropdown = null" style="width: 100%;">
                                        <div class="custom-select-trigger" (click)="toggleDropdown(c.control)">
                                            <span class="dropdown-text">{{ getSelectionLabel(c.control, allRegions) }}</span>
                                        </div>
                                        <div class="custom-select-dropdown" *ngIf="activeDropdown === c.control">
                                            <label class="custom-select-option" *ngFor="let opt of allRegions">
                                                <input type="checkbox" [checked]="isChecked(c.control, opt.value)" (change)="toggleSelection(c.control, opt.value)">
                                                {{opt.label}}
                                            </label>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Keywords -->
                <div style="background: var(--bg-surface, transparent); border-radius: 8px; padding: 16px;">
                    <div style="font-weight:600; font-size: 1.1rem; margin-bottom: 12px; color: var(--text-primary);">Keywords</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="color: var(--text-primary);">
                                <th style="padding: 8px; width: 60px;">Score</th>
                                <th style="padding: 8px;">Terms</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr *ngFor="let c of keywordControls">
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">{{c.label}}</td>
                                <td style="padding: 12px 8px;">
                                    <div class="custom-select-container" (mouseleave)="activeDropdown = null" style="width: 100%;">
                                        <div class="custom-select-trigger" (click)="toggleDropdown(c.control)">
                                            <span class="dropdown-text">{{ getSelectionLabel(c.control, allKeywords) }}</span>
                                        </div>
                                        <div class="custom-select-dropdown" *ngIf="activeDropdown === c.control">
                                            <label class="custom-select-option" *ngFor="let opt of allKeywords">
                                                <input type="checkbox" [checked]="isChecked(c.control, opt.value)" (change)="toggleSelection(c.control, opt.value)">
                                                {{opt.label}}
                                            </label>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Weights -->
                <div style="background: var(--bg-surface, transparent); border-radius: 8px; padding: 16px;">
                    <div style="font-weight:600; font-size: 1.1rem; margin-bottom: 12px; color: var(--text-primary);">Weights (must add up to 1)</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="color: var(--text-primary);">
                                <th style="padding: 8px; width: 80px;">Feature</th>
                                <th style="padding: 8px;">Weight</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">Geography</td>
                                <td style="padding: 12px 8px;">
                                    <input formControlName="weight_geography" type="number" step="0.01" style="width:100%; padding:10px 10px; border:2px solid var(--border-color, #f9f9f9); background-color: var(--bg-filter, transparent); font-family: var(--font-family-base, inherit); font-weight: var(--font-weight-header, normal); font-size: var(--font-size-header, 0.875rem); color: var(--text-primary);" />
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">Funding</td>
                                <td style="padding: 12px 8px;">
                                    <input formControlName="weight_funding_stage" type="number" step="0.01" style="width:100%; padding:10px 10px; border:2px solid var(--border-color, #f9f9f9); background-color: var(--bg-filter, transparent); font-family: var(--font-family-base, inherit); font-weight: var(--font-weight-header, normal); font-size: var(--font-size-header, 0.875rem); color: var(--text-primary);" />
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">Employees</td>
                                <td style="padding: 12px 8px;">
                                    <input formControlName="weight_employee_count" type="number" step="0.01" style="width:100%; padding:10px 10px; border:2px solid var(--border-color, #f9f9f9); background-color: var(--bg-filter, transparent); font-family: var(--font-family-base, inherit); font-weight: var(--font-weight-header, normal); font-size: var(--font-size-header, 0.875rem); color: var(--text-primary);" />
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">Age</td>
                                <td style="padding: 12px 8px;">
                                    <input formControlName="weight_age" type="number" step="0.01" style="width:100%; padding:10px 10px; border:2px solid var(--border-color, #f9f9f9); background-color: var(--bg-filter, transparent); font-family: var(--font-family-base, inherit); font-weight: var(--font-weight-header, normal); font-size: var(--font-size-header, 0.875rem); color: var(--text-primary);" />
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">Industry</td>
                                <td style="padding: 12px 8px;">
                                    <input formControlName="weight_industry" type="number" step="0.01" style="width:100%; padding:10px 10px; border:2px solid var(--border-color, #f9f9f9); background-color: var(--bg-filter, transparent); font-family: var(--font-family-base, inherit); font-weight: var(--font-weight-header, normal); font-size: var(--font-size-header, 0.875rem); color: var(--text-primary);" />
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 12px 8px; font-weight: 500; color: var(--text-primary);">Keywords</td>
                                <td style="padding: 12px 8px;">
                                    <input formControlName="weight_keywords" type="number" step="0.01" style="width:100%; padding:10px 10px; border:2px solid var(--border-color, #f9f9f9); background-color: var(--bg-filter, transparent); font-family: var(--font-family-base, inherit); font-weight: var(--font-weight-header, normal); font-size: var(--font-size-header, 0.875rem); color: var(--text-primary);" />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div style="margin-top:32px; display:flex; gap:16px;">
                <button type="submit" style="padding:10px 24px; background:#ffc107; color:#000; font-weight: 600; border-radius:6px; border:none; cursor:pointer;">Save</button>
                <a routerLink="/settings" style="padding:10px 24px; background:transparent; color:var(--text-primary); border-radius:6px; border:1px solid var(--border-color, rgba(0,0,0,0.2)); text-decoration:none;">Back</a>
            </div>
        </form>
    </div>
    `
})
export class IcpConfigComponent {
    form: FormGroup;
    activeDropdown: string | null = null;

    allAges = [
        { label: '0-2', value: '0,2' },
        { label: '3-5', value: '3,5' },
        { label: '6-10', value: '6,10' },
        { label: '11-20', value: '11,20' }
    ];

    allEmployees = [
        { label: '1-5', value: '1,5' },
        { label: '6-15', value: '6,15' },
        { label: '16-20', value: '16,20' },
        { label: '21-50', value: '21,50' },
        { label: '51-100', value: '51,100' }
    ];

    allFunding = [
        { label: 'Bootstrapped', value: 'bootstrapped' },
        { label: 'Grant', value: 'grant' },
        { label: 'Pre-seed', value: 'pre_seed' },
        { label: 'Seed', value: 'seed' },
        { label: 'Series A', value: 'series_a' },
        { label: 'Series B', value: 'series_b' }
    ];

    allIndustries = [
        { label: 'Fintech', value: 'fintech' },
        { label: 'Ecommerce', value: 'ecommerce' },
        { label: 'SaaS', value: 'saas' },
        { label: 'Information Technology', value: 'information technology' },
        { label: 'Healthtech', value: 'healthtech' },
        { label: 'Marketplace', value: 'marketplace' },
        { label: 'Insurtech', value: 'insurtech' },
        { label: 'Education', value: 'education' },
        { label: 'Government', value: 'government' },
        { label: 'Manufacturing', value: 'manufacturing' },
    ];

    primaryTargetCountries = [
        { label: 'Netherlands', value: 'netherlands' },
        { label: 'Germany', value: 'germany' },
        { label: 'United Kingdom', value: 'united kingdom' },
        { label: 'Ireland', value: 'ireland' }
    ];

    allRegions = [
        { label: 'Eastern Europe', value: 'eastern_europe' },
        { label: 'North America', value: 'north_america' },
        { label: 'Western Europe', value: 'western_europe' }
    ];

    allKeywords = [
        { label: 'Outsourcing Terms e.g. contract, agency, outsource', value: 'outsourcing_terms' },
        { label: 'Remote Hiring Terms e.g. remote team, distributed', value: 'remote_hiring_terms' },
        { label: 'Generic Terms', value: 'generic_terms' }
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

    industryControls = [
        { label: '100', control: 'industry_100' },
        { label: '70', control: 'industry_70' },
        { label: '30', control: 'industry_30' }
    ];

    geographyRegionControls = [
        { label: '85', control: 'geo_eastern' },
        { label: '60', control: 'geo_na' },
        { label: '50', control: 'geo_west' }
    ];

    keywordControls = [
        { label: '100', control: 'kw_outsource' },
        { label: '70', control: 'kw_remote' },
        { label: '30', control: 'kw_generic' }
    ];

    constructor(private fb: FormBuilder) {
        this.form = this.fb.group({
            age_100: [['0,2']],
            age_70: [['3,5']],
            age_50: [['6,10']],
            age_30: [['11,20']],

            emp_100: [['6,15']],
            emp_80: [['1,5']],
            emp_70: [['16,20']],
            emp_40: [['21,50']],
            emp_20: [['51,100']],

            fund_100: [['series_a']],
            fund_90: [['seed']],
            fund_50: [['pre_seed']],
            fund_40: [['grant']],
            fund_30: [['bootstrapped']],
            fund_10: [['series_b']],

            industry_100: [['fintech']],
            industry_70: [['healthtech']],
            industry_30: [['education']],

            geo_primary: [['netherlands', 'germany', 'united kingdom', 'ireland']],
            geo_eastern: [['eastern_europe']],
            geo_na: [['north_america']],
            geo_west: [['western_europe']],

            kw_outsource: [['outsourcing_terms']],
            kw_remote: [['remote_hiring_terms']],
            kw_generic: [['generic_terms']],

            weight_geography: [0.30],
            weight_funding_stage: [0.20],
            weight_employee_count: [0.15],
            weight_age: [0.15],
            weight_industry: [0.15],
            weight_keywords: [0.05]
        });
    }

    toggleDropdown(controlName: string) {
        this.activeDropdown = this.activeDropdown === controlName ? null : controlName;
    }

    isChecked(controlName: string, value: string): boolean {
        const controlValue = this.form.get(controlName)?.value || [];
        return controlValue.includes(value);
    }

    toggleSelection(controlName: string, value: string) {
        const control = this.form.get(controlName);
        if (!control) return;

        const currentValues: string[] = control.value || [];
        let newValues: string[];

        if (currentValues.includes(value)) {
            newValues = currentValues.filter(v => v !== value);
        } else {
            newValues = [...currentValues, value];
        }

        control.setValue(newValues);
    }

    getSelectionLabel(controlName: string, options: {label: string, value: string}[]): string {
        const values: string[] = this.form.get(controlName)?.value || [];
        if (values.length === 0) return 'Select...';
        if (values.length === 1) {
            const opt = options.find(o => o.value === values[0]);
            return opt ? opt.label : values[0];
        }
        return `${values.length} selected`;
    }

    onSubmit() {
        console.log('ICP settings submitted', this.form.value);
        alert('ICP settings saved (local preview)');
    }
}

