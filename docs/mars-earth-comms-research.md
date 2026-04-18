# Mars-Earth Communication Infrastructure: Real Data

Research compiled 2026-03-19 for AstroFarm hackathon.

---

## 1. Deep Space Network (DSN)

**Three ground stations, ~120 degrees apart for continuous coverage:**
- **Goldstone** — near Barstow, California, USA
- **Madrid Deep Space Communications Complex** — near Madrid, Spain
- **Canberra Deep Space Communication Complex** — near Canberra, Australia

**Antenna sizes:**
- **70-meter dishes** (one per complex) — the largest and most sensitive; capable of tracking spacecraft tens of billions of miles from Earth
- **34-meter dishes** (multiple per complex) — workhorse antennas, newer beam-waveguide (BWG) designs

**Frequency bands used for Mars missions:**
- **S-band** (~2 GHz) — legacy, low data rate
- **X-band** (~8 GHz) — primary for most Mars missions
- **Ka-band** (~32 GHz) — higher bandwidth, used by MRO; more susceptible to weather

**Data rates (direct-to-Earth from rover X-band):**

| Link | 34m DSN antenna | 70m DSN antenna |
|------|----------------|----------------|
| Perseverance uplink (Earth→Mars) | 160 bps | 800 bps |
| Perseverance downlink (Mars→Earth) | 500 bps | 3,000 bps |
| Low-gain antenna (receive only) | ~10 bps | ~30 bps |

These X-band direct rates are **extremely slow** — used mainly for emergency commands, not bulk data transfer. Bulk data goes through relay orbiters.

