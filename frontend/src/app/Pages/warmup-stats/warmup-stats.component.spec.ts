import { ComponentFixture, TestBed } from '@angular/core/testing';
import { WarmupStatsComponent } from './warmup-stats.component';

describe('WarmupStatsComponent', () => {
  let component: WarmupStatsComponent;
  let fixture: ComponentFixture<WarmupStatsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WarmupStatsComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(WarmupStatsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
