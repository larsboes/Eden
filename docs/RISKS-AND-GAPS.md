# EDEN — Risks, Gaps, Judge Psychology & Scope Control

> Merged from: Judge Panel Council (4 judges × 3 rounds), Deep Analysis (6 parallel agents), Creative Deep Dive (11 agents). Distilled to actionable items only.

---

## Critical Risks

### RISK 1: Scope vs Time

PRD has 7 tiers of features. ~20h remaining. Realistic throughput: 10-12 hours of features for a 4-person team. Must cut ruthlessly.

**Rule: Demo 1 feature at 200%, not 10 at 50%.** Let judges discover depth in Q&A.

**Preparation:**
- The ONE feature is the **CME prediction → stockpiling sequence**. It touches every architecture layer (SENTINEL detects → ORACLE simulates → AQUA calculates → FLORA triages → VITA shows human cost). Everything else is bonus.
- Agent council: ONE agent with structured system prompt outputting `[SENTINEL]: ...` format. 80% of impact for 20% of effort. Don't build 5 separate LLM instances.
- Virtual Farming Lab: text in agent log only ("Strategy A: 40% loss. Strategy B: 12%. Strategy C: 3%. SELECTED: C."). Prompt engineering, not frontend.
- Dashboard serves the demo sequence, not the other way around. 4 components: agent log + CME countdown + water gauge + triage card. Everything else is polish.

### RISK 2: Live Demo Failure

Hackathon WiFi with 20+ teams. Pi connectivity, API calls, WebSocket streams — any can fail.

**Mitigation (defense in depth — 5 layers):**
1. **Pre-record backup video** — After demo works ONCE, screen-record the full CME→stockpiling sequence (30-60s). If live fails: "Here's what you'd see live — let me walk you through it." Lose 5% impact vs 100%.
2. **Replay mode** — JSON file with pre-recorded state transitions. `REPLAY_MODE=true` → dashboard reads from local file. Agent log scrolls, countdown ticks, water gauge rises. Looks identical to live from the audience.
3. **Decouple Pi from critical path** — Pi serves sensor JSON via simple HTTP polling, NOT IoT Core + MQTT through cloud. If Pi dies, dashboard falls back to simulated sensor data. If WiFi drops, Pi still blinks LEDs from a local script.
4. **Cache API responses** — First successful DONKI CME call → save to local JSON. If NASA API is slow/down during demo, serve from cache. Same for Syngenta KB queries.
5. **Phone hotspot as backup network** — One team member's phone hotspot. Dedicated, no contention with 20+ teams.

**The meta-prep: Rehearse the full 3-minute demo at least 3 times before judging.** Every break = a failure point to harden. Teams that rehearse win. Teams that "it works on my machine" lose.

### RISK 3: K8s Jargon Alienating Non-Technical Judges

"PodDisruptionBudget check: 1/3 nodes affected" means nothing to a crop scientist.

**Rule: Two vocabularies, two contexts.**
- **Dashboard + agent log** = agricultural language ONLY. "Isolating Protein Zone to prevent cross-contamination." "Adjusting nutrient solution EC from 1.8 to 2.4 mS/cm." Never "Applying NetworkPolicy to Node:Protein."
- **Pitch slides** = K8s mapping as ONE 30-second slide. "If you know Kubernetes, you already understand EDEN." Then move on.

**Preparation:**
- Write 5-6 example agent log entries using agricultural vocabulary (VPD, EC, DLI, BBCH) naturally. Bake into system prompt as few-shot examples so the agent outputs in that style.
- The VPD/EC/DLI/BBCH vocabulary is the secret weapon for Syngenta judges. One agent sentence — "VPD target: 0.8-1.2 kPa. DLI maintained at 17 mol/m²/day." — signals more agricultural knowledge than most teams' entire submission. System prompt change only, 30 minutes.

### RISK 4: Not Actually Using AgentCore

"Usage of the provided AWS AgentCore system" is a KEY ELEMENT for judging. Direct Bedrock API calls do NOT earn the AWS bonus. Deployed on AgentCore Runtime + MCP endpoint calls DO.

**Fix**: Deploy agent to AgentCore Runtime (Lab 04, 30 minutes). Non-negotiable.

**Preparation:**
- Someone does the Lab 04 walkthrough BEFORE building features. Get the deployment pipeline working with a "hello world" agent first, then swap in real agent code. Don't discover deployment issues at hour 18.
- The higher-value play: don't just deploy to Runtime — create at least 1 custom Gateway target (e.g., DONKI CME as OpenAPI spec → S3 → Gateway Target). Now you have "1 provided + 1 custom" targets through the same MCP Gateway URL. AWS judge sees you understood the Gateway pattern, not just the Runtime.
- Code is 4 lines (see `reference/AWS_BLUEPRINT.md`, Lab 04 section): `BedrockAgentCoreApp()` → `@app.entrypoint` → Docker → ECR → AgentCore Runtime.

