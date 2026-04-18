# Telemetry Data — EDEN Mars Greenhouse

Simulated sensor telemetry for the EDEN Martian greenhouse dashboard. Represents Raspberry Pi sensor readings after Mars transformation.

## Files

### `sensor-baseline.json`
Baseline nominal readings for all three zones and system metrics. Use this as the "reference" values for threshold calculations and gauge displays. Each zone has 9 sensor fields; system has 9 fields.

**Dashboard usage:** Initialize gauges, set nominal range indicators, populate "current reading" cards when no timeseries is active.

### `timeseries-nominal.json`
24 hours of nominal operation. 144 data points at 10-minute intervals (06:00 sol start to 05:50 next sol). Shows natural diurnal variation:
- Temperature follows solar curve with ~1h lag
- Humidity inversely correlates with temperature
- Solar output traces a sinusoidal bell curve (peak at solar noon)
- Water reserve shows consumption/desal production balance
- CO2 rises at night when photosynthesis stops
- Sensor noise of +/-0.1-0.5 on all readings

**Dashboard usage:** Powers the 24h chart view, sparklines, and "normal day" demo mode. Animate by stepping through readings at 100-500ms intervals.

### `timeseries-cme-crisis.json`
Full CME (coronal mass ejection) event sequence. 144 data points across ~216 mission hours with variable time resolution. Four phases:

| Phase | Hours | Points | Key Changes |
|-------|-------|--------|-------------|
| `nominal` | 0-2 | 4 | Green state, all nominal |
| `stockpiling` | 2-50 | 32 | Water 340->580L, battery climbing, desal at max |
| `crisis` | 50-170 | 80 | Solar at 30%, radiation spike to 260+ uSv/hr, water draining, temp dropping |
| `recovery` | 170-216 | 28 | Solar returning, radiation decaying, systems normalizing |

Each data point includes `phase`, `status` (green/yellow/orange/red), and `alert` fields for UI state management.

**Dashboard usage:** Powers the CME demo scenario. Use `phase` field to drive UI state (background color, alert banners). Use `status` field for overall health indicator. Animate at 200-1000ms per point.

### `crop-states.json`
Per-crop growth state for all 6 crops across 3 zones. Includes BBCH growth stage codes, companion planting relationships, water/light needs, and health status.

**Dashboard usage:** Populate crop cards, growth stage indicators, and the companion planting relationship diagram. The `status` field ("nominal" or "watch") drives alert highlighting.

## Zone Layout

| Zone | Crops | Temp Profile | Notes |
|------|-------|-------------|-------|
| `protein` | Soybean, Lentil | 20-24°C | N-fixing legumes, moderate humidity |
| `carb` | Potato, Wheat | 18-22°C | Starch crops, lower humidity preferred |
| `vitamin` | Tomato, Spinach | 22-26°C | High light demand, higher humidity |

## System Parameters

- **Dome pressure:** 500 hPa (half Earth sea level)
- **Outside:** avg -62°C, 750 Pa, 7-8 m/s wind
- **Water reserve:** ~500L nominal, desalination at 120 L/sol peak
- **Solar:** 4.2 kW max, battery backup
- **Radiation:** 0.67 uSv/hr nominal (dome shielded), 250+ during CME
