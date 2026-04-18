# EDEN — The Complete Storyline

> **This is the ONE document.** Read this before the pitch. Everything else is reference material.

---

## What We Built (one paragraph)

EDEN is an autonomous closed-loop agricultural system for a Martian greenhouse. Real sensors on a real plant feed data to AI agents that reason with Syngenta's crop science knowledge base, predict threats before they arrive, debate tradeoffs transparently, act on the physical environment, measure the results, and write new operational rules from experience. The system gets smarter every day without human intervention — because on Mars, 22 minutes from Earth, it has to.

---

## The Closed Loop (our architecture in one diagram)

Borrowed from AWS's proven closed-loop operations pattern (Bedrock + SageMaker, used by Deutsche Telekom for cloud-native IMS):

```
    ┌──────────────────────────────────────────────────────┐
    │                                                      │
    ▼                                                      │
 OBSERVE          PREDICT           DECIDE           ACT   │
 ───────          ───────           ──────           ───   │
 Real sensors     Simulation        Agent Council    Actuators
 on real plant    engine runs       5 specialists    (LEDs, fan,
 (Pi: temp,       100 scenarios     debate with      pump, heat)
 humidity,        using Syngenta    visible          Commands sent
 soil, light)     KB parameters     reasoning        to physical
                  (GDD, Liebig's                     environment
                  Law, VPD)
    │                                                      │
    │              MEASURE ◄──────────── LEARN             │
    │              ───────               ─────             │
    │              Compare               Write new         │
    │              predicted vs          flight rule        │
    │              actual outcome        from evidence      │
    │                                                      │
    └──────────────────────────────────────────────────────┘
                    CLOSED LOOP
           "Gets smarter every cycle"
```

**What makes this a REAL closed loop (not just a dashboard):**
- Sensors read the REAL plant → agent reasons → actuators change the REAL environment → sensors measure the change → agent learns from the delta
- Not simulated. The basil plant on the table is IN the loop right now.

---

## How We Address Every Challenge Requirement

### 1. Monitor and Control the Environment
*"Maintain optimal conditions for plant growth (temperature, humidity, light, water)"*

**What we built:**
- Raspberry Pi with DHT22 (temp + humidity), capacitive soil moisture sensor, BH1750 light sensor — reading every 10 seconds
- LED grow lights + fan controllable by agent commands
- Dashboard shows real-time sensor data with green/amber/red status
- Flight rules provide deterministic safety floor (e.g., IF temp > 35C THEN increase ventilation — fires in 0ms, no AI needed)

**What the judges see:**
- Live sensor readings on dashboard from the actual plant on the table
- Agent log: "Temperature 23.4C, humidity 62%, soil moisture 45% — all within optimal range"

**One line in the pitch:**
> "Day to day, EDEN monitors every plant, every sensor, every 10 seconds."

---

### 2. Manage Resources
*"Efficiently use and recycle precious resources like water and nutrients"*

**What we built:**
- Resource chain model: solar → power → desalination → water → crops
- Water budget tracking per zone (340L reserve, 120L/sol production, consumption per crop)
- Pre-storm stockpiling protocol: when CME detected 50h out, maximize desalination, charge battery, pre-water all crops
- Simulation compares resource allocation strategies (e.g., redirect 30% water from drought-tolerant soybean to water-critical potato = 25% more calories from same water)

**What the judges see:**
- Water gauge CLIMBING during stockpiling sequence
- Agent log: "Water reserve at 340L. Need 480L for 5-sol storm autonomy. Running desalination at MAX."
- Strategy comparison: "Strategy A: 40% loss. Strategy C: 3% loss. Selected: C."

**One line in the pitch:**
> "EDEN runs 100 simulations and picks the strategy that saves the most crops with the least water."

---

### 3. Detect and Respond to Plant Stress
*"Identify plant health issues (e.g., nutrient deficiencies, disease) and trigger automated responses"*

