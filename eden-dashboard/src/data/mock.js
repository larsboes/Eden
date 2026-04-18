// EDEN Data Layer — derived from data/*.json source files
// Source: sensor-baseline.json, crop-states.json, crop-profiles.json,
//         crew-requirements.json, mission-projection.json, triage-scenarios.json,
//         flight-rules.json, demo-script.json, dashboard-config.json

// ─── ZONES ──────────────────────────────────────────────────────────────────
// From: sensor-baseline.json + crop-states.json + crop-profiles.json

export const ZONES = [
  {
    id: "A", name: "PROTEIN",
    crops: ["Soybean", "Lentil"],
    icon: "\u{1FAD8}",
    // sensor-baseline.json zones.protein
    temp: 22.3, humidity: 63, soilMoisture: 72,
    co2: 890, light: 82, ph: 6.2,
    vpd: 0.95, ec: 1.8, dli: 17.2,
    // crop-states.json aggregated
    health: 90, // avg(91, 88)
    waterUsage: 1.75, // avg(2.1, 1.4)
    bbch: 65, bbchLabel: "Full flowering",
    pods: 20, activePods: 20,
    status: "nominal",
    cropDetails: [
      { name: "Soybean", bbch: 65, bbchLabel: "Full flowering — 50% of flowers open", health: 91, daysPlanted: 60, daysToHarvest: 30, companion: "Lentil (shared N-fixation, -18% nutrient input)" },
      { name: "Lentil", bbch: 71, bbchLabel: "Beginning of fruit development — pods visible", health: 88, daysPlanted: 55, daysToHarvest: 25, companion: "Soybean (shared N-fixation, mutual legume synergy)" },
    ],
  },
  {
    id: "B", name: "CARB",
    crops: ["Potato", "Wheat"],
    icon: "\u{1F33E}",
    // sensor-baseline.json zones.carb
    temp: 20.1, humidity: 58, soilMoisture: 68,
    co2: 820, light: 78, ph: 5.9,
    vpd: 1.12, ec: 1.5, dli: 15.8,
    // crop-states.json aggregated
    health: 92, // avg(94, 90)
    waterUsage: 2.35, // avg(2.8, 1.9)
    bbch: 55, bbchLabel: "Heading — half of inflorescence emerged",
    pods: 24, activePods: 23,
    status: "nominal",
    cropDetails: [
      { name: "Potato", bbch: 45, bbchLabel: "Tuber development — stolons thickening", health: 94, daysPlanted: 50, daysToHarvest: 40, companion: "Wheat (staggered canopy layers)" },
      { name: "Wheat", bbch: 55, bbchLabel: "Heading — half of inflorescence emerged", health: 90, daysPlanted: 65, daysToHarvest: 35, companion: "Potato (interplanted rows)" },
    ],
  },
  {
    id: "C", name: "VITAMIN",
    crops: ["Tomato", "Spinach"],
    icon: "\u{1F345}",
    // sensor-baseline.json zones.vitamin (humidity=42 — easter egg!)
    temp: 23.8, humidity: 42, soilMoisture: 75,
    co2: 950, light: 88, ph: 6.4,
    vpd: 0.88, ec: 2.2, dli: 19.5,
    health: 91, // avg(86, 96)
    waterUsage: 2.0, // avg(3.2, 0.8)
    bbch: 73, bbchLabel: "Fruit development — 30% at final size",
    pods: 18, activePods: 17,
    status: "watch",
    cropDetails: [
      { name: "Tomato", bbch: 73, bbchLabel: "Fruit development — 30% of fruits at final size", health: 86, daysPlanted: 70, daysToHarvest: 20, companion: "Basil (antifungal VOCs reduce Botrytis -40%)" },
      { name: "Spinach", bbch: 41, bbchLabel: "Leaf development — harvestable rosette formed", health: 96, daysPlanted: 28, daysToHarvest: 7, companion: "Tomato (shaded by canopy, reduces bolting)" },
    ],
  },
  {
    id: "D", name: "SUPPORT",
    crops: ["Basil", "Reserve"],
    icon: "\u{1F33F}",
    temp: 21.5, humidity: 68, soilMoisture: 70,
    co2: 880, light: 65, ph: 6.5,
    vpd: 0.72, ec: 1.2, dli: 12.0,
    health: 94,
    waterUsage: 0.8,
    bbch: 30, bbchLabel: "Stem elongation",
    pods: 8, activePods: 8,
    status: "nominal",
    cropDetails: [
      { name: "Basil", bbch: 30, bbchLabel: "Stem elongation — aromatic compound peak", health: 94, daysPlanted: 35, daysToHarvest: 10, companion: "Tomato (linalool + eugenol suppress fungal spores)" },
      { name: "Microgreens", bbch: 10, bbchLabel: "Emergency reserve — 10-14 sol harvest cycle", health: 95, daysPlanted: 8, daysToHarvest: 6, companion: null },
    ],
  },
];

// ─── CREW ───────────────────────────────────────────────────────────────────
// From: crew-requirements.json + mission-projection.json