### RISK 5: Team Coordination (Meta-Risk)

4 people, parallel workstreams. Digital (Lars + Bryan) and Physical (Johannes + PJ) need a clear interface contract.

**Preparation:**
- Define the Pi ↔ Dashboard contract in 10 minutes: "Pi serves JSON at `http://pi-ip:8080/sensors` with these fields. Dashboard polls every 10s. Pi accepts POST to `/actuator` with `{device, action, value}`." Then work independently.
- **Pitch rehearsal matters as much as tech** — 25% of score is presentation quality. Assign speaking roles. ONE person on keyboard. Know the backup video plan. Rehearse the 3-minute arc. Teams that wing the pitch always underperform their build quality.

---

## Gaps to Close (Prioritized)

### 0-Minute Fixes (SYSTEM PROMPT ONLY — covers challenge requirements)

These are system prompt additions that cost zero build time but check explicit judging criteria:

**GAP: Disease Detection in Nominal Ops (0 min) — CHALLENGE REQUIREMENT**
Brief says: "Detect and Respond to Plant Stress: Identify plant health issues (e.g., nutrient deficiencies, disease)."
Add few-shot example to system prompt showing VPD monitoring → Botrytis risk detection → preventive airflow increase → KB query for disease thresholds. Shows daily vigilance, not just crisis response.

**GAP: Learning Loop Visibility (0 min) — CHALLENGE REQUIREMENT**
Brief says: "Learn and adapt to find the most effective strategies." Add post-event debrief example: agent compares predicted vs actual loss, proposes new flight rule, increments rule count. Shows the system gets smarter over time.

**GAP: KB Causality (0 min) — PROVES REAL INTEGRATION**
Agent must explicitly state: "Without Syngenta KB data, I would prioritize X. KB changes my assessment to Y." Shows KB isn't decorative — it drives decisions. Syngenta judge will ask to see this live.

**GAP: Honest Nutritional Framing (0 min) — SCIENTIFIC ACCURACY**
VITA agent surfaces: "Rations provide 82% of calories. Greenhouse provides 193% vitamin C, 146% iron, 139% folate — the fresh nutrition rations can't." Prevents Syngenta scientist from catching the calorie math and thinking we didn't understand the brief's "supplement" language.

**GAP: Post-Event Learning in Demo Script (0 min)**
Add to demo script between Act 3 and Act 4: quick agent log showing "Actual loss 4.1% vs predicted 3%. Promoting FR-CME-014. Rule count: 55." Proves "optimize and adapt over time."

### 30-Minute Fixes (DO FIRST — highest ROI)

**GAP: BBCH + Precision Ag Vocabulary (~30min)**
Add to agent system prompt. Massive credibility with Syngenta judges.

| Term | What Pros Use | What We Have Now | Fix |
|------|--------------|-----------------|-----|
| VPD | Vapor Pressure Deficit (drives transpiration) | "humidity %" | Add VPD calculation + display |
| EC | Electrical Conductivity (nutrient concentration) | "nutrients" generic | Add EC reading to sensor display |
| DLI | Daily Light Integral (mol/m²/day of PAR) | "lux / light %" | Add DLI target per crop |
| BBCH | Growth stage codes ("BBCH 61 = beginning of anthesis") | "flowering" | Use BBCH in agent logs |
| Root zone temp | Critical for nutrient uptake | Air temp only | Mention distinction in reasoning |

Agent should say: "Adjusting nutrient solution EC from 1.8 to 2.4 mS/cm as tomato enters BBCH 65 (full flowering). VPD target: 0.8-1.2 kPa. DLI maintained at 17 mol/m²/day." That ONE sentence signals more agricultural knowledge than most teams' entire submission.

**GAP: AgentCore Runtime Deploy (~30min)**
Follow Lab 04: Docker → ECR → AgentCore Runtime. 4 lines of code change. Biggest AWS bonus for least effort.

**GAP: Human Moment in Demo (0 minutes)**
Add to pitch script: "Dr. Chen requested spinach three times this week. The agent knows. But the math says no." Zero build time.

### 1-Hour Fixes (HIGH impact)

**GAP: KB Query + Response Visible in Agent Log (~1h)**
Agent log must show: "Querying Syngenta KB: wheat radiation tolerance at BBCH 65..." → "KB: Yield reduction 15-40% under elevated UV-B." Proves integration is real, not faked.

