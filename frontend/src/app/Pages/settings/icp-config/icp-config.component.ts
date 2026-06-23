import { Component, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ButtonComponent } from '../../../@shared/Components/button/button.component';
import { IcpSettingsService } from '../../../@shared/Services/icp-settings/icp-settings.service';

@Component({
    selector: 'app-icp-config',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule, ButtonComponent],
    templateUrl: './icp-config.component.html',
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
            background: var(--bg-surface, #fff);
            border: 1px solid #ccc;
            border-radius: 6px;
            margin-top: 4px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
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
        :host-context(body.dark-theme) .custom-select-trigger,
        :host-context(body.dark-theme) .custom-select-option,
        :host-context(body.dark-theme) .dropdown-text {
            color: #ffffff;
        }
        :host-context(body:not(.dark-theme)) .custom-select-trigger,
        :host-context(body:not(.dark-theme)) .custom-select-option,
        :host-context(body:not(.dark-theme)) .dropdown-text {
            color: #000000;
        }
        :host-context(body.dark-theme) select,
        :host-context(body.dark-theme) .custom-select-container select {
            color: #ffffff;
        }
        :host-context(body:not(.dark-theme)) select,
        :host-context(body:not(.dark-theme)) .custom-select-container select {
            color: #000000;
        }
        :host-context(body.dark-theme) input[type="number"] {
            color: #ffffff;
        }
        :host-context(body:not(.dark-theme)) input[type="number"] {
            color: #000000;
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
    `]
})
export class IcpConfigComponent implements OnInit {

    form: FormGroup;
    activeDropdown: string | null = null;

    allSettings: any[] = [];
    activeSettingId: number | null = null;
    activeSettingName: string = 'Default';

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
        { label: 'Eastern Europe', value: 'eastern_eu_wedge' },
        { label: 'North America', value: 'north_america' },
        { label: 'Western Europe', value: 'western_eu_rest' }
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

    constructor(private fb: FormBuilder, private icpService: IcpSettingsService) {
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

            industry_100: [['fintech', 'ecommerce', 'saas']],
            industry_70: [['healthtech']],
            industry_30: [['education']],

            geo_primary: [['netherlands', 'germany', 'united kingdom', 'ireland']],
            geo_eastern: [['eastern_eu_wedge']],
            geo_na: [['north_america']],
            geo_west: [['western_eu_rest']],

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

    ngOnInit() {
        this.loadSettings();
    }

    loadSettings() {
        this.icpService.getSettings().subscribe({
            next: (res) => {
                console.log('Loaded ICP settings', res);
                this.allSettings = res?.all_settings || [];
                this.activeSettingId = res?.active_id || null;
                this.activeSettingName = res?.active_name || 'Default';

                const icp = res?.icp;
                if (!icp || Object.keys(icp).length === 0) {
                    this.form.reset({
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

                        industry_100: ['fintech', 'ecommerce', 'saas'],
                        industry_70: ['healthtech'],
                        industry_30: ['education'],

                        geo_primary: ['netherlands', 'germany', 'united kingdom', 'ireland'],
                        geo_eastern: ['eastern_eu_wedge'],
                        geo_na: ['north_america'],
                        geo_west: ['western_eu_rest'],

                        kw_outsource: ['outsourcing_terms'],
                        kw_remote: ['remote_hiring_terms'],
                        kw_generic: ['generic_terms'],

                        weight_geography: 0.30,
                        weight_funding_stage: 0.20,
                        weight_employee_count: 0.15,
                        weight_age: 0.15,
                        weight_industry: 0.15,
                        weight_keywords: 0.05
                    });
                    return;
                }

                const patch: any = {};

                // --- Age: backend format is [[[min, max], score], ...]
                if (Array.isArray(icp.age)) {
                    icp.age.forEach(([range, score]: [[number, number], number]) => {
                        const key = `${range[0]},${range[1]}`;
                        const controlMap: Record<number, string> = { 100: 'age_100', 70: 'age_70', 50: 'age_50', 30: 'age_30' };
                        const ctrl = controlMap[score];
                        if (ctrl) patch[ctrl] = [key];
                    });
                }

                // --- Employee Count: backend format is [[[min, max], score], ...]
                if (Array.isArray(icp.employee_count)) {
                    icp.employee_count.forEach(([range, score]: [[number, number], number]) => {
                        const key = `${range[0]},${range[1]}`;
                        const controlMap: Record<number, string> = {
                            100: 'emp_100', 80: 'emp_80', 70: 'emp_70', 40: 'emp_40', 20: 'emp_20'
                        };
                        const ctrl = controlMap[score];
                        if (ctrl) patch[ctrl] = [key];
                    });
                }

                // --- Funding Stage: backend format is { stage_name: score, ... }
                if (icp.funding_stage && typeof icp.funding_stage === 'object') {
                    const fundingByScore: Record<number, string[]> = {};
                    Object.entries(icp.funding_stage).forEach(([stage, score]) => {
                        const s = score as number;
                        if (!fundingByScore[s]) fundingByScore[s] = [];
                        fundingByScore[s].push(stage);
                    });
                    const fundingControlMap: Record<number, string> = {
                        100: 'fund_100', 90: 'fund_90', 50: 'fund_50',
                        40: 'fund_40', 30: 'fund_30', 10: 'fund_10'
                    };
                    Object.entries(fundingByScore).forEach(([score, stages]) => {
                        const ctrl = fundingControlMap[Number(score)];
                        if (ctrl) patch[ctrl] = stages;
                    });
                }

                // --- Industry: backend format is [[[industry1, industry2, ...], score], ...]
                if (Array.isArray(icp.industry)) {
                    icp.industry.forEach(([industries, score]: [string[], number]) => {
                        const controlMap: Record<number, string> = { 100: 'industry_100', 70: 'industry_70', 30: 'industry_30' };
                        const ctrl = controlMap[score];
                        if (ctrl) patch[ctrl] = industries;
                    });
                }

                // --- Geography: primary is [[countries], score], rest are flat key:score
                if (icp.geography) {
                    const geo = icp.geography;
                    if (Array.isArray(geo.primary)) {
                        // format: [[country1, country2, ...], score]
                        patch['geo_primary'] = geo.primary[0];
                    }
                    // Regional tiers are stored by their backend key name directly
                    if (geo.eastern_eu_wedge !== undefined) patch['geo_eastern'] = ['eastern_eu_wedge'];
                    if (geo.north_america !== undefined)     patch['geo_na']      = ['north_america'];
                    if (geo.western_eu_rest !== undefined)   patch['geo_west']    = ['western_eu_rest'];
                }

                // --- Keywords: backend format is { keyword_group: score, ... }
                if (icp.keywords && typeof icp.keywords === 'object') {
                    const kwByScore: Record<number, string[]> = {};
                    Object.entries(icp.keywords).forEach(([kw, score]) => {
                        const s = score as number;
                        if (!kwByScore[s]) kwByScore[s] = [];
                        kwByScore[s].push(kw);
                    });
                    const kwControlMap: Record<number, string> = {
                        100: 'kw_outsource', 70: 'kw_remote', 30: 'kw_generic'
                    };
                    Object.entries(kwByScore).forEach(([score, kws]) => {
                        const ctrl = kwControlMap[Number(score)];
                        if (ctrl) patch[ctrl] = kws;
                    });
                }

                // --- Weights
                if (icp.weights) {
                    patch['weight_geography']     = icp.weights.geography     ?? 0.30;
                    patch['weight_funding_stage'] = icp.weights.funding_stage ?? 0.20;
                    patch['weight_employee_count']= icp.weights.employee_count?? 0.15;
                    patch['weight_age']           = icp.weights.age           ?? 0.15;
                    patch['weight_industry']      = icp.weights.industry       ?? 0.15;
                    patch['weight_keywords']      = icp.weights.keywords       ?? 0.05;
                }

                this.form.patchValue(patch);
            },
            error: (err) => console.error('Failed to load ICP settings', err)
        });
    }

    onSettingSelected(event: Event) {
        const select = event.target as HTMLSelectElement;
        const id = Number(select.value);
        if (!id) return;
        this.icpService.activateSetting(id).subscribe({
            next: () => {
                console.log(`Activated setting ${id}`);
                this.loadSettings();
            },
            error: (err) => {
                console.error('Failed to activate setting', err);
                alert('Failed to activate setting');
            }
        });
    }

    onNewSetting() {
        const name = prompt('Enter a name for the new ICP profile:');
        if (!name || !name.trim()) return;

        const payload = this.buildPayload();
        this.icpService.saveSettings(payload, name.trim()).subscribe({
            next: (res: any) => {
                alert('New ICP profile created!');
                this.loadSettings();
            },
            error: (err) => {
                console.error('Failed to create setting', err);
                alert('Failed to create setting');
            }
        });
    }

    onDeleteSetting() {
        if (!this.activeSettingId) return;
        if (!confirm(`Are you sure you want to delete the profile "${this.activeSettingName}"?`)) return;

        this.icpService.deleteSetting(this.activeSettingId).subscribe({
            next: () => {
                alert('ICP profile deleted!');
                this.loadSettings();
            },
            error: (err) => {
                console.error('Failed to delete setting', err);
                alert('Failed to delete setting');
            }
        });
    }

    @HostListener('document:click', ['$event'])
    onDocumentClick(event: MouseEvent) {
        const target = event.target as HTMLElement;
        if (!target.closest('.custom-select-container')) {
            this.activeDropdown = null;
        }
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

    buildPayload() {
        const f = this.form.value;
        const parseRange = (v: string) => v.split(',').map(Number);

        return {
            age: [
                [parseRange(f.age_100[0]), 100],
                [parseRange(f.age_70[0]),  70],
                [parseRange(f.age_50[0]),  50],
                [parseRange(f.age_30[0]),  30],
            ],
            employee_count: [
                [parseRange(f.emp_100[0]), 100],
                [parseRange(f.emp_80[0]),  80],
                [parseRange(f.emp_70[0]),  70],
                [parseRange(f.emp_40[0]),  40],
                [parseRange(f.emp_20[0]),  20],
            ],
            funding_stage: {
                ...f.fund_100.reduce((acc: any, v: string) => ({ ...acc, [v]: 100 }), {}),
                ...f.fund_90.reduce((acc: any, v: string) => ({ ...acc, [v]: 90  }), {}),
                ...f.fund_50.reduce((acc: any, v: string) => ({ ...acc, [v]: 50  }), {}),
                ...f.fund_40.reduce((acc: any, v: string) => ({ ...acc, [v]: 40  }), {}),
                ...f.fund_30.reduce((acc: any, v: string) => ({ ...acc, [v]: 30  }), {}),
                ...f.fund_10.reduce((acc: any, v: string) => ({ ...acc, [v]: 10  }), {}),
            },
            industry: [
                [f.industry_100, 100],
                [f.industry_70,  70],
                [f.industry_30,  30],
            ],
            geography: {
                primary:          [f.geo_primary, 100],
                eastern_eu_wedge: 85,
                north_america:    60,
                western_eu_rest:  50,
            },
            keywords: {
                ...f.kw_outsource.reduce((acc: any, v: string) => ({ ...acc, [v]: 100 }), {}),
                ...f.kw_remote.reduce((acc: any, v: string)    => ({ ...acc, [v]: 70  }), {}),
                ...f.kw_generic.reduce((acc: any, v: string)   => ({ ...acc, [v]: 30  }), {}),
            },
            weights: {
                geography:      f.weight_geography,
                funding_stage:  f.weight_funding_stage,
                employee_count: f.weight_employee_count,
                age:            f.weight_age,
                industry:       f.weight_industry,
                keywords:       f.weight_keywords,
            }
        };
    }

    saveICPSettings() {
        const payload = this.buildPayload();
        console.log('Saving ICP payload', payload);
        this.icpService.saveSettings(payload, this.activeSettingName, this.activeSettingId || undefined).subscribe({
            next: () => alert('ICP settings saved!'),
            error: (err) => alert(`Failed to save ICP settings: ${err}`)
        });
    }
}