export const CREW = [
  {
    name: "Cmdr. Chen", role: "Commander", emoji: "\u{1F469}\u{200D}\u{1F680}",
    kcalTarget: 2375, kcalActual: 2256, // 95% achieved
    protein: 87, iron: 72, calcium: 85, vitC: 133, vitD: 0, zinc: 78, potassium: 65,
    preference: "Spinach \u2014 requested 3x this week. Prefers stir-fry preparation.",
    dietaryFlags: [],
    note: "Light EVA schedule. Iron trending low \u2014 monitoring.",
  },
  {
    name: "Dr. Okafor", role: "Science Lead", emoji: "\u{1F468}\u{200D}\u{1F52C}",
    kcalTarget: 2250, kcalActual: 2138,
    protein: 94, iron: 91, calcium: 88, vitC: 120, vitD: 0, zinc: 82, potassium: 70,
    preference: "Lentil soup \u2014 vegetarian preference. Values meal variety.",
    dietaryFlags: ["vegetarian"],
    note: "Lab-focused, lowest energy expenditure.",
  },
  {
    name: "Eng. Petrov", role: "Engineer", emoji: "\u{1F468}\u{200D}\u{1F680}",
    kcalTarget: 2750, kcalActual: 2530,
    protein: 82, iron: 85, calcium: 68, vitC: 115, vitD: 0, zinc: 75, potassium: 60,
    preference: "Potato \u2014 comfort food, reminds him of home.",
    dietaryFlags: [],
    note: "Higher calorie need from EVA work. Calcium trending low.",
  },
  {
    name: "Sci. Tanaka", role: "Botanist", emoji: "\u{1F469}\u{200D}\u{1F52C}",
    kcalTarget: 2375, kcalActual: 2280,
    protein: 90, iron: 88, calcium: 82, vitC: 140, vitD: 0, zinc: 80, potassium: 68,
    preference: "Tomato \u2014 sees fresh tomatoes as mission morale indicator.",
    dietaryFlags: [],
    note: "Monitors crop health daily. Emotional attachment to greenhouse.",
  },
];

// ─── RESOURCES ──────────────────────────────────────────────────────────────
// From: demo-script.json phases (NOMINAL / STOCKPILING / IMPACT)

export const RESOURCES = {
  water:   { current: 340, max: 600, unit: "L", rate: "+20 L/sol surplus", label: "Clean Water Reserve" },
  battery: { current: 78,  max: 100, unit: "%", rate: "Cycling nominal", label: "Battery Charge" },
  solar:   { current: 100, max: 100, unit: "%", rate: "4.2 kW output", label: "Solar Output" },
  desal:   { current: 120, max: 120, unit: "L/sol", rate: "Nominal capacity", label: "Desalination Rate" },
  o2:      { current: 14.2, max: 20, unit: "%", rate: "Greenhouse O\u2082 contribution", label: "O\u2082 Contribution" },
};

export const RESOURCES_PRESTORM = {
  water:   { current: 580, max: 600, unit: "L", rate: "+240L stockpiled in 48h", label: "Clean Water Reserve" },
  battery: { current: 100, max: 100, unit: "%", rate: "Fully charged", label: "Battery Charge" },
  solar:   { current: 100, max: 100, unit: "%", rate: "4.2 kW (last hours)", label: "Solar Output" },
  desal:   { current: 120, max: 120, unit: "L/sol", rate: "Running at MAX", label: "Desalination Rate" },
  o2:      { current: 14.2, max: 20, unit: "%", rate: "Pre-storm nominal", label: "O\u2082 Contribution" },
};

export const RESOURCES_STORM = {
  water:   { current: 260, max: 600, unit: "L", rate: "-64 L/sol deficit", label: "Clean Water Reserve" },
  battery: { current: 45,  max: 100, unit: "%", rate: "Draining \u2014 shields active", label: "Battery Charge" },
  solar:   { current: 30,  max: 100, unit: "%", rate: "1.26 kW \u2014 STORM", label: "Solar Output" },
  desal:   { current: 36,  max: 120, unit: "L/sol", rate: "Degraded (30% power)", label: "Desalination Rate" },
  o2:      { current: 11.8, max: 20, unit: "%", rate: "Reduced \u2014 lights dimmed", label: "O\u2082 Contribution" },
};

export const RESOURCES_RECOVERY = {
  water:   { current: 340, max: 600, unit: "L", rate: "Stabilizing", label: "Clean Water Reserve" },
  battery: { current: 72,  max: 100, unit: "%", rate: "Recharging", label: "Battery Charge" },
  solar:   { current: 91,  max: 100, unit: "%", rate: "3.82 kW recovering", label: "Solar Output" },
  desal:   { current: 114, max: 120, unit: "L/sol", rate: "Ramping up", label: "Desalination Rate" },
  o2:      { current: 13.6, max: 20, unit: "%", rate: "Recovering", label: "O\u2082 Contribution" },
};

// ─── COUNCIL LOG ────────────────────────────────────────────────────────────
// From: demo-script.json phases.agent_log

export const COUNCIL_LOG_NOMINAL = [
  { time: "14:19:11", agent: "FLORA", msg: "Sol 247. All zones nominal. Soybean entering BBCH 65 \u2014 full flowering. Companion planting synergy with wheat confirmed: nutrient solution EC reduced to 1.6 mS/cm. VPD at 0.95 kPa, within target.", type: "info", color: "#22c55e" },
  { time: "14:20:03", agent: "AQUA", msg: "Water recycler at 94.2%. Desalination producing 120L/sol. Net surplus: +20L/sol. Reserve trending upward. Transpiration capture at 65% efficiency.", type: "info", color: "#06b6d4" },
  { time: "14:21:15", agent: "VITA", msg: "Crew nutrition on track. Protein coverage: 32%. Vitamin C: 133% \u2014 surplus. Cmdr. Chen\u2019s iron trending low at 72% \u2014 monitoring. Next spinach harvest Sol 252.", type: "info", color: "#a855f7" },
  { time: "14:22:30", agent: "ORACLE", msg: "Overnight dream cycle: 4,217 scenarios simulated. 3 new flight rules proposed. Mission survival probability: 96.2%. Next dust storm season peak: Ls 220 in ~5 sols.", type: "info", color: "#f59e0b" },
  { time: "14:23:00", agent: "SENTINEL", msg: "DONKI scan: No active CME events. InSight baseline: -62\u00B0C surface, 750 Pa. Current Ls: 215\u00B0 \u2014 entering dust storm season. Heightened readiness.", type: "info", color: "#ef4444" },
];