**GAP: "Mission Day 1" — 450-Sol Crop Plan (~1h)**
Before the crisis scenario, agent generates a full 450-sol crop rotation schedule. One LLM call using Syngenta KB data + simple timeline display.

Pitch line: "On Sol 1, our agent already knows what it needs to harvest on Sol 400. Everything you see next is about protecting that plan."

Nobody else opens their demo with PLANNING. Everyone else shows reacting. This is the K8s manifest — the agent IS the reconciliation loop keeping reality aligned with the plan. HIGH IMPACT.

**GAP: Agent Personality in Logs (~1h)**
Not sterile system output. The agent speaks like a seasoned Martian farmer:

Instead of: `[Sol 142] PREDICTIVE ANALYSIS: CME detected. Speed: 1,247 km/s.`
Write: `"Sol 142. CME coming in hot — 1,247 km/s. Wheat's in full flower, worst possible timing. I have 50 hours. Going to stress-harden the nutrient mix and stockpile water. She'll be ornery but she'll make it."`

System prompt change only. Highest-leverage single change for Creativity score.

### 2-3 Hour Fixes (MEDIUM — if time permits)

**GAP: O2/CO2 Life Support Indicator**
Plants on Mars aren't just food — they're OXYGEN GENERATORS. If crops die, astronauts suffocate.

- Small persistent dashboard indicator: "Greenhouse O₂ Contribution: 14.2% of crew requirements"
- When crops degrade during storm, this number drops
- Pitch line: "If these crops die, the astronauts don't just go hungry — they suffocate."
- Transforms how judges perceive the entire project. 2-3h build.

**GAP: Dashboard State Machine (Progressive Disclosure)**
Not all panels visible at once. 4 states matching demo acts:
- NOMINAL: Full dashboard, calm, muted colors
- ALERT: 60% screen = CME alert + countdown + Virtual Lab. Amber tint.
- CRISIS: Water gauge + triage primary. Countdown massive. Red accents.
- RECOVERY: Gradual warm-up. Green returns.

3-4h for full implementation. **Shortcut (1h)**: Just do the background color tint change on alert — 70% of the visual impact.

**GAP: Font Sizes for Projection (~30min)**
- Agent log: 18-20px minimum
- Sol counter: 48px+
- Countdown timer: 64px+
- Max 4-5 agent log lines visible
- Test on external monitor if possible

**GAP: Custom Gateway Target for DONKI (~1-2h)**
Wrap DONKI OpenAPI spec as MCP tool through own AgentCore Gateway target (S3 → Gateway Target). Shows you created custom gateway targets, not just used the provided one. High AWS bonus.

---

## What to Build vs Fake vs Cut

| Feature | BUILD | FAKE (mention/log text) | CUT |
|---------|-------|------------------------|-----|
| AgentCore Runtime deployment | YES — mandatory | | |
| Syngenta MCP KB integration (visible in log) | YES — mandatory | | |
| Dashboard (agent log, sensors, nutrition, alerts) | YES | | |
| DONKI CME prediction + countdown | YES — demo climax | | |
| Water/energy stockpiling | YES — demo climax | | |
| Agent personality in logs | YES — system prompt | | |
| VPD/EC/DLI/BBCH vocabulary | YES — prompt + display | | |
| Nutritional tracking (4×450 days) | YES — answers the brief | | |
| Virtual Farming Lab (strategy comparison) | | YES — text in agent log | |
| Pi physical prop (LEDs sync) | YES — decoupled from cloud | | |
| Pre-recorded demo fallback | YES — insurance | | |
| Mission Day 1 crop plan | YES — 1h, wild card | | |
| Council debate in agent log | YES — structured prompt | | |
| Ethical triage with human cost | YES — prompt + display | | |
| Disease/stress detection in nominal ops | YES — system prompt, 0 build | | |
| Post-event learning loop (rule promotion) | YES — system prompt, 0 build | | |
| KB causality ("KB changed my decision") | YES — system prompt, 0 build | | |
| Honest nutritional framing (supplement) | YES — system prompt, 0 build | | |
| O₂/CO₂ life support indicator | | MENTION in pitch | |
| Mars-to-Earth mode switch | | Only if time (hour 28+) | |
| Companion planting (Three Sisters) | | YES — 1 agent log entry | |
| Rent-a-Human API | | MENTION in Q&A | |
| Seed bank / genetic diversity | | MENTION in Q&A | |
| Sol Forecast Timeline | | | CUT |
| Seasonal Ls mechanics | | | CUT |
| Lambda Mars Transform | | | CUT — inline in agent |
| IoT Core MQTT pipeline | | | CUT — use HTTP polling |
| EventBridge CronJobs | | | CUT |
| CloudWatch integration | | | CUT |
| S3 image storage | | | CUT |
| Camera feed | | | CUT |
| Sound design | | | CUT |