**What we built:**
- VPD (Vapor Pressure Deficit) calculation from temperature and humidity — THE metric for disease prediction in controlled environment agriculture
- Agent queries Syngenta KB for disease thresholds per crop and growth stage
- Proactive detection: spots conditions that LEAD to disease before symptoms appear
- Automated response: adjust fan speed, reduce irrigation, increase airflow

**What the judges see:**
- Agent log: "VPD drifting low — 0.52 kPa, below target 0.8-1.2. Botrytis risk rising."
- KB query visible: "Querying Syngenta KB: lettuce disease thresholds in CEA..."
- KB response: "Botrytis cinerea onset at VPD < 0.5 kPa sustained >6h"
- Action: "Increasing airflow. Monitoring VPD recovery."

**THE key moment (KB causality):**
> "Without Syngenta's data, the system would wait for visible symptoms. With it, EDEN acts NOW — before the disease exists."

---

### 4. Optimize for Growth / Learn and Adapt
*"Learn and adapt to find the most effective strategies for growing crops in an alien environment"*

**What we built:**
- Closed-loop feedback: every cycle, compare what EDEN predicted to what actually happened
- Flight rule proposals: when the delta reveals a pattern, EDEN writes a new operational rule
- Simulation validation: before promoting a new rule, re-run scenarios with the rule active vs inactive
- Rule accumulation: starts with ~50 rules from Earth knowledge, grows as EDEN gains Mars experience

**What the judges see:**
- Post-storm debrief in agent log:
  - "Predicted loss: 3.0%. Actual: 4.1%. Delta: +1.1%"
  - "Root cause: stockpiling started 2h too late for Zone B saturation"
  - "Proposing new rule: IF cme_eta > 55h AND water < 80% THEN begin stockpiling"
  - "Rule count: 51. System improving."

**One line in the pitch:**
> "On Sol 1, EDEN had 50 rules from Earth. By Sol 450, it has written over 250 — all from experience. The system teaches itself."

---

## Our Unique Selling Point

**Not a feature. An experience.**

> "EDEN is the only team where you watch a real AI argue about a real plant — and then watch the plant respond."

Three components:

| USP Element | What it is | Why it's unique |
|---|---|---|
| **Living demo** | Real basil plant, real sensors, real actuators (LEDs + fan) | Everyone else demos a simulation. We demo LIFE. |
| **Visible reasoning** | 5 agents disagree in color-coded real-time log | Everyone else has a black box. We show the ARGUMENT. |
| **The silence** | LEDs dim, fan stops, 3 seconds of nothing | Everyone else talks for 180 seconds. We STOP. |

---

## The Pitch (4 beats, 170 seconds)

### Beat 1: THE LONELIEST FARMER (0:00-0:35)

*[Plant on table, LEDs warm, dashboard live]*

> "Four astronauts. 450 days on Mars. 22-minute signal delay. By the time Houston answers, the crops are already dead — or already saved."
>
> "So we built EDEN — an autonomous AI that manages every plant, every drop of water, every watt of power. Day to day, it detects disease before symptoms appear using Syngenta's crop science. But let's see what happens when something goes wrong."

**Covers:** Requirement 1 (monitor/control), Requirement 3 (detect stress) — in one sentence each.

### Beat 2: THE STORM (0:35-1:30)

*[NASA alert. Dashboard green → amber. Countdown 50:42:17.]*

> "A real coronal mass ejection from NASA's database. 1,247 km/s. EDEN calculates: Mars impact in 50 hours."

*[Council debate, color-coded]*

> "Five specialists convene. SENTINEL identifies the threat. AQUA calculates the water deficit. FLORA consults Syngenta's KB — the wheat is in its most vulnerable growth phase. Without that data, EDEN would protect potatoes. The KB changes the decision."
>
> "Standard protocol: shut down and wait. 40% crop loss."
>
> "EDEN runs 100 simulations. Pre-emptive protocol: 3% loss. It picks that. Desalination to maximum. Water climbing."