export const COUNCIL_LOG = [
  { time: "14:24:09", agent: "SENTINEL", msg: "Sol 247. CME-2026-0124 detected. Speed: 1,243 km/s out of N15E10. Instruments: SOHO LASCO/C2, C3, STEREO A COR2. Mars ETA: 50.7 hours. Wheat in Node:Carb at BBCH 60 \u2014 HIGH radiation vulnerability at flowering.", type: "alert", color: "#ef4444" },
  { time: "14:24:10", agent: "SENTINEL", msg: "Querying Syngenta KB: wheat radiation tolerance at BBCH 60... KB response: \u2018Yield reduction 15-40% under elevated UV-B during flowering. Recommend radiation shielding and modified nutrient solution.\u2019 Source: Plant Stress and Response Guide.", type: "kb_query", color: "#ef4444" },
  { time: "14:24:12", agent: "ORACLE", msg: "Running Virtual Farming Lab \u2014 3 strategies evaluating. Strategy A (Do Nothing): 40% crop loss, 3-sol recovery. Strategy B (Standard Survival): 12% loss, shields + reduce light. Strategy C (Pre-emptive Full Protocol): 3% loss, stockpile water, pre-harvest spinach, stress-harden wheat. RECOMMENDATION: Strategy C. Confidence: 87% (Syngenta KB stress data).", type: "decision", color: "#f59e0b" },
  { time: "14:24:16", agent: "AQUA", msg: "Water at 340L. Storm needs 5-sol autonomy = 580L. Deficit: 240L. Running desalination at MAX for 48h \u2014 solar still at 100%. Battery charging priority. Transpiration capture sealed.", type: "action", color: "#06b6d4" },
  { time: "14:24:17", agent: "FLORA", msg: "Pre-harvest spinach \u2014 lock in 1.9 kg nutrition before stress period. Stress-harden wheat: EC from 2.0 to 2.4 mS/cm. DLI maintained at 17 mol/m\u00B2/day. She\u2019ll be ornery but she\u2019ll make it.", type: "action", color: "#22c55e" },
  { time: "14:24:18", agent: "VITA", msg: "Pre-harvest spinach secured. Vitamin C buffer: 58 sols. Cmdr. Chen requested spinach 3x this week \u2014 saving a portion. Dr. Okafor\u2019s iron stable. Eng. Petrov\u2019s calorie reserves adequate for 5-sol reduced output.", type: "triage", color: "#a855f7" },
  { time: "14:24:19", agent: "COUNCIL", msg: "VOTE: Strategy C adopted unanimously (5/5). SENTINEL: shield activation. AQUA: max desalination. FLORA: pre-harvest spinach, stress-harden wheat. VITA: vitamin C buffer 58 sols \u2014 acceptable. Executing pre-emptive full protocol.", type: "decision", color: "#ffffff" },
];

// ─── STRATEGIES ─────────────────────────────────────────────────────────────
// From: demo-script.json DETECTION phase

export const STRATEGIES = [
  { name: "A \u2014 Do Nothing", loss: 40, recovery: 45, resourceCost: "Nominal", confidence: 95, selected: false, detail: "No intervention. Accept radiation damage. 3+ sols recovery. Wheat flowering disrupted." },
  { name: "B \u2014 Standard Survival", loss: 12, recovery: 15, resourceCost: "Shields + heating: 2.1kW for 5 sols", confidence: 88, selected: false, detail: "Activate shields and reduce light. No pre-emptive water stockpiling." },
  { name: "C \u2014 Pre-emptive Full Protocol", loss: 3, recovery: 5, resourceCost: "Max desal 48h + pre-harvest + stress-harden", confidence: 87, selected: true, detail: "Stockpile 240L water. Pre-harvest spinach. Stress-harden wheat EC +0.4 mS/cm. Top battery. Shields armed." },
];

// ─── TRIAGE ─────────────────────────────────────────────────────────────────
// From: triage-scenarios.json + demo-script.json IMPACT phase

export const TRIAGE = [
  {
    zone: "B", crop: "Wheat", score: 0.72, trend: "at-risk",
    color: "RED",
    decision: "Shields activated. Stress-hardening EC +0.4 mS/cm. Monitoring BBCH 60 flowering.",
    crewImpact: "Carb output may drop 8% if flowering disrupted. Eng. Petrov\u2019s bread ration reduced.",
    nutritionalDelta: { calories: -3.2, carbs: -8.0, protein: -2.1 },
  },
  {
    zone: "C", crop: "Tomato", score: 0.85, trend: "monitoring",
    color: "YELLOW",
    decision: "Light reduced to survival minimum. Growth paused. Resume post-storm.",
    crewImpact: "Vitamin C output paused 5 sols. Buffer adequate (133% pre-storm). Sci. Tanaka monitoring hourly.",
    nutritionalDelta: { vitC: -5.0, calories: -1.8 },
  },
  {
    zone: "A", crop: "Soybean", score: 0.91, trend: "stable",
    color: "GREEN",
    decision: "Pod development stage \u2014 radiation resilient. Maintaining protocol.",
    crewImpact: null,
    nutritionalDelta: null,
  },
  {
    zone: "C", crop: "Spinach", score: 0.34, trend: "pre-harvested",
    color: "BLACK",
    decision: "PRE-HARVESTED before storm. 1.9 kg secured in cold storage.",
    crewImpact: "Cmdr. Chen\u2019s preferred green \u2014 portion saved. Iron from spinach locked in. Microgreens substituting from reserve.",
    nutritionalDelta: { iron: -33.3, vitC: -26.0, calcium: -49.3 },
  },
];