**Sources:** [NASA Perseverance Rover Components](https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/), [NASA DSN About](https://www.nasa.gov/directorates/heo/scan/services/networks/deep_space_network/about)

---

## 2. Mars Relay Orbiters — Surface-to-Orbit UHF Relay

The **Mars Relay Network (MRN)** consists of five orbiters that relay data from surface assets (rovers/landers) to Earth:

| Orbiter | Agency | Arrived | Avg Daily Relay Volume | Notes |
|---------|--------|---------|----------------------|-------|
| **Mars Odyssey (ODY)** | NASA | 2001 | 170.4 Mb/day | Oldest active relay |
| **Mars Express (MEX)** | ESA | 2003 | Backup | Emergency/backup relay |
| **Mars Reconnaissance Orbiter (MRO)** | NASA | 2005 | 447.5 Mb/day | Has Ka-band for high-rate Earth link |
| **MAVEN (MVN)** | NASA | 2013 | 897.5 Mb/day | Electra UHF relay package (6.5 kg) |
| **ExoMars Trace Gas Orbiter (TGO)** | ESA | 2016 | 1,562.7 Mb/day | Currently highest-volume relay |

**Surface-to-orbiter UHF link rate: up to 2 Mbps** (2 million bits per second)

**Relay pass frequency:** 2-4 passes per rover per orbiter per day. The MRN returns rover data to scientists "about a dozen times a week — each gigabit containing one billion bits of data."

**MRO total data throughput:** MRO's instruments alone can generate 40-90 Gb/day for downlink (with SHARAD getting ~15% allocation). HiRISE camera can acquire 28 Gb in 6 seconds. MARCI provides ~6.2 Gb/day of full-resolution global imagery.

**Key insight:** Rovers lack line-of-sight to Earth for ~12 hours per day, making relay orbiters essential.

**Sources:** [NASA Mars Relay Network Update](https://science.nasa.gov/mars/mars-relay-network-update/), [NASA MRO Instruments](https://science.nasa.gov/mission/mars-reconnaissance-orbiter/science-instruments/)

---

## 3. Actual Communication Latency (One-Way Light Time)

The "22-minute" figure is only the maximum. The real range depends on orbital positions:

| Orbital Position | Distance | One-Way Light Time |
|-----------------|----------|-------------------|
| **Closest approach (opposition)** | ~56 million km (0.37 AU) | **~3.1 minutes** |
| **Average distance** | ~225 million km (1.5 AU) | **~12.5 minutes** |
| **Maximum distance (conjunction)** | ~400 million km (2.67 AU) | **~22.3 minutes** |

**Round-trip signal time:** 6.2 to 44.6 minutes.

For the hackathon's 450-day mission, the crew would experience the **full range** of latencies as Mars and Earth move through their orbits. The synodic period (time between oppositions) is ~780 days (2 years 50 days).

**Sources:** [Britannica Mars](https://www.britannica.com/science/Mars-planet/Mars-in-the-sky), [NASA Mars Facts](https://science.nasa.gov/mars/facts/)

---

## 4. Communication Windows

**Per-sol contact availability:**
- Each DSN complex can see Mars for **8-12 hours per sol** (depending on Mars's declination)
- With 3 complexes spaced ~120 degrees, there is **near-continuous coverage** — but not every antenna is available (DSN is shared across 30+ missions)
- In practice, a Mars mission gets **scheduled DSN time**, typically a few hours per sol for direct downlink
- Relay orbiter passes: **2-4 overhead passes per orbiter per sol**, each lasting ~8-15 minutes
- Rovers have no line-of-sight to Earth for ~12 hours/day (Mars rotation)

**Typical daily data budget for Perseverance:**
- Via UHF relay through MRO/MAVEN/TGO: **primary method**, 100s of Mb per sol
- Via X-band direct: only used for low-rate commands/telemetry

**MRO's Earth downlink capacity** (orbiter-to-Earth via HGA):
- X-band: up to ~2 Mbps (varies with distance)
- Ka-band: up to ~6 Mbps at closest approach
- At maximum distance: rates drop to ~0.5-1 Mbps

---

## 5. Mars Solar Conjunction (Blackout)

When Mars passes behind the Sun (as seen from Earth):

- **Duration:** Approximately **2 weeks** (some sources say up to 2-3 weeks for degraded comms)
- **Total communications moratorium:** NASA stops sending commands when Mars is within ~2 degrees of the Sun (risk of solar interference corrupting commands)
- **Frequency:** Occurs every **~26 months** (every synodic period)
- **What missions do:**
  - Pre-conjunction: upload 2+ weeks of autonomous command sequences
  - During: rovers execute pre-loaded routines, limited to safe activities (weather monitoring, stationary science)
  - Orbiters continue autonomous operations
  - No new commands are sent; telemetry may still trickle through but is unreliable
  - Post-conjunction: full link re-established, backlog data downloaded

**For a 450-day mission, conjunction would occur once** (maybe at the edges of a second one).

**This is the strongest argument for autonomous AI on Mars** — even outside conjunction, latency makes real-time control impossible, and during conjunction, Earth is completely unreachable.

---

## 6. Future Plans: Laser Communication (DSOC)

NASA's **Deep Space Optical Communications (DSOC)** technology demo flew on the Psyche mission (2023-2025) and achieved groundbreaking results:

| Distance | Max Data Rate | Notes |
|----------|--------------|-------|
| 19 million miles (31M km) | **267 Mbps** | Faster than most broadband internet |
| 140 million miles | **25 Mbps** | With Psyche's comm system |
| **249 million miles (Mars-like distance)** | **8.3 Mbps** | 2.7 AU from Earth |
| 288 million miles | Signal verified | Uplink commands successful |

**Comparison to RF:**
- DSOC aims for **10-100x improvement** over state-of-the-art RF systems
- In a single night of operations, DSOC downloaded **1.3 terabits** — more than the entire Magellan Venus mission returned over 4 years (1.2 Tb total, 1990-1994)
- The demo ran for 2 years across 65 passes and "surpassed all technical goals"

**At Mars distance (8.3 Mbps), DSOC could transfer:**
- ~90 GB per day (at sustained max rate)
- Compare to MRO's RF relay of ~0.5-1 GB/day

**Status:** Technology demo completed September 2025. Not yet operational on any Mars mission. Future deployment would require ground-based optical receivers (the demo used Palomar Observatory's Hale Telescope).

**Sources:** [NASA DSOC](https://www.nasa.gov/technology/space-comms/optical-communications/nasas-tech-demo-streams-first-video-from-deep-space-via-laser/), [NASA DSOC page](https://www.nasa.gov/technology/space-comms/optical-communications/deep-space-optical-communications-dsoc/)

---

## 7. What Does This Mean for Data Transfer? (Practical Implications for AstroFarm)

### Current RF-based infrastructure (what a near-future mission would have):

| Metric | Value |
|--------|-------|
| Rover direct-to-Earth (X-band) | 500-3,000 bps downlink |
| Rover-to-orbiter (UHF relay) | Up to 2 Mbps |
| Orbiter-to-Earth (X-band/Ka-band) | 0.5-6 Mbps (distance-dependent) |
| Total data per sol (all relay passes combined) | **~0.25 - 2 GB** (varies by distance and scheduling) |
| DSN availability for one mission | A few hours per sol (shared resource) |
| One-way latency | 3.1 - 22.3 minutes |
| Round-trip latency | 6.2 - 44.6 minutes |
| Conjunction blackout | ~2 weeks, every ~26 months |

### Could you sync LLM model weights?

| Model | Size | Transfer Time (at 2 Mbps relay) | Transfer Time (at 1 Mbps Earth link) |
|-------|------|-------------------------------|-------------------------------------|
| Small model (1B params, quantized) | ~0.5 GB | ~33 min relay to orbiter | ~1.1 hours Earth downlink |
| Medium model (7B params, quantized) | ~4 GB | ~4.4 hours | ~8.9 hours |
| Large model (70B params, quantized) | ~35 GB | ~39 hours | ~3.2 days |
| Full frontier model (400B+) | ~200 GB+ | **Not feasible** | ~18+ days |

**Verdict:** You could sync a small quantized model (~1B params) within a single sol's communication window. A 7B model would take most of a sol's bandwidth allocation. Anything larger would require multiple sols of dedicated bandwidth — and you'd be competing with mission-critical science data.

### Could you send/receive LLM prompts?

| Content | Size | Transfer Time (1 Mbps) |
|---------|------|----------------------|
| Text prompt (1000 tokens) | ~4 KB | ~0.03 seconds |
| Text response (4000 tokens) | ~16 KB | ~0.13 seconds |
| Prompt + response roundtrip | ~20 KB | Bandwidth: trivial. **Latency: 6-45 min roundtrip** |

**Verdict:** Bandwidth for text prompts is trivial — the bottleneck is **latency**. A single prompt-response cycle takes 6-45 minutes depending on orbital position. You could send hundreds of prompts per sol bandwidth-wise, but each one has that latency tax. This makes interactive use impossible but batch queries feasible.

### With future DSOC laser (8.3 Mbps at Mars distance):

| Metric | Value |
|--------|-------|
| Data per hour | ~3.7 GB |
| Data per sol (8 hours contact) | **~30 GB** |
| 7B quantized model sync | ~8 minutes |
| 70B quantized model sync | ~1.2 hours |

DSOC would make model weight syncing **practical** for most model sizes.

---

## Summary Table for Quick Reference

| Parameter | Value |
|-----------|-------|
| One-way light time (min) | 3.1 min |
| One-way light time (max) | 22.3 min |
| One-way light time (avg) | ~12.5 min |
| Round-trip (min) | 6.2 min |
| Round-trip (max) | 44.6 min |
| Rover X-band direct (downlink) | 500-3,000 bps |
| Rover UHF to orbiter | up to 2 Mbps |
| MRO to Earth (X-band) | ~2 Mbps |
| MRO to Earth (Ka-band) | up to ~6 Mbps |
| DSOC at Mars distance | 8.3 Mbps (demo) |
| Total data per sol (current RF) | ~0.25-2 GB |
| Relay passes per sol per orbiter | 2-4 passes |
| Conjunction blackout | ~2 weeks every ~26 months |
| DSN antenna sizes | 34m and 70m dishes |
| DSN locations | Goldstone, Madrid, Canberra |

---

## Key Sources

- NASA Perseverance Rover Components: https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/
- NASA Mars Relay Network: https://science.nasa.gov/mars/mars-relay-network-update/
- NASA MRO Instruments: https://science.nasa.gov/mission/mars-reconnaissance-orbiter/science-instruments/
- NASA DSOC: https://www.nasa.gov/technology/space-comms/optical-communications/deep-space-optical-communications-dsoc/
- NASA DSOC Video Demo: https://www.nasa.gov/technology/space-comms/optical-communications/nasas-tech-demo-streams-first-video-from-deep-space-via-laser/
- NASA DSN About: https://www.nasa.gov/directorates/heo/scan/services/networks/deep_space_network/about
- NASA Mars Facts: https://science.nasa.gov/mars/facts/
- Britannica Mars: https://www.britannica.com/science/Mars-planet/Mars-in-the-sky
