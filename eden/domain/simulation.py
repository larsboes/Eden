"""EDEN Virtual Farming Lab — Monte Carlo crop simulation engine.

Layer 3: The Dreamer. Real math, not LLM text generation.
Deterministic reproducibility: same seed = same numbers, every time.

Models: GDD thermal time, Liebig's Law stress, VPD-based disease,
DLI-based light, stage-aware radiation, per-crop transpiration,
closed-loop water recovery, nutritional output.

PURE PYTHON. Zero external imports. Only stdlib. THIS IS THE LAW.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


# ── Crop Simulation Parameters ──────────────────────────────────────────


@dataclass(frozen=True)
class CropSimParams:
    """Per-crop simulation parameters. Sourced from Syngenta KB + CEA data."""

    name: str
    zone_id: str
    area_m2: float

    # Thermal time (GDD)
    base_temp_c: float
    optimal_temp_min_c: float
    optimal_temp_max_c: float
    gdd_maturity: float

    # Root zone
    root_zone_optimal_min_c: float
    root_zone_optimal_max_c: float

    # Light (DLI)
    dli_optimal: float          # mol/m2/day
    photoperiod_hours: float

    # VPD target (kPa)
    vpd_target_min: float
    vpd_target_max: float

    # Transpiration rates by stage name -> L/m2/day
    transpiration_rates: dict

    # Yield
    max_growth_rate: float      # kg/m2/day theoretical max biomass
    harvest_index: float        # edible fraction of total biomass
    yield_kg_per_m2: float      # reference yield under optimal

    # Nutrition
    calories_per_kg: float
    protein_per_kg: float

    # Stress
    radiation_tolerance: float          # 1.0 = Earth normal UV-B
    is_bolting_sensitive: bool
    tuberization_temp_max: float | None  # potato: 25C root zone max


# ── Default crop library (from crop-cea-data.json + CropProfile) ────────


CROP_LIBRARY: dict[str, CropSimParams] = {
    "soybean": CropSimParams(
        name="soybean", zone_id="protein", area_m2=20.0,
        base_temp_c=10, optimal_temp_min_c=20, optimal_temp_max_c=30, gdd_maturity=1800,
        root_zone_optimal_min_c=22, root_zone_optimal_max_c=26,
        dli_optimal=30.0, photoperiod_hours=16,
        vpd_target_min=0.8, vpd_target_max=1.2,
        transpiration_rates={"seedling": 1.0, "vegetative": 2.1, "flowering": 3.2, "maturation": 2.8},
        max_growth_rate=0.004, harvest_index=0.45, yield_kg_per_m2=0.3,
        calories_per_kg=446, protein_per_kg=36,
        radiation_tolerance=1.0, is_bolting_sensitive=False, tuberization_temp_max=None,
    ),
    "potato": CropSimParams(
        name="potato", zone_id="carb", area_m2=20.0,
        base_temp_c=5, optimal_temp_min_c=15, optimal_temp_max_c=22, gdd_maturity=1500,
        root_zone_optimal_min_c=15, root_zone_optimal_max_c=20,
        dli_optimal=25.0, photoperiod_hours=14,
        vpd_target_min=0.6, vpd_target_max=1.0,
        transpiration_rates={"seedling": 1.2, "vegetative": 2.5, "tuber_bulking": 4.5, "senescence": 1.5},
        max_growth_rate=0.050, harvest_index=0.80, yield_kg_per_m2=4.0,
        calories_per_kg=77, protein_per_kg=2,
        radiation_tolerance=1.5, is_bolting_sensitive=False, tuberization_temp_max=25.0,
    ),
    "wheat": CropSimParams(
        name="wheat", zone_id="carb", area_m2=10.0,
        base_temp_c=5, optimal_temp_min_c=15, optimal_temp_max_c=25, gdd_maturity=2000,
        root_zone_optimal_min_c=18, root_zone_optimal_max_c=22,
        dli_optimal=35.0, photoperiod_hours=16,
        vpd_target_min=0.8, vpd_target_max=1.2,
        transpiration_rates={"seedling": 1.0, "vegetative": 2.0, "heading": 3.5, "grain_fill": 3.0, "senescence": 1.0},
        max_growth_rate=0.006, harvest_index=0.42, yield_kg_per_m2=0.5,
        calories_per_kg=339, protein_per_kg=13,
        radiation_tolerance=0.9, is_bolting_sensitive=False, tuberization_temp_max=None,
    ),
    "tomato": CropSimParams(
        name="tomato", zone_id="vitamin", area_m2=15.0,
        base_temp_c=10, optimal_temp_min_c=20, optimal_temp_max_c=28, gdd_maturity=1200,
        root_zone_optimal_min_c=20, root_zone_optimal_max_c=25,
        dli_optimal=30.0, photoperiod_hours=16,
        vpd_target_min=0.8, vpd_target_max=1.2,
        transpiration_rates={"seedling": 1.2, "vegetative": 2.5, "flowering": 4.5, "ripening": 3.0},
        max_growth_rate=0.100, harvest_index=0.60, yield_kg_per_m2=8.0,
        calories_per_kg=18, protein_per_kg=0.9,
        radiation_tolerance=1.2, is_bolting_sensitive=False, tuberization_temp_max=None,
    ),
    "spinach": CropSimParams(
        name="spinach", zone_id="vitamin", area_m2=10.0,
        base_temp_c=5, optimal_temp_min_c=15, optimal_temp_max_c=22, gdd_maturity=600,
        root_zone_optimal_min_c=14, root_zone_optimal_max_c=20,
        dli_optimal=17.0, photoperiod_hours=12,
        vpd_target_min=0.5, vpd_target_max=0.8,
        transpiration_rates={"seedling": 0.6, "active_growth": 2.5, "harvest": 2.0},
        max_growth_rate=0.050, harvest_index=0.90, yield_kg_per_m2=2.0,
        calories_per_kg=23, protein_per_kg=2.9,
        radiation_tolerance=1.2, is_bolting_sensitive=True, tuberization_temp_max=None,
    ),
    "lettuce": CropSimParams(
        name="lettuce", zone_id="vitamin", area_m2=10.0,
        base_temp_c=5, optimal_temp_min_c=15, optimal_temp_max_c=22, gdd_maturity=500,
        root_zone_optimal_min_c=16, root_zone_optimal_max_c=22,
        dli_optimal=14.0, photoperiod_hours=14,
        vpd_target_min=0.5, vpd_target_max=0.8,
        transpiration_rates={"seedling": 0.6, "heading": 2.5, "mature": 2.0},
        max_growth_rate=0.040, harvest_index=0.85, yield_kg_per_m2=1.5,
        calories_per_kg=15, protein_per_kg=1.4,
        radiation_tolerance=1.2, is_bolting_sensitive=True, tuberization_temp_max=None,
    ),
}


# ── Environmental Physics ───────────────────────────────────────────────


def vpd(temp_c: float, rh_pct: float) -> float:
    """Vapor Pressure Deficit (kPa). THE metric for CEA management."""
    svp = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))  # Tetens
    return svp * (1.0 - rh_pct / 100.0)


def compute_dli(ppfd_umol: float, photoperiod_hours: float) -> float:
    """Daily Light Integral: mol/m2/day from PPFD and photoperiod."""
    return ppfd_umol * photoperiod_hours * 0.0036


def root_zone_temp(air_temp: float, cooling_active: bool = True) -> float:
    """Root zone: typically 2-5C below air in hydroponic/aeroponic systems."""
    return air_temp + (-3.0 if cooling_active else -1.0)


# ── Stress Functions ────────────────────────────────────────────────────


def temperature_stress(temp: float, opt_min: float, opt_max: float) -> float:
    """Trapezoidal response: 1.0 in optimal range, linear decay outside."""
    if opt_min <= temp <= opt_max:
        return 1.0
    if temp < opt_min:
        return max(0.0, 1.0 - (opt_min - temp) / 10.0)
    return max(0.0, 1.0 - (temp - opt_max) / 10.0)


def water_stress(water_available_l: float, water_demand_l: float) -> float:
    """Ratio model: actual / required."""
    if water_demand_l <= 0:
        return 1.0
    return min(1.0, max(0.0, water_available_l / water_demand_l))


def light_stress_dli(actual_dli: float, optimal_dli: float) -> float:
    """Light response using DLI (mol/m2/day)."""
    if optimal_dli <= 0:
        return 1.0
    ratio = actual_dli / optimal_dli
    if ratio >= 2.0:
        return max(0.7, 2.5 - ratio)  # mild photoinhibition only at extreme excess
    if ratio >= 1.0:
        return 1.0
    return max(0.0, ratio)


def disease_stress_vpd(temp: float, rh: float, vpd_min: float) -> float:
    """Fungal pressure via VPD. Low VPD = wet leaf = pathogen risk."""
    current = vpd(temp, rh)
    if current >= vpd_min:
        return 1.0
    deficit = (vpd_min - current) / vpd_min
    return max(0.0, 1.0 - deficit * 0.4)


# Radiation sensitivity by growth stage (flowering = CRITICAL)
_RADIATION_STAGE_SENSITIVITY: list[tuple[float, float, float]] = [
    (0.0, 0.2, 0.6),   # seedling: moderate
    (0.2, 0.5, 0.3),   # vegetative: low
    (0.5, 0.8, 1.5),   # flowering/anthesis: CRITICAL (BBCH 60-69)
    (0.8, 1.0, 0.5),   # maturation/grain fill: moderate
]


def radiation_stress(rad_level: float, tolerance: float, growth_stage: float) -> float:
    """UV-B damage with BBCH-derived stage sensitivity."""
    stage_mult = 1.0
    for lo, hi, mult in _RADIATION_STAGE_SENSITIVITY:
        if lo <= growth_stage < hi:
            stage_mult = mult
            break
    effective = rad_level * stage_mult
    if effective <= tolerance:
        return 1.0
    excess = (effective - tolerance) / tolerance
    # Softer curve: crops degrade but don't die instantly in one day
    return max(0.10, 1.0 - excess * 0.25)


def bolting_stress(root_temp: float, photoperiod_h: float, sensitive: bool) -> float:
    """Spinach/lettuce bolt risk: high root temp + long photoperiod."""
    if not sensitive:
        return 1.0
    if root_temp > 22.0 and photoperiod_h > 12.0:
        return 0.3  # 70% loss from premature bolting
    return 1.0


def tuberization_factor(root_temp: float, max_temp: float | None) -> float:
    """Potato tuber initiation stops above threshold root zone temp."""
    if max_temp is None:
        return 1.0
    if root_temp > max_temp:
        return 0.0
    if root_temp > max_temp - 5.0:
        return (max_temp - root_temp) / 5.0
    return 1.0


# ── Transpiration Lookup ────────────────────────────────────────────────


def _get_transpiration_rate(rates: dict, growth_stage: float) -> float:
    """Look up transpiration rate from per-crop stage dict by growth_stage 0-1."""
    keys = list(rates.keys())
    n = len(keys)
    if n == 0:
        return 2.0  # fallback
    idx = min(int(growth_stage * n), n - 1)
    return rates[keys[idx]]


# ── Single Day Simulation ───────────────────────────────────────────────


@dataclass
class DayState:
    """State snapshot for one simulation day."""
    day: int
    gdd_accumulated: float
    growth_stage: float
    biomass_kg: float
    water_consumed_l: float
    stress_factor: float
    alive: bool


def simulate_crop_day(
    crop: CropSimParams,
    prev: DayState,
    air_temp: float,
    rh_pct: float,
    ppfd_umol: float,
    water_available_l: float,
    radiation_level: float,
) -> DayState:
    """Advance one crop by one day. Pure math, no side effects."""
    if not prev.alive:
        return DayState(
            day=prev.day + 1, gdd_accumulated=prev.gdd_accumulated,
            growth_stage=prev.growth_stage, biomass_kg=prev.biomass_kg,
            water_consumed_l=prev.water_consumed_l, stress_factor=0.0, alive=False,
        )

    # Thermal time accumulation (GDD)
    gdd_today = max(0.0, air_temp - crop.base_temp_c)
    gdd_total = prev.gdd_accumulated + gdd_today
    growth_stage = min(1.0, gdd_total / crop.gdd_maturity) if crop.gdd_maturity > 0 else 1.0

    # Compute environmental metrics
    rz_temp = root_zone_temp(air_temp)
    actual_dli = compute_dli(ppfd_umol, crop.photoperiod_hours)

    # Water demand: transpiration is CIRCULATION in closed system, 95% recovered.
    # Net consumption = 5% of transpiration. Stress = can the system circulate enough?
    daily_transpiration = _get_transpiration_rate(crop.transpiration_rates, growth_stage)
    water_circulation_need = daily_transpiration * crop.area_m2
    # Water available for circulation = supply + reserve buffer
    # Crop is stressed only if system can't provide enough flow
    net_water_need = water_circulation_need * (1.0 - TRANSPIRATION_RECOVERY)

    # Five stress factors (Liebig's Law: minimum governs)
    s_temp = temperature_stress(air_temp, crop.optimal_temp_min_c, crop.optimal_temp_max_c)
    s_water = water_stress(water_available_l, net_water_need)
    s_light = light_stress_dli(actual_dli, crop.dli_optimal)
    s_radiation = radiation_stress(radiation_level, crop.radiation_tolerance, growth_stage)
    s_disease = disease_stress_vpd(air_temp, rh_pct, crop.vpd_target_min)

    # Crop-specific modifiers
    s_bolt = bolting_stress(rz_temp, crop.photoperiod_hours, crop.is_bolting_sensitive)
    s_tuber = tuberization_factor(rz_temp, crop.tuberization_temp_max)

    combined = min(s_temp, s_water, s_light, s_radiation, s_disease, s_bolt, s_tuber)

    # Growth
    daily_biomass = crop.max_growth_rate * combined * crop.area_m2
    new_biomass = prev.biomass_kg + daily_biomass

    # Net water consumed (only the 5% not recovered from transpiration)
    water_used = net_water_need * min(1.0, s_water)

    # Death check: combined stress < 0.05 for a full day = lethal
    alive = combined > 0.05

    return DayState(
        day=prev.day + 1,
        gdd_accumulated=gdd_total,
        growth_stage=growth_stage,
        biomass_kg=new_biomass,
        water_consumed_l=prev.water_consumed_l + water_used,
        stress_factor=combined,
        alive=alive,
    )


# ── Resource Chain Model ────────────────────────────────────────────────


SOLAR_CAPACITY_KW = 4.2
DESAL_EFFICIENCY_L_PER_KW = 28.6      # ~120L/sol at 4.2kW
BATTERY_CAPACITY_KWH = 50.0
TRANSPIRATION_RECOVERY = 0.95          # 95% in closed Mars greenhouse
DESAL_POWER_FRACTION = 0.25


@dataclass
class ResourceDay:
    """Resource chain state for one day."""
    day: int
    solar_output_kw: float
    desal_rate_l: float
    water_in_l: float
    water_out_l: float
    water_reserve_l: float
    battery_pct: float


def simulate_resource_day(
    prev: ResourceDay,
    dust_opacity: float,
    total_crop_transpiration_l: float,
    total_crop_water_demand_l: float,
    max_desal_override: bool = False,
    recovery_rate: float = TRANSPIRATION_RECOVERY,
) -> ResourceDay:
    """Advance resource chain by one day."""
    solar = SOLAR_CAPACITY_KW * max(0.0, 1.0 - dust_opacity)

    if max_desal_override:
        desal = DESAL_EFFICIENCY_L_PER_KW * SOLAR_CAPACITY_KW * DESAL_POWER_FRACTION
    else:
        desal = DESAL_EFFICIENCY_L_PER_KW * solar * DESAL_POWER_FRACTION

    water_recovered = total_crop_transpiration_l * recovery_rate
    water_in = desal + water_recovered
    water_out = total_crop_water_demand_l
    new_reserve = max(0.0, prev.water_reserve_l + water_in - water_out)

    # Battery: charges during high solar, drains during low
    battery_delta = (solar / SOLAR_CAPACITY_KW - 0.5) * 10.0  # rough %/day
    new_battery = max(0.0, min(100.0, prev.battery_pct + battery_delta))

    return ResourceDay(
        day=prev.day + 1,
        solar_output_kw=round(solar, 2),
        desal_rate_l=round(desal, 1),
        water_in_l=round(water_in, 1),
        water_out_l=round(water_out, 1),
        water_reserve_l=round(new_reserve, 1),
        battery_pct=round(new_battery, 1),
    )


# ── Scenarios ───────────────────────────────────────────────────────────


SCENARIOS: dict[str, dict] = {
    "cme": {
        "type": "cme",
        "onset_day": 2,
        "duration_days": 5,
        "dust_opacity_peak": 0.85,
        "radiation_peak": 2.5,
        "pre_warning_days": 2,
    },
    "water_failure": {
        "type": "water_failure",
        "onset_day": 0,
        "duration_days": 3,
        "desal_capacity_pct": 0.0,
    },
    "disease": {
        "type": "disease",
        "onset_day": 0,
        "duration_days": 7,
        "humidity_override": 92.0,
        "temp_override": 28.0,
    },
    "dust_storm": {
        "type": "dust_storm",
        "onset_day": 0,
        "duration_days": 10,
        "dust_opacity_peak": 0.90,
        "radiation_peak": 1.0,
    },
    "nominal": {
        "type": "nominal",
        "onset_day": 999,
        "duration_days": 0,
    },
    "nominal_constrained": {
        "type": "nominal",
        "onset_day": 999,
        "duration_days": 0,
        "recovery_rate": 0.80,
        "description": "Sol 280: recovery system degraded to 80%, water reserve at 200L",
    },
}


def get_scenario(name: str) -> dict:
    return dict(SCENARIOS.get(name, SCENARIOS["cme"]))


# ── Strategies ──────────────────────────────────────────────────────────


STRATEGIES: dict[str, list[dict]] = {
    "cme": [
        {"name": "Do Nothing", "actions": []},
        {"name": "Standard Survival", "actions": [
            {"day_offset": 0, "action": "activate_shields", "value": True},
        ]},
        {"name": "Pre-emptive Protocol", "actions": [
            {"day_offset": -2, "action": "max_desal", "value": True},
            {"day_offset": -1, "action": "stress_harden_ec", "value": 2.4},
            {"day_offset": 0, "action": "activate_shields", "value": True},
            {"day_offset": 0, "action": "boost_led_critical", "value": True},
        ]},
    ],
    "water_failure": [
        {"name": "Do Nothing", "actions": []},
        {"name": "Triage Irrigation", "actions": [
            {"day_offset": 0, "action": "reduce_irrigation_pct", "value": 50},
        ]},
        {"name": "Emergency Rationing", "actions": [
            {"day_offset": 0, "action": "reduce_irrigation_pct", "value": 30},
            {"day_offset": 0, "action": "pre_harvest_zone", "zone": "vitamin", "value": True},
        ]},
    ],
    "disease": [
        {"name": "Do Nothing", "actions": []},
        {"name": "Increase Airflow", "actions": [
            {"day_offset": 0, "action": "increase_ventilation", "value": True},
        ]},
        {"name": "Quarantine + Ventilation", "actions": [
            {"day_offset": 0, "action": "increase_ventilation", "value": True},
            {"day_offset": 0, "action": "reduce_humidity", "value": True},
        ]},
    ],
    "dust_storm": [
        {"name": "Do Nothing", "actions": []},
        {"name": "Battery Supplement", "actions": [
            {"day_offset": 0, "action": "boost_led_critical", "value": True},
        ]},
        {"name": "Pre-emptive Protocol", "actions": [
            {"day_offset": -1, "action": "max_desal", "value": True},
            {"day_offset": 0, "action": "boost_led_critical", "value": True},
        ]},
    ],
    "nominal": [
        {"name": "Standard Protocol", "actions": [], "water_allocation": {}},
        {"name": "Redirect 30% Protein->Carb", "actions": [],
         "water_allocation": {"protein": 0.7, "carb": 1.3}},
        {"name": "Redirect 50% Protein->Carb", "actions": [],
         "water_allocation": {"protein": 0.5, "carb": 1.5}},
    ],
    "nominal_constrained": [
        {"name": "Standard Protocol", "actions": [], "water_allocation": {}},
        {"name": "Redirect 30% Protein->Carb", "actions": [],
         "water_allocation": {"protein": 0.7, "carb": 1.3}},
        {"name": "Redirect 50% Protein->Carb", "actions": [],
         "water_allocation": {"protein": 0.5, "carb": 1.5}},
    ],
}


def get_default_strategies(scenario_type: str) -> list[dict]:
    return [dict(s) for s in STRATEGIES.get(scenario_type, STRATEGIES["cme"])]


# ── Scenario Runner ─────────────────────────────────────────────────────


def _get_env_for_day(
    day: int,
    scenario: dict,
    strategy: dict,
    base_temp: float = 22.0,
    base_rh: float = 65.0,
    base_ppfd: float = 500.0,
    base_dust: float = 0.15,
) -> dict:
    """Compute environmental conditions for a given day, applying scenario + strategy."""
    temp = base_temp
    rh = base_rh
    ppfd = base_ppfd
    dust = base_dust
    radiation = 0.3  # dome-shielded baseline (70% UV blocked by structure)
    max_desal = False
    water_mult = 1.0

    onset = scenario.get("onset_day", 0)
    duration = scenario.get("duration_days", 5)
    stype = scenario.get("type", "cme")

    # Apply scenario effects during event window
    if onset <= day < onset + duration:
        if stype in ("cme", "dust_storm"):
            dust = scenario.get("dust_opacity_peak", 0.85)
            radiation = scenario.get("radiation_peak", 2.5)
            ppfd *= max(0.1, 1.0 - dust)
        elif stype == "water_failure":
            water_mult = scenario.get("desal_capacity_pct", 0.0)
        elif stype == "disease":
            rh = scenario.get("humidity_override", 92.0)
            temp = scenario.get("temp_override", 28.0)

    # Event is active if within window (includes pre-warning for pre-emptive actions)
    event_active = onset <= day < onset + duration
    pre_warning = scenario.get("pre_warning_days", 0)
    event_or_prep = (onset - pre_warning) <= day < (onset + duration)

    # Apply strategy actions only during event+prep window
    for action in strategy.get("actions", []):
        trigger_day = onset + action.get("day_offset", 0)
        if trigger_day <= day < onset + duration:
            act = action.get("action", "")
            if act == "reduce_light_pct":
                # Reduce supplemental LEDs (from base, not from storm-degraded)
                ppfd = base_ppfd * (action["value"] / 100.0) * max(0.1, 1.0 - dust)
            elif act == "max_desal":
                max_desal = True
            elif act == "activate_shields":
                radiation *= 0.3  # shields reduce 70% of radiation
            elif act == "increase_ventilation":
                rh = max(50.0, rh - 15.0)
            elif act == "reduce_humidity":
                rh = max(45.0, rh - 25.0)
            elif act == "stress_harden_ec":
                temp -= 1.0  # slight temp reduction from EC hardening effect
            elif act == "boost_led_critical":
                # Supplement LEDs from battery to maintain minimum DLI
                ppfd = max(ppfd, base_ppfd * 0.5)  # maintain at least 50% base
            elif act == "reduce_irrigation_pct":
                water_mult = action["value"] / 100.0

    return {
        "temp": temp, "rh": rh, "ppfd": ppfd, "dust": dust,
        "radiation": radiation, "max_desal": max_desal, "water_mult": water_mult,
    }


def run_scenario(
    scenario: dict,
    strategy: dict,
    crops: list[CropSimParams],
    initial_water_reserve: float = 340.0,
    initial_battery_pct: float = 78.0,
    simulation_days: int = 14,
    initial_gdd_fraction: float = 0.5,
) -> dict:
    """Run a full scenario with one strategy. Returns outcome metrics."""
    # Initialize crop states at mid-growth (typical for crisis scenario)
    crop_states: dict[str, DayState] = {}
    for crop in crops:
        # Estimate days of growth from GDD fraction and typical dome temp
        est_days = (crop.gdd_maturity * initial_gdd_fraction) / max(1.0, 22.0 - crop.base_temp_c)
        initial_biomass = crop.max_growth_rate * crop.area_m2 * est_days * 0.85  # 85% nominal efficiency
        crop_states[crop.name] = DayState(
            day=0, gdd_accumulated=crop.gdd_maturity * initial_gdd_fraction,
            growth_stage=initial_gdd_fraction,
            biomass_kg=initial_biomass,
            water_consumed_l=0.0, stress_factor=1.0, alive=True,
        )

    resource_state = ResourceDay(
        day=0, solar_output_kw=SOLAR_CAPACITY_KW, desal_rate_l=120.0,
        water_in_l=0, water_out_l=0,
        water_reserve_l=initial_water_reserve, battery_pct=initial_battery_pct,
    )

    # Run day-by-day
    baseline_biomass = sum(s.biomass_kg for s in crop_states.values())
    min_stress = 1.0
    stress_days = 0

    for day in range(1, simulation_days + 1):
        env = _get_env_for_day(day, scenario, strategy)

        total_transpiration = 0.0
        total_water_demand = 0.0

        # Per-zone water allocation multipliers from strategy
        water_alloc = strategy.get("water_allocation", {})

        for crop in crops:
            prev = crop_states[crop.name]
            # Daily water available = desal production share + draw from reserve
            daily_supply = resource_state.desal_rate_l / max(1, len(crops))
            reserve_draw = resource_state.water_reserve_l * 0.10 / max(1, len(crops))
            zone_mult = water_alloc.get(crop.zone_id, 1.0)
            water_per_crop = (daily_supply + reserve_draw) * zone_mult

            new_state = simulate_crop_day(
                crop, prev,
                air_temp=env["temp"], rh_pct=env["rh"],
                ppfd_umol=env["ppfd"],
                water_available_l=water_per_crop,
                radiation_level=env["radiation"],
            )
            crop_states[crop.name] = new_state

            # Track transpiration for water recovery
            rate = _get_transpiration_rate(crop.transpiration_rates, new_state.growth_stage)
            total_transpiration += rate * crop.area_m2 * new_state.stress_factor
            total_water_demand += rate * crop.area_m2

            if new_state.stress_factor < min_stress:
                min_stress = new_state.stress_factor
            if new_state.stress_factor < 0.8:
                stress_days += 1

        # Scenario can degrade recovery rate (Sol 280 equipment degradation)
        recovery = scenario.get("recovery_rate", TRANSPIRATION_RECOVERY)

        resource_state = simulate_resource_day(
            resource_state, env["dust"],
            total_transpiration, total_water_demand,
            max_desal_override=env["max_desal"],
            recovery_rate=recovery,
        )

    # Compute outcomes
    final_biomass = sum(s.biomass_kg for s in crop_states.values())
    biomass_gained = final_biomass - baseline_biomass

    # Yield loss: compare actual growth vs nominal (85% efficiency baseline)
    # Nominal = what you'd gain in these days with no event, ~85% stress factor
    nominal_gain = sum(c.max_growth_rate * c.area_m2 for c in crops) * simulation_days * 0.85
    if nominal_gain > 0:
        yield_loss_pct = max(0.0, (1.0 - biomass_gained / nominal_gain) * 100)
    else:
        yield_loss_pct = 0.0

    # Nutritional output
    total_kcal = sum(
        crop_states[c.name].biomass_kg * c.harvest_index * c.calories_per_kg
        for c in crops if crop_states[c.name].alive
    )
    total_protein = sum(
        crop_states[c.name].biomass_kg * c.harvest_index * c.protein_per_kg
        for c in crops if crop_states[c.name].alive
    )

    crops_survived = sum(1 for s in crop_states.values() if s.alive)
    total_water = sum(s.water_consumed_l for s in crop_states.values())

    # Water Use Efficiency: kcal produced per liter of water consumed
    # THE metric for Mars agriculture — every liter must be desalinated
    kcal_per_liter = round(total_kcal / max(0.1, total_water), 1) if total_water > 0 else 0.0
    protein_per_liter = round(total_protein / max(0.1, total_water), 2) if total_water > 0 else 0.0

    # Caloric gain vs baseline (for optimization comparison, not clamped to 0)
    baseline_kcal = sum(
        c.max_growth_rate * c.area_m2 * simulation_days * 0.85 * c.harvest_index * c.calories_per_kg
        for c in crops
    )
    caloric_delta_pct = round((total_kcal / max(1, baseline_kcal) - 1.0) * 100, 1) if baseline_kcal > 0 else 0.0

    return {
        "yield_loss_pct": round(yield_loss_pct, 1),
        "water_consumed_L": round(total_water, 1),
        "crops_survived": crops_survived == len(crops),
        "crops_alive": crops_survived,
        "crops_total": len(crops),
        "final_water_reserve_L": round(resource_state.water_reserve_l, 1),
        "min_stress_factor": round(min_stress, 3),
        "stress_days": stress_days,
        "nutrition": {
            "total_kcal": round(total_kcal, 0),
            "total_protein_g": round(total_protein, 0),
            "kcal_per_sol": round(total_kcal / max(1, simulation_days), 0),
            "protein_g_per_sol": round(total_protein / max(1, simulation_days), 0),
        },
        "efficiency": {
            "kcal_per_liter": kcal_per_liter,
            "protein_g_per_liter": protein_per_liter,
            "caloric_delta_pct": caloric_delta_pct,
        },
    }


# ── Monte Carlo Engine ──────────────────────────────────────────────────


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = (pct / 100.0) * (len(s) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def perturb_params(base: dict, sigma: float = 0.08) -> dict:
    """Add gaussian noise to all numeric parameters for Monte Carlo spread."""
    result = dict(base)
    for key in ("initial_water_reserve", "initial_battery_pct",
                "base_temp", "base_rh", "event_severity"):
        if key in result and isinstance(result[key], (int, float)):
            result[key] = max(0.0, result[key] * (1.0 + random.gauss(0, sigma)))
    return result


def monte_carlo_compare(
    scenario: dict,
    strategies: list[dict],
    crops: list[CropSimParams] | None = None,
    initial_state: dict | None = None,
    n_runs: int = 100,
    simulation_days: int = 14,
    seed: int | None = None,
) -> list[dict]:
    """Compare strategies via Monte Carlo. Returns ranked results with CIs."""
    if seed is not None:
        random.seed(seed)

    if crops is None:
        crops = list(CROP_LIBRARY.values())

    state = initial_state or {}
    base_water = state.get("initial_water_reserve", 340.0)
    base_battery = state.get("initial_battery_pct", 78.0)

    all_results: list[dict] = []

    for strategy in strategies:
        outcomes: list[dict] = []
        for _ in range(n_runs):
            perturbed = perturb_params({
                "initial_water_reserve": base_water,
                "initial_battery_pct": base_battery,
                "base_temp": 22.0,
                "base_rh": 65.0,
                "event_severity": 1.0,
            }, sigma=0.08)

            # Perturb event severity (dust/radiation intensity varies)
            perturbed_scenario = dict(scenario)
            sev = perturbed.get("event_severity", 1.0)
            for key in ("dust_opacity_peak", "radiation_peak"):
                if key in perturbed_scenario:
                    perturbed_scenario[key] = perturbed_scenario[key] * sev

            outcome = run_scenario(
                perturbed_scenario, strategy, crops,
                initial_water_reserve=perturbed["initial_water_reserve"],
                initial_battery_pct=perturbed["initial_battery_pct"],
                simulation_days=simulation_days,
            )
            outcomes.append(outcome)

        yield_losses = [o["yield_loss_pct"] for o in outcomes]
        water_used = [o["water_consumed_L"] for o in outcomes]
        kcals = [o["nutrition"]["kcal_per_sol"] for o in outcomes]
        kcal_per_l = [o["efficiency"]["kcal_per_liter"] for o in outcomes]
        caloric_deltas = [o["efficiency"]["caloric_delta_pct"] for o in outcomes]

        all_results.append({
            "strategy": strategy["name"],
            "yield_loss_pct": {
                "mean": round(_mean(yield_losses), 1),
                "p5": round(_percentile(yield_losses, 5), 1),
                "p50": round(_percentile(yield_losses, 50), 1),
                "p95": round(_percentile(yield_losses, 95), 1),
            },
            "water_consumed_L": {
                "mean": round(_mean(water_used), 1),
                "p5": round(_percentile(water_used, 5), 1),
                "p95": round(_percentile(water_used, 95), 1),
            },
            "nutrition_preserved": {
                "kcal_per_sol": round(_mean(kcals), 0),
                "protein_g_per_sol": round(_mean([o["nutrition"]["protein_g_per_sol"] for o in outcomes]), 0),
            },
            "efficiency": {
                "kcal_per_liter": round(_mean(kcal_per_l), 1),
                "caloric_delta_pct": round(_mean(caloric_deltas), 1),
            },
            "survival_probability": round(
                sum(1 for o in outcomes if o["crops_survived"]) / n_runs, 2
            ),
            "confidence": round(
                1.0 - (_percentile(yield_losses, 95) - _percentile(yield_losses, 5)) / 100, 2
            ),
            "n_runs": n_runs,
        })

    # Rank by caloric efficiency for nominal scenarios, yield loss for crisis
    scenario_type = scenario.get("type", "cme")
    if scenario_type == "nominal":
        all_results.sort(key=lambda r: -r["efficiency"]["kcal_per_liter"])  # higher is better
    else:
        all_results.sort(key=lambda r: r["yield_loss_pct"]["mean"])  # lower is better
    for i, r in enumerate(all_results):
        r["rank"] = i + 1
        r["selected"] = i == 0

    return all_results