// ─── FLIGHT RULES ───────────────────────────────────────────────────────────
// From: flight-rules.json (top relevant rules for dashboard display)

export const FLIGHT_RULES = [
  { id: "FR-S-001", rule: "Dome pressure < 400 hPa \u2192 Seal all zones, alert crew, EMERGENCY mode", status: "armed", count: 0, priority: "CRITICAL", source: "Earth baseline" },
  { id: "FR-R-001", rule: "Radiation > 50 \u00B5Sv/hr \u2192 Shields ON, non-essential power OFF", status: "armed", count: 0, priority: "HIGH", source: "Earth baseline" },
  { id: "FR-W-001", rule: "Water reserve < 200L \u2192 RATION mode, suspend non-critical irrigation", status: "armed", count: 0, priority: "HIGH", source: "Earth baseline" },
  { id: "FR-CME-001", rule: "CME detected speed > 800 km/s \u2192 Calculate Mars ETA, convene Council", status: "triggered", count: 1, priority: "HIGH", source: "Sol 1 baseline" },
  { id: "FR-CME-002", rule: "CME ETA < 72h \u2192 Pre-storm water stockpiling, desal MAX, battery priority", status: "triggered", count: 1, priority: "HIGH", source: "Sol 1 baseline" },
  { id: "FR-T-003", rule: "Zone temp > 25\u00B0C + spinach \u2192 Bolting risk, reduce temp, emergency harvest", status: "armed", count: 0, priority: "MEDIUM", source: "Syngenta KB" },
  { id: "FR-N-001", rule: "pH < 5.0 or > 7.0 \u2192 Nutrient lockout risk, flush and recalibrate", status: "armed", count: 0, priority: "HIGH", source: "CEA principles" },
  { id: "FR-CME-004", rule: "CME > 1000 km/s + flowering BBCH 55-70 \u2192 Pre-harvest leafy greens, stress-harden", status: "triggered", count: 1, priority: "HIGH", source: "Learned: post-CME-2026-0124" },
  { id: "FR-E-001", rule: "Battery < 20% \u2192 LOW POWER mode, shutdown non-critical lighting", status: "armed", count: 0, priority: "HIGH", source: "Earth baseline" },
  { id: "FR-H-003", rule: "VPD > 1.5 kPa \u2192 Increase humidity or reduce temperature", status: "armed", count: 0, priority: "MEDIUM", source: "CEA principles" },
];

// ─── MISSION PLAN ───────────────────────────────────────────────────────────
// From: mission-projection.json

export const MISSION_PLAN = {
  cargo_kg: 2400,
  dome_m2: 100,
  crew: 4,
  duration_sols: 450,
  // From mission-projection.json coverage percentages
  projectedCalories: 14.5,
  projectedProtein: 32.2,
  projectedVitamins: 133.5, // Vitamin C surplus
  projectedIron: 112.7,
  projectedFat: 7.3,
  totalYieldKg: 1282.5,
  totalCalories: 651975,
  daysWithFreshFood: 420,
  riskFlags: [
    "Wheat flowering (BBCH 60) overlaps Ls 220 dust storm season",
    "Protein gap Sol 1-90 before first soybean harvest",
    "Fat coverage only 7.3% \u2014 stored oils mission-critical",
    "Vitamin D: 0% greenhouse production, supplements mandatory",
    "Calcium: effective 12-15% after spinach oxalate absorption loss",
  ],
  surpluses: [
    "Vitamin C: 133.5% \u2014 tomato (45.6%) + potato (27.3%) + spinach (26.0%)",
    "Iron: 112.7% \u2014 spinach (33.3%) + soybean (29.0%); note low bioavailability",
  ],
  waterBudget: {
    dailyNeed: 253.5,
    recyclingEfficiency: 65,
    netDailyConsumption: 88.7,
    desalCapacity: 120,
    note: "Within capacity with 35% margin after transpiration recycling",
  },
};

// ─── MEMORY WALL ────────────────────────────────────────────────────────────
// From: mission-projection.json timeline

export const MEMORY_WALL = [
  { sol: 1,   event: "First seed planted. Greenhouse environment stabilizing." },
  { sol: 30,  event: "First spinach leaves. Cmdr. Chen\u2019s morale boost \u2014 fresh food after 30 sols of stored rations." },
  { sol: 45,  event: "First full spinach harvest: 20 kg. Fresh Vitamin C entering crew diet." },
  { sol: 70,  event: "First tomato harvest: 120 kg. Sci. Tanaka establishes \u2018Tomato Day\u2019 crew tradition." },
  { sol: 80,  event: "First potato harvest: 60 kg. Eng. Petrov finally gets his comfort food." },
  { sol: 90,  event: "First protein harvest. Soybean: 6 kg, Lentil: 2 kg. Dr. Okafor\u2019s lentil soup." },
  { sol: 120, event: "First wheat harvest: 7.5 kg. First bread baked. \u2018Bread Day\u2019 celebrated." },
  { sol: 135, event: "Steady-state production reached. All 6 crops in continuous rotation." },
  { sol: 180, event: "Second protein cycle complete. Cumulative: 16 kg dried legumes." },
  { sol: 225, event: "Mid-mission. All crops in steady rotation. Spinach cycle 5, tomato cycle 3." },
  { sol: 240, event: "Second wheat harvest. Cumulative: 15 kg. Flight rules: 50 \u2192 87." },
  { sol: 247, event: "Current sol. CME-2026-0124 detected. Council convened. Strategy C activated." },
];