*[LEDs dim. Fan stops. 3 SECONDS SILENCE.]*

> *(quietly)* "The storm hits."

**Covers:** Requirement 2 (manage resources), Requirement 3 (detect/respond to stress). KB causality proven.

### Beat 3: THE LEARNING (1:30-2:10)

*[Dashboard amber → green. LEDs brighten.]*

> "Storm passes. 4.1% loss vs predicted 3%. EDEN doesn't just survive — it learns."
>
> "It finds the gap: stockpiling started 2 hours too late. Writes a new rule. Next time, start at 60 hours."
>
> "Sol 1: 50 rules from Earth. Sol 450: over 250. All self-taught."

**Covers:** Requirement 4 (learn and adapt). THE differentiator.

### Beat 4: THE MIRROR (2:10-2:50)

> "We built this for Mars — the hardest environment imaginable."
>
> "But 800 million people on Earth are food insecure. Syngenta has one agronomist per 5,000 farmers. Same constraints: no water, extreme conditions, no expert when it counts."
>
> "Same Syngenta knowledge base. Same closed loop. Mars forced the hardest version. The Earth version is easier."

*[LEDs full warm. Plant alive.]*

> "Because on Mars, there is no second chance."

**Covers:** Earth applicability. Clean close.

---

## The Closed-Loop Advantage (what to say if judges ask about architecture)

The ng-voice/Deutsche Telekom whitepaper validated this exact pattern on AWS:

| Telco (ng-voice) | Agriculture (EDEN) |
|---|---|
| Network logs → S3 | Plant sensors → Pi |
| SageMaker predictions | Simulation engine (GDD, Liebig's Law) |
| CloudWatch event triggers | Flight rules (deterministic, 0ms) |
| Bedrock agent decides | Agent council debates (visible reasoning) |
| Lambda corrective actions | Actuator commands (LEDs, fan, pump) |
| Closed loop feedback | Predicted vs actual → new flight rules |

> "AWS proved this closed-loop pattern works for Deutsche Telekom's network operations. We proved it works for agriculture. Same Bedrock agents, same event-driven pattern, different domain."

---

## What We Have (inventory)

| Asset | Status | Demo-ready? |
|---|---|---|
| Raspberry Pi with sensors (temp, humidity, soil, light) | Working | Yes |
| LED strip (warm → amber → red → warm) | Working | Yes |
| Fan (controllable, audible) | Working | Yes |
| Real basil plant | Alive | Yes |
| React dashboard (dark theme) | Working | Needs 4-panel demo mode |
| Agent system (Strands SDK, multi-agent) | Working | Yes |
| Syngenta KB integration (MCP) | Working | Yes |
| Simulation engine (Monte Carlo) | Working | Yes |
| Flight rules engine | Working | Yes |
| NASA DONKI integration | Working | Yes |
| AgentCore Runtime deployment | Not done | 30 min |

---

## Before the Pitch (checklist)

- [ ] Fix companion planting claim (VOC, not nitrogen fixation) — 10 min
- [ ] Deploy AgentCore Runtime — 30 min
- [ ] Dashboard: 4 panels max in demo mode — 30 min
- [ ] Font sizes: 18px+ log, 48px+ counter — 15 min
- [ ] Color transitions: green → amber → red → green — 1h
- [ ] Record backup video — 30 min
- [ ] Test on phone hotspot — 10 min
- [ ] Card next to plant: "SOL 280 | EDEN OPERATIONAL" — 5 min
- [ ] **HARD STOP building 4 hours before pitch**
- [ ] Rehearse full pitch 3x with timer — 45 min
- [ ] Practice the 3-second silence with a count
- [ ] Practice the closing line looking at judges, not screen
- [ ] Assign: Lars speaks, Bryan drives, Johannes prop, PJ backup
