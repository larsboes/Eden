# API Cache - EDEN Mars Greenhouse Project

Probed on: 2026-03-19

These cached JSON files provide real API response data for the dashboard's replay/fallback mode when live API calls are unavailable (e.g., Mars communication latency simulation).

---

## API Status Summary

| API | Status | File | Size |
|-----|--------|------|------|
| NASA DONKI CME | OK | `donki-cme-2026.json` | 693 KB |
| NASA DONKI MPC | OK | `donki-mpc-2026.json` | 1.7 KB |
| NASA InSight Weather | OK | `insight-weather.json` | 36 KB |
| JPL Close Approach | OK | `jpl-mars-approaches.json` | 17 KB |
| Syngenta MCP Tools | OK | `syngenta-mcp-tools.json` | - |
| Syngenta MCP KB Examples | OK | `syngenta-kb-examples.json` | - |

All 5 APIs responded successfully. No auth issues encountered.

---

## Task 1: DONKI CME (Coronal Mass Ejections)

- **Endpoint:** `https://api.nasa.gov/DONKI/CME`
- **Date range:** 2026-01-01 to 2026-03-19
- **Total CME events:** 370
- **All 370 events have analysis data**
- **Speed range:** 165 - 1,820 km/s
- **Average speed:** 526 km/s
- **Total speed measurements:** 399 (some events have multiple analyses)
- **Half-angle/location data available** - e.g., CME 2026-01-01T19:36 had halfAngle=35, lat=22, lon=-9, speed=628 km/s
- **Use case:** Feed radiation alert system; CMEs with speeds >1000 km/s and Earth/Mars-directed half-angles trigger greenhouse shielding protocols

## Task 2: DONKI MPC (Mars Magnetopause Crossings)

- **Endpoint:** `https://api.nasa.gov/DONKI/MPC`
- **Date range:** 2026-01-01 to 2026-03-19
- **Total Mars events:** 3
- **All 3 are linked to CME activity:**
  1. 2026-01-11 - linked to 4 CMEs from Jan 8 + geomagnetic storm + interplanetary shock
  2. 2026-01-19 - linked to 1 CME from Jan 18 + geomagnetic storm + interplanetary shock
  3. 2026-02-05 - linked to 1 CME from Feb 2 + interplanetary shock
- **Use case:** Direct evidence of solar weather impacting Mars magnetosphere; correlate with CME data for predictive radiation alerts

## Task 3: InSight Mars Weather

- **Endpoint:** `https://api.nasa.gov/insight_weather/`
- **Data period:** Sol 675-681 (frozen at Oct 2020, InSight mission ended Dec 2022)
- **Temperature ranges (real Mars surface data):**
  - Min: -97.7C (Sol 678)
  - Max: -4.4C (Sol 681)
  - Average: ~ -62.5C
- **Pressure:** 717-769 Pa (avg ~746 Pa = 7.46 mbar)
- **Wind:** 0.2 - 26.9 m/s (avg 5-9 m/s)
- **Use case:** Real Mars baseline values for greenhouse thermal management simulation. Confirms Mars environment doc values (-140 to +21C range, 6-7 mbar pressure)

## Task 4: Syngenta MCP Knowledge Base

- **Endpoint:** `https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp`
- **Protocol:** MCP (Model Context Protocol) via streamable HTTP, protocol version 2025-03-26
- **Server:** `kb-start-hack-gateway` v1.0.0
- **Auth:** None required (open endpoint)
- **Available tools:** 1 tool
  - `kb-start-hack-target___knowledge_base_retrieve` - retrieves relevant chunks from the knowledge base
  - Params: `query` (string, required), `max_results` (integer, optional, default 5)

### Knowledge Base Documents Discovered (6 documents found):
1. `01_Mars_Environment_Extended.md` - Mars physical constraints (temp, pressure, radiation, gravity)
2. `02_Controlled_Environment_Agriculture_Principles.md` - CEA/hydroponics principles
3. `03_Crop_Profiles_Extended.md` - Crop profiles (lettuce, potato, radish, beans/peas, herbs)
4. `04_Plant_Stress_and_Response_Guide.md` - 7 abiotic stress categories + AI response logic
5. `05_Human_Nutritional_Strategy.md` - Crew nutrition (12,000 kcal/day for 4 astronauts)
6. `07_From_Mars_to_Earth_Innovation_Impact.md` - Innovation transfer to Earth agriculture

### Key Agricultural Parameters from KB:
- Greenhouse temps: 15-22C (leafy), 16-20C (potato), 18-25C (legumes)
- Humidity: 50-70% RH
- CO2: 800-1200 ppm optimal
- PAR: 150-400 umol/m2/s depending on crop
- pH: 5.5-6.5
- Portfolio: 40-50% potatoes, 20-30% legumes, 15-20% leafy greens, 5-10% herbs/radish
- Crew needs: ~3,000 kcal/astronaut/day, 90-135g protein/astronaut/day

## Task 5: JPL Close Approach Data

- **Endpoint:** `https://ssd-api.jpl.nasa.gov/cad.api`
- **Query:** Objects approaching Mars, 2025-2027
- **Total close approaches:** 96 objects
- **Fields:** designation, orbit_id, julian_date, calendar_date, distance (AU), min/max distance, relative velocity, H magnitude
- **Notable:** Multiple near-Earth asteroids making close Mars approaches, velocities ranging ~5-15 km/s
- **Use case:** Easter egg data for dashboard; asteroid proximity alerts for the greenhouse scenario

---

## Replay Mode Usage

All files can serve as fallback data when live APIs are unreachable:

```javascript
// Example: load cached CME data
const cmeData = await fetch('/data/api-cache/donki-cme-2026.json').then(r => r.json());

// Example: load cached Mars weather
const weather = await fetch('/data/api-cache/insight-weather.json').then(r => r.json());

// Example: query Syngenta KB (requires live MCP connection)
// Fallback: use syngenta-kb-examples.json for pre-cached responses
```

## API Keys & Auth

- **NASA APIs:** Key `YOUR_NASA_API_KEY` (rate limited)
- **JPL SSD API:** No key required
- **Syngenta MCP:** No auth required, uses MCP JSON-RPC protocol