// ─── NUTRITIONAL PROJECTION ─────────────────────────────────────────────────
// From: mission-projection.json — for NutritionPanel detail view

export const NUTRITIONAL_PROJECTION = {
  calories:  { coverage: 14.5,  required: 4500000,  produced: 651975,  severity: "high",     note: "Greenhouse supplements stored rations. 362 kcal/person/day." },
  protein:   { coverage: 32.2,  required: 108000,   produced: 34780,   severity: "moderate",  note: "Soybean is anchor (31.5% of greenhouse protein)." },
  fat:       { coverage: 7.3,   required: 126000,   produced: 9182,    severity: "critical",  note: "Only soybean produces meaningful fat. Stored oils essential." },
  carbs:     { coverage: 18.9,  required: 630000,   produced: 118870,  severity: "high",      note: "Potato 44% of greenhouse carbs. Wheat limited by 120-day cycle." },
  fiber:     { coverage: 58.3,  required: 45000,    produced: 26245,   severity: "low",       note: "Good base from fresh vegetables." },
  vitaminC:  { coverage: 133.5, required: 162000,   produced: 216190,  severity: "surplus",   note: "SURPLUS. Tomato 45.6%, potato 27.3%, spinach 26.0%." },
  iron:      { coverage: 112.7, required: 14400,    produced: 16230,   severity: "surplus",   note: "Nominal surplus but non-heme iron has 5-12% bioavailability." },
  calcium:   { coverage: 22.3,  required: 1800000,  produced: 401225,  severity: "moderate",  note: "Spinach oxalates reduce absorption ~75%. Effective ~12-15%." },
  vitaminD:  { coverage: 0.0,   required: 27000,    produced: 0,       severity: "critical",  note: "ZERO. No plant produces Vitamin D. Supplements mandatory." },
};

// ─── CROP PROFILES ──────────────────────────────────────────────────────────
// From: crop-profiles.json — summary for components

export const CROP_PROFILES = [
  { name: "Soybean",  zone: "protein",  area: 20, growthDays: 90,  cycles: 5,  totalYield: 30,   calPer100g: 446, proteinPer100g: 36.5, vitCPer100g: 6.0,  ironPer100g: 15.7, companion: "Wheat (N-fixation -18%)", radiationTolerance: "moderate" },
  { name: "Lentil",   zone: "protein",  area: 10, growthDays: 90,  cycles: 5,  totalYield: 10,   calPer100g: 353, proteinPer100g: 25.8, vitCPer100g: 4.5,  ironPer100g: 7.5,  companion: null, radiationTolerance: "low" },
  { name: "Potato",   zone: "carb",     area: 15, growthDays: 80,  cycles: 5,  totalYield: 300,  calPer100g: 77,  proteinPer100g: 2.0,  vitCPer100g: 19.7, ironPer100g: 0.8,  companion: null, radiationTolerance: "high" },
  { name: "Wheat",    zone: "carb",     area: 15, growthDays: 120, cycles: 3,  totalYield: 22.5, calPer100g: 339, proteinPer100g: 13.2, vitCPer100g: 0,    ironPer100g: 3.6,  companion: "Soybean (receives fixed N)", radiationTolerance: "moderate" },
  { name: "Tomato",   zone: "vitamin",  area: 15, growthDays: 70,  cycles: 6,  totalYield: 720,  calPer100g: 18,  proteinPer100g: 0.9,  vitCPer100g: 13.7, ironPer100g: 0.3,  companion: "Basil (antifungal VOCs)", radiationTolerance: "low" },
  { name: "Spinach",  zone: "vitamin",  area: 10, growthDays: 45,  cycles: 10, totalYield: 200,  calPer100g: 23,  proteinPer100g: 2.9,  vitCPer100g: 28.1, ironPer100g: 2.7,  companion: null, radiationTolerance: "low" },
];

// ─── DEMO SCENARIO PHASES ──────────────────────────────────────────────────
// From: demo-script.json + replay-timing.json

export const DEMO_PHASES = [
  { id: "NOMINAL",    name: "The Loneliest Farmer",     durationS: 30, bgTint: "#0a0c10", accent: "#22c55e" },
  { id: "DETECTION",  name: "EDEN Sees the Future",     durationS: 30, bgTint: "#1a1408", accent: "#f59e0b" },
  { id: "STOCKPILING",name: "Preparing for the Storm",  durationS: 30, bgTint: "#1a1408", accent: "#f59e0b" },
  { id: "IMPACT",     name: "The Storm Hits",           durationS: 30, bgTint: "#1a0808", accent: "#ef4444" },
  { id: "RECOVERY",   name: "Through the Storm",        durationS: 15, bgTint: "#081a0a", accent: "#22c55e" },
  { id: "MIRROR",     name: "The Mirror",               durationS: 45, bgTint: "#0a0c10", accent: "#22c55e" },
];

// ─── CME EVENT (real NASA DONKI data) ───────────────────────────────────────
// From: demo-scenario/demo-cme-event.json

export const CME_EVENT = {
  activityID: "2026-01-24T09:23:00-CME-001",
  startTime: "2026-01-24T09:23Z",
  sourceLocation: "N15E10",
  speed_km_s: 1243,
  halfAngle_deg: 11,
  instruments: ["SOHO: LASCO/C2", "SOHO: LASCO/C3", "STEREO A: SECCHI/COR2"],
  marsETA_hours: 50.7,
  marsETA_calculation: "227,000,000 km / 1,243 km/s / 3600 = 50.7 hours",
  type: "S",
};

