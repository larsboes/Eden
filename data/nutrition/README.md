# EDEN Nutritional Model (KB-Aligned v2.0)

Data powering the VITA agent's reasoning and the dashboard's Nutrition panel. Aligned with Syngenta Knowledge Base crop recommendations.

## Files

| File | Purpose |
|------|---------|
| `crop-profiles.json` | 7 crop profiles with USDA nutrition, CEA growth params, BBCH stages, stress data |
| `crew-requirements.json` | Syngenta KB + NASA-based daily requirements per astronaut, crew roster with preferences |
| `mission-projection.json` | Computed yield vs requirement across 450 sols, gap analysis, harvest timeline |
| `triage-scenarios.json` | 5 pre-computed failure scenarios with nutritional deltas and crew impact |
| `crop-selection-rationale.json` | Why this crop mix was chosen, KB alignment evidence, deviation explanations |

## Syngenta KB Crop Allocation

| Zone | Area | KB Target | Crops | Status |
|------|------|-----------|-------|--------|
| Caloric | 45m2 (45%) | 40-50% | Potato | Aligned |
| Protein | 25m2 (25%) | 20-30% beans/legumes | Soybean + Lentil | Aligned |
| Leafy Green | 18m2 (18%) | 15-20% | Lettuce + Spinach | Aligned |
| Quick Harvest | 7m2 (7%) | 5-10% | Radish | Aligned |
| Support | 5m2 (5%) | Herbs included | Basil + Microgreens | Aligned |

## Key Numbers

| Metric | Value |
|--------|-------|
| Mission duration | 450 sols |
| Crew size | 4 astronauts |
| Calorie baseline | 3,000 kcal/person/day (Syngenta KB) |
| Total calorie requirement | 5,400,000 kcal |
| Greenhouse area | 100m2 (5 zones) |
| Total projected yield | 1,837.3 kg fresh food |
| Calorie coverage | 17.7% (greenhouse supplements stored food) |
| First fresh food | Sol 25 (radish) |

## Nutritional Coverage Summary

| Nutrient | Coverage | Status |
|----------|----------|--------|
| Vitamin K | 729.0% | Massive surplus (spinach + lettuce + basil) |
| Vitamin C | 193.7% | Large surplus (potato alone covers 109%) |
| Iron | 146.9% | Surplus (low bioavailability caveat — effective ~40-60%) |
| Folate | 139.6% | Surplus (leafy greens + legumes) |
| Fiber | 81.5% | Near self-sufficient |
| Protein | 37.8% | Moderate gap — stored rations required |
| Calcium | 34.2% | Gap — oxalates reduce spinach absorption by ~75% |
| Carbs | 31.2% | Moderate gap — major improvement from v1 (18.9%) |
| Calories | 17.7% | Expected gap — greenhouse supplements, not replaces |
| Fat | 5.2% | Critical gap — only soybean produces meaningful fat |
| Vitamin D | 0% | Critical — no plant produces Vitamin D, supplements mandatory |

## Crop Yield Breakdown

| Crop | Zone | Area | Cycles | Total Yield | Primary Contribution |
|------|------|------|--------|-------------|---------------------|
| Potato | Caloric | 45m2 | 4 | 900.0 kg | Calories (72.3%), Carbs (80.1%), Vitamin C (56.5%) |
| Lettuce | Leafy Green | 10m2 | 11 | 440.0 kg | Vitamin K (35.3%), Folate (31.9%), Calcium (25.7%) |
| Radish | Quick Harvest | 7m2 | 15 | 262.5 kg | First harvest Sol 25, Fiber (11.5%), Morale anchor |
| Spinach | Leafy Green | 8m2 | 9 | 180.0 kg | Vitamin K (55.2%), Folate (34.7%), Iron (23.0%) |
| Basil | Support | 3m2 | 12 | 28.8 kg | Antifungal VOCs (potato protection), Vitamin K (7.6%) |
| Soybean | Protein | 15m2 | 4 | 18.0 kg | Fat (54.2%), Protein (16.1%), Iron (13.4%) |
| Lentil | Protein | 10m2 | 4 | 8.0 kg | Folate (3.8%), Protein (5.1%) |

## Changes from v1.0

| Change | Reason |
|--------|--------|
| Dropped Wheat | Not in KB crop list. Potato 10x more efficient per m2. |
| Dropped Tomato | Not in KB primary list. Vitamin C covered by potato (109% alone). |
| Added Lettuce | KB recommends leafy greens. Vitamin K + folate powerhouse. |
| Added Radish | KB recommends 5-10%. First harvest Sol 25 (morale). |
| Potato 15m2 -> 45m2 | KB says 40-50% = caloric backbone. |
| Calorie baseline 2,500 -> 3,000 | Syngenta KB value (higher than NASA ISS standard). |

## Design Decisions

1. **Nutritional values use USDA FoodData Central** for the form astronauts consume (dried legumes, raw vegetables)
2. **Growth parameters reflect CEA hydroponics**, not field agriculture — shorter cycles, higher yields
3. **100m2 greenhouse is a supplement, not sole food source** — consistent with NASA BIO-Plex research
4. **Vitamin C and Vitamin K are the greenhouse's nutritional strongholds** — surpluses provide safety margin
5. **Potato is the caloric backbone** at 45% of area — KB-aligned, produces 72.3% of all greenhouse calories
6. **Soybean is mission-critical for fat** — only meaningful fat source, loss triggers stored-fat protocols
7. **Radish is the morale crop** — first fresh food at Sol 25, fastest turnaround, psychological milestone
8. **Basil has dual role** — culinary herb AND biological pest management (antifungal VOCs)
9. **Spinach calcium discounted by oxalate binding** — effective absorption ~25% of nominal value
10. **Water budget accounts for transpiration recycling** at 65% efficiency — net 91.9 L/sol within 120 L/sol capacity
11. **Triage scenarios reference crew preferences** for VITA agent's human-centered decision making

## How VITA Uses This Data

1. **Real-time monitoring**: Compare current growth stage (BBCH) against expected timeline
2. **Gap alerts**: When projected coverage drops below threshold, trigger Council discussion
3. **Triage decisions**: Match current crisis to pre-computed scenarios for rapid response
4. **Crew nutrition tracking**: Apply individual calorie modifiers and dietary flags
5. **Harvest scheduling**: Use timeline to plan crew meal rotations around fresh food availability
6. **Companion planting**: Monitor basil VOC protection for potato zone, N-fixation in protein zone