---

## Judge Psychology

### Syngenta Agricultural Scientist

**Impresses**: VPD/EC/DLI on dashboard, BBCH in agent reasoning, agronomic rationale ("reducing N at day 180 for reproductive stage"), Earth applications with specific Syngenta business case (1:5000 agronomist ratio), visible KB query+response that CHANGES agent behavior, ethical triage with dietary impact, honest "supplement not sole source" framing, disease detection from environmental drift

**Loses points**: K8s jargon in UI, generic "nutrients" without EC/pH, humidity without VPD, ignoring Earth angle, claiming greenhouse feeds the crew (it can't — the math doesn't work)

**Q&A probe**: "Show me the agent querying the Syngenta KB live and making a decision based on what it gets back." ANSWER: Show the CME sequence where SENTINEL queries wheat radiation tolerance and explicitly says "KB changed my priority from potato to wheat."

### AWS Solutions Architect

**Impresses**: Agent on AgentCore Runtime, MCP tool calls through gateway, clean architecture, proper use of their provided infra, multi-agent patterns

**Loses points**: Direct Bedrock calls bypassing AgentCore, custom stack that ignores their system, claiming "multi-agent" when it's one agent with personas (be honest about what you built)

**Q&A probe**: "Walk me through a single agent decision — sensor data in, tool calls, actuator command out."

### UX/Design Judge

**Impresses**: Dashboard tells a story (state machine), projection-readable fonts, color shifts driving narrative, physical prop sync, information hierarchy (not all panels equal)

**Loses points**: Wall of information, 12px text, everything visible at once, no visual hierarchy for the climax moment

**Q&A probe**: Won't ask — will watch and note: "Did I understand what was happening at every moment without reading small text?"

### Presentation Expert

**Impresses**: One strong narrative arc, 5 moments max, physical prop between screen and judges, confident team handoffs, ONE person on keyboard

**Loses points**: "And then... and then..." demo with 10+ rushed moments, team members talking over each other, no backup when demo breaks

**Q&A probe**: "What was the hardest technical challenge you solved?" (Separates real builders from assemblers)

---

## What "Standard" Submissions Look Like

Most teams will:
- Follow Amplify Gen2 + Kiro + Strands SDK happy path
- Build a React dashboard with sensor charts
- Connect to Syngenta MCP KB
- Show reactive agent: "sensor drops → agent fixes"
- 2D charts, standard UI components

**EDEN's real differentiators vs the field:**
1. PREDICTIVE (CME detection, not just reactive)
2. PHYSICAL PROP (likely no other team has hardware)
3. Agent PERSONALITY (no other team has voice/inner monologue)
4. The Earth pivot ("1 agronomist per 5,000 farmers — EDEN fills the gap")
5. Agricultural vocabulary depth (VPD/EC/DLI signals)
6. Ethical triage with human cost transparency
7. 4-layer architecture (not just "agent + dashboard")
8. LEARNS AND ADAPTS (flight rule promotion visible in demo — core requirement)
9. DISEASE DETECTION in nominal ops (VPD monitoring → preventive action — core requirement)
10. KB CAUSALITY ("Without Syngenta KB I'd do X. KB changed my decision to Y.")
11. SCIENTIFICALLY HONEST (supplement framing — greenhouse + rations complement each other)

---

## TRAPS — Do NOT Build

| Trap | Why | Wasted Time |
|------|-----|-------------|
| Full multi-agent architecture (5 separate LLM instances) | Re-architecting with limited time. One agent with structured prompt achieves 80%. | 15-20h |
| Sound design / Mars ambience | Useless in noisy hackathon judging room | 3-4h |
| Interactive agent Q&A during pitch | One weird LLM answer = dead demo | risk |
| Deep "42" easter egg weaving | Judges won't notice. One 42% humidity flash is enough. | attention |
| Seed bank simulation model | Mention in pitch. Don't model it. | 8h+ |
| Disease quarantine scenario (FULL) | Brief explicitly asks for disease detection. Cover via system prompt agent log entry showing VPD/Botrytis detection during nominal ops (0 build time). Full quarantine simulation is overkill. | 4-5h for full, 0 for prompt |
| Body silhouette health degradation | Crosses from visceral to unsettling | 4h |
| Philosophical climate change sermon | Judges score what you built, not beliefs | time |