// ─── SYNGENTA KB QUERIES ────────────────────────────────────────────────────
// From: syngenta-kb-examples.json — visible in agent log for demo

export const SYNGENTA_KB = {
  documents: [
    { id: "01", name: "Mars Environmental Constraints" },
    { id: "02", name: "Controlled Environment Agriculture Principles" },
    { id: "03", name: "Crop Profiles Extended" },
    { id: "04", name: "Plant Stress and Response Guide" },
    { id: "05", name: "Human Nutritional Strategy" },
    { id: "07", name: "From Mars to Earth Innovation Impact" },
  ],
  exampleQueries: [
    { query: "wheat radiation tolerance at BBCH 60", source: "Plant Stress + Crop Profiles", finding: "Yield reduction 15-40% under elevated UV-B during flowering. Recommend shielding and modified nutrient solution." },
    { query: "water requirements per crop per stage", source: "CEA Principles + Crop Profiles", finding: "Potato 3.5 L/m\u00B2/day, Tomato 4.0, Soybean 2.1, Spinach 2.0, Wheat 2.5, Lentil 1.8." },
    { query: "optimal crop portfolio 4 astronauts 450 days", source: "Crop Profiles + Human Nutritional Strategy", finding: "40-50% Potatoes (caloric backbone), 20-30% Legumes (protein), 15-20% Leafy greens (vitamins), 5-10% Herbs (morale)." },
    { query: "companion planting synergies", source: "Crop Profiles + CEA Principles", finding: "Soybean-Wheat N-fixation reduces nutrient cost 18%. Basil-Tomato antifungal VOCs reduce Botrytis 40%." },
    { query: "Mars agriculture applications for Earth", source: "Innovation Impact", finding: "Autonomous agriculture for drought regions, food deserts, refugee camps. Same agent architecture, different planet." },
  ],
};

// ─── AGENT COLORS (from dashboard-config.json) ──────────────────────────────

export const AGENT_COLORS = {
  SENTINEL:   "#ef4444",
  ORACLE:     "#f59e0b",
  AQUA:       "#06b6d4",
  FLORA:      "#22c55e",
  VITA:       "#a855f7",
  COUNCIL:    "#ffffff",
  FLIGHT_CTRL:"#f97316",
  SYSTEM:     "#6b7280",
};

// ─── K8s CLUSTER STATE ──────────────────────────────────────────────────────
// ArgoCD-style reconciliation status for the EDEN cluster

export const CLUSTER_STATUS = {
  nominal: {
    syncStatus: "Synced",
    healthStatus: "Healthy",
    reconciledAt: "30s ago",
    nodes: 4,
    pods: 8,
    activePods: 8,
    flightRules: 87,
    pdb: { maxUnavailable: "30%", currentUnavailable: 0, budget: "OK" },
    daemonSet: { desired: 4, ready: 4 },
    strategy: null,
    networkPolicy: "OPEN",
  },
  alert: {
    syncStatus: "Warning",
    healthStatus: "CME Incoming",
    reconciledAt: "5s ago",
    nodes: 4,
    pods: 8,
    activePods: 8,
    flightRules: 87,
    pdb: { maxUnavailable: "30%", currentUnavailable: 0, budget: "OK" },
    daemonSet: { desired: 4, ready: 4 },
    strategy: "C",
    networkPolicy: "OPEN",
  },
  crisis: {
    syncStatus: "OutOfSync",
    healthStatus: "Degraded",
    reconciledAt: "2s ago",
    nodes: 4,
    pods: 8,
    activePods: 7,
    flightRules: 87,
    pdb: { maxUnavailable: "30%", currentUnavailable: 1, budget: "OK" },
    daemonSet: { desired: 4, ready: 4 },
    strategy: "C (Promoted)",
    networkPolicy: "ISOLATED",
  },
  recovery: {
    syncStatus: "Syncing",
    healthStatus: "Recovering",
    reconciledAt: "10s ago",
    nodes: 4,
    pods: 8,
    activePods: 8,
    flightRules: 89,
    pdb: { maxUnavailable: "30%", currentUnavailable: 0, budget: "OK" },
    daemonSet: { desired: 4, ready: 4 },
    strategy: null,
    networkPolicy: "OPEN",
  },
};

// ─── K8s POD PROBES ─────────────────────────────────────────────────────────
// Liveness = "is it alive?", Readiness = "is it harvestable?"

export const POD_PROBES = {
  Soybean:     { liveness: "passing", livenessAge: "30s", readiness: "notReady", readinessDetail: "Harvest in 30 sols", restarts: 0, startedSol: 187 },
  Lentil:      { liveness: "passing", livenessAge: "30s", readiness: "notReady", readinessDetail: "Harvest in 25 sols", restarts: 0, startedSol: 192 },
  Potato:      { liveness: "passing", livenessAge: "28s", readiness: "notReady", readinessDetail: "Harvest in 40 sols", restarts: 0, startedSol: 197 },
  Wheat:       { liveness: "passing", livenessAge: "30s", readiness: "notReady", readinessDetail: "Harvest in 35 sols", restarts: 0, startedSol: 182 },
  Tomato:      { liveness: "passing", livenessAge: "31s", readiness: "approaching", readinessDetail: "Harvest in 20 sols", restarts: 0, startedSol: 177 },
  Spinach:     { liveness: "passing", livenessAge: "29s", readiness: "ready", readinessDetail: "Harvest in 7 sols", restarts: 0, startedSol: 219 },
  Basil:       { liveness: "passing", livenessAge: "30s", readiness: "approaching", readinessDetail: "Harvest in 10 sols", restarts: 0, startedSol: 212 },
  Microgreens: { liveness: "passing", livenessAge: "30s", readiness: "ready", readinessDetail: "Harvest in 6 sols", restarts: 0, startedSol: 239 },
};

// Crisis overrides for specific pods
export const POD_PROBES_CRISIS = {
  ...POD_PROBES,
  Wheat:   { liveness: "degraded", livenessAge: "5s", readiness: "notReady", readinessDetail: "STRESSED \u2014 flowering disrupted", restarts: 0, startedSol: 182 },
  Spinach: { liveness: "terminated", livenessAge: "N/A", readiness: "terminated", readinessDetail: "PRE-HARVESTED \u2014 1.9kg secured", restarts: 0, startedSol: 219 },
  Tomato:  { liveness: "degraded", livenessAge: "8s", readiness: "notReady", readinessDetail: "Growth paused \u2014 survival mode", restarts: 0, startedSol: 177 },
};

// ─── K8s EVENTS (kubectl get events) ────────────────────────────────────────

export const EVENTS_NOMINAL = [
  { age: "10s", type: "Normal",  reason: "LivenessProbe",   object: "pod/soybean",     message: "Sensors nominal. Health 91%." },
  { age: "30s", type: "Normal",  reason: "Reconciled",      object: "cluster/eden",    message: "Desired state matches actual. Synced." },
  { age: "1m",  type: "Normal",  reason: "CronJob",         object: "dreamer/nightly", message: "Dream cycle: 4,217 scenarios. 3 rules proposed." },
  { age: "2m",  type: "Warning", reason: "VPDDrift",        object: "node/vitamin",    message: "VPD 0.88 below target 1.0 kPa." },
  { age: "5m",  type: "Normal",  reason: "AdmissionCtrl",   object: "rule/FR-H-003",  message: "Armed: VPD correction monitor." },
  { age: "8m",  type: "Normal",  reason: "RollingUpdate",   object: "node/vitamin",    message: "Spinach cycle 5 initiated." },
  { age: "12m", type: "Normal",  reason: "LivenessProbe",   object: "pod/wheat",       message: "Sensors nominal. BBCH 55." },
  { age: "15m", type: "Normal",  reason: "DaemonSet",       object: "sensors/all",     message: "4/4 zone sensors reporting." },
];

export const EVENTS_CRISIS = [
  { age: "0s",  type: "Warning", reason: "CMEDetected",     object: "cluster/eden",    message: "CME-2026-0315. Speed: 1,247 km/s. Mars ETA: 50.7h." },
  { age: "1s",  type: "Normal",  reason: "AdmissionCtrl",   object: "rule/FR-CME-001", message: "ADMITTED: CME speed 1247 > threshold 800." },
  { age: "2s",  type: "Normal",  reason: "AdmissionCtrl",   object: "rule/FR-CME-002", message: "ADMITTED: CME ETA 50.7h < 72h threshold." },
  { age: "3s",  type: "Normal",  reason: "CanaryCreate",    object: "strategy/C",      message: "Simulating: pre-emptive full protocol." },
  { age: "5s",  type: "Normal",  reason: "CanaryPromote",   object: "strategy/C",      message: "3% predicted loss. PROMOTED to production." },
  { age: "8s",  type: "Warning", reason: "NetworkPolicy",   object: "node/carb",       message: "ISOLATED: Condition Zebra. Cross-zone sharing suspended." },
  { age: "10s", type: "Warning", reason: "Triage",          object: "pod/wheat",       message: "RED: Intervening. BBCH 60 radiation vulnerability." },
  { age: "12s", type: "Warning", reason: "PDBViolation",    object: "node/vitamin",    message: "50% unavailable > 30% budget. Spinach pre-harvested." },
  { age: "15s", type: "Normal",  reason: "PreHarvest",      object: "pod/spinach",     message: "1.9 kg secured in cold storage." },
  { age: "18s", type: "Normal",  reason: "StressHarden",    object: "pod/wheat",       message: "EC adjusted +0.4 mS/cm per Syngenta KB." },
  { age: "20s", type: "Normal",  reason: "Stockpile",       object: "resource/water",  message: "Desal at MAX. Target: 580L in 48h." },
  { age: "25s", type: "Warning", reason: "CMEImpact",       object: "cluster/eden",    message: "Radiation spike: 263 \u00B5Sv/hr. Solar: 30%." },
];

export const EVENTS_RECOVERY = [
  { age: "0s",  type: "Normal",  reason: "StormClearing",   object: "cluster/eden",    message: "Radiation returning to baseline. Solar: 91%." },
  { age: "5s",  type: "Normal",  reason: "PostEventDebrief",object: "dreamer/oracle",  message: "Predicted: 3.0% loss. Actual: 2.7%. Model accuracy: 90%." },
  { age: "10s", type: "Normal",  reason: "FlightRuleCreate",object: "rule/FR-CME-012", message: "IF cme>1000 + BBCH 55-70 THEN pre-harvest leafy greens." },
  { age: "15s", type: "Normal",  reason: "FlightRuleCreate",object: "rule/FR-CME-013", message: "IF cme_eta>55h THEN begin stockpiling (was 48h)." },
  { age: "20s", type: "Normal",  reason: "Reconciled",      object: "cluster/eden",    message: "Rules: 87 \u2192 89. System improving. Synced." },
  { age: "30s", type: "Normal",  reason: "NetworkPolicy",   object: "node/carb",       message: "OPEN: Condition Zebra lifted. Cross-zone sharing resumed." },
];

// ─── K8s RESOURCE QUOTAS (per zone) ─────────────────────────────────────────

export const RESOURCE_QUOTAS = {
  A: { water: { used: 1.75, limit: 3.0 }, light: { used: 82, limit: 100 }, nutrients: { used: 1.8, limit: 3.0 }, space: { used: 20, limit: 30 } },
  B: { water: { used: 2.35, limit: 3.5 }, light: { used: 78, limit: 100 }, nutrients: { used: 1.5, limit: 3.0 }, space: { used: 24, limit: 30 } },
  C: { water: { used: 2.0,  limit: 3.5 }, light: { used: 88, limit: 100 }, nutrients: { used: 2.2, limit: 3.0 }, space: { used: 18, limit: 25 } },
  D: { water: { used: 0.8,  limit: 2.0 }, light: { used: 65, limit: 100 }, nutrients: { used: 1.2, limit: 3.0 }, space: { used: 8,  limit: 15 } },
};

// ─── K8s TRIAGE COLORS (per zone per state) ─────────────────────────────────

export const ZONE_TRIAGE = {
  nominal:  { A: null, B: null, C: null, D: null },
  alert:    { A: null, B: "amber", C: "amber", D: null },
  crisis:   { A: "GREEN", B: "RED", C: "YELLOW", D: "GREEN" },
  recovery: { A: null, B: "recovering", C: "recovering", D: null },
};

// ─── RESOURCE FLOW NODES (Hubble-style) ─────────────────────────────────────

export const RESOURCE_FLOW = {
  nominal: {
    solar:      { label: "Solar Panels", value: "4.2 kW", pct: 100, status: "nominal" },
    power:      { label: "Power Grid", value: "78%", pct: 78, status: "nominal" },
    desal:      { label: "Desalination", value: "120 L/sol", pct: 100, status: "nominal" },
    irrigation: { label: "Irrigation", value: "4 zones", pct: 100, status: "nominal" },
    lights:     { label: "Grow Lights", value: "Active", status: "nominal" },
    heating:    { label: "Dome Heating", value: "22\u00B0C", status: "nominal" },
    shields:    { label: "Shields", value: "Standby", status: "standby" },
    battery:    { label: "Battery", value: "78%", pct: 78, status: "nominal" },
    harvest:    { label: "Harvest Output", value: "Nominal", status: "nominal" },
    crew:       { label: "Crew (4)", vitC: "133%", iron: "112%", o2: "14.2%", status: "nominal" },
    ingress:    { label: "Ingress", sources: ["Syngenta KB", "DONKI", "InSight", "NASA POWER"] },
  },
  crisis: {
    solar:      { label: "Solar Panels", value: "1.26 kW", pct: 30, status: "degraded" },
    power:      { label: "Power Grid", value: "45%", pct: 45, status: "critical" },
    desal:      { label: "Desalination", value: "36 L/sol", pct: 30, status: "degraded" },
    irrigation: { label: "Irrigation", value: "Reduced", pct: 50, status: "degraded" },
    lights:     { label: "Grow Lights", value: "Minimum", status: "degraded" },
    heating:    { label: "Dome Heating", value: "18\u00B0C", status: "degraded" },
    shields:    { label: "Shields", value: "ACTIVE", status: "critical" },
    battery:    { label: "Battery", value: "45%", pct: 45, status: "critical" },
    harvest:    { label: "Harvest Output", value: "Paused", status: "degraded" },
    crew:       { label: "Crew (4)", vitC: "128%", iron: "108%", o2: "11.8%", status: "warning" },
    ingress:    { label: "Ingress", sources: ["Syngenta KB", "DONKI", "InSight", "NASA POWER"] },
  },
};

// ─── CANARY DEPLOYMENT (strategies as K8s canary) ───────────────────────────

export const CANARY_DEPLOYMENT = {
  active: true,
  strategies: [
    { name: "A \u2014 Do Nothing", loss: 40, status: "rejected", color: "#ef4444" },
    { name: "B \u2014 Standard Survival", loss: 12, status: "suboptimal", color: "#f59e0b" },
    { name: "C \u2014 Pre-emptive Full Protocol", loss: 3, status: "promoted", color: "#22c55e" },
  ],
  promoted: "C",
  rolloutPct: 80,
  confidence: 87,
  source: "Syngenta KB stress data",
};

// ─── RECONCILIATION DIFF (desired vs actual) ────────────────────────────────

export const RECONCILIATION = {
  nominal: [
    { field: "Pods running", desired: "8", actual: "8", status: "synced" },
    { field: "Min health", desired: "> 85%", actual: "86% (Tomato)", status: "synced" },
    { field: "Water reserve", desired: "> 300L", actual: "340L", status: "synced" },
    { field: "VitC coverage", desired: "> 100%", actual: "133%", status: "surplus" },
    { field: "Iron coverage", desired: "> 100%", actual: "72% (Chen)", status: "drift" },
  ],
  crisis: [
    { field: "Pods running", desired: "8", actual: "7 (Spinach harvested)", status: "outOfSync" },
    { field: "Min health", desired: "> 85%", actual: "72% (Wheat)", status: "outOfSync" },
    { field: "Water reserve", desired: "> 300L", actual: "260L", status: "outOfSync" },
    { field: "Solar output", desired: "> 80%", actual: "30%", status: "outOfSync" },
    { field: "Shield status", desired: "Active", actual: "Active", status: "synced" },
    { field: "Strategy", desired: "C deployed", actual: "C running", status: "synced" },
  ],
};
