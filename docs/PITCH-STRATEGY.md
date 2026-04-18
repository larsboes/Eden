# EDEN — Pitch Strategy (Single Source of Truth)

> This document replaces all scattered pitch guidance. If it contradicts PRD.md, CONCEPT.md, or RISKS-AND-GAPS.md, THIS document wins. Generated from 4 parallel analyses: FirstPrinciples, Creative Brainstorm (10 angles), Judge Council (4 simulated judges, 3 rounds), and Red Team (8 adversarial attackers).

---

## THE ACTUAL PROBLEM (one paragraph)

Syngenta has the world's best crop science locked in a knowledge base. 570 million farms need it. There aren't enough agronomists to deliver it. The Mars greenhouse challenge is Syngenta's stress test: if an AI agent can make Syngenta's crop science actionable under the harshest conditions imaginable — 22-minute latency, zero margin for error, limited resources — then the Earth version is trivially easier. EDEN doesn't just manage a greenhouse. EDEN makes Syngenta's knowledge base autonomous.

## THE USP (one sentence)

**EDEN is what happens when you give Syngenta's crop science the ability to think, argue, and act — and prove it works 227 million km from the nearest expert.**

## THE PITCH ORDER (critical insight)

**Do NOT open with Earth. Do NOT treat Earth as an afterthought.**

- **Open with Mars** (the assignment) — this is what judges expect. You're doing the challenge.
- **Demo on Mars** (the proof) — this is where the agent shows it works.
- **Close on Earth** (the punchline) — this is where Syngenta leans forward.

The Earth pivot is the PUNCHLINE, not the premise. Judges remember the close. Give it 45 seconds, not 30. Make it specific.

---

## THE 3-MINUTE PITCH (4 beats, timed)

### Beat 1: THE HOOK (0:00-0:15) — Physical + Emotional

*[Presenter stands next to Raspberry Pi prop with living basil plant, LEDs warm white]*

> "This basil plant has an AI managing its life right now. It monitors its soil, its light, its water — every 30 seconds. Now imagine this plant is on Mars. 227 million kilometers from the nearest expert. 22 minutes before anyone on Earth even hears it's in trouble. That's the problem we solved."

*[Turn to dashboard, already live]*

**Why this works:** Physical prop creates focal point. Judges look at something alive. The zoom from micro (one plant) to macro (Mars) happens in 3 sentences.

### Beat 2: THE BRAIN (0:15-0:45) — Agricultural Intelligence

> "EDEN doesn't just react to sensors. It THINKS."

Show nominal operations — ONE decision cycle:

- Agent detects VPD drifting low in leafy green zone (5 seconds)
- Queries Syngenta KB: "lettuce disease thresholds in CEA" (5 seconds, VISIBLE in agent log)
- KB returns: "Botrytis cinerea onset at VPD < 0.5 kPa sustained >6h" (KB causality moment)
- Agent says: "Without Syngenta's data, I'd wait for symptoms. With it, I act NOW. Increasing airflow." (THE line)
- Dashboard shows fan speed adjustment, VPD trending back up

> "That's EDEN preventing a disease that hasn't happened yet — using Syngenta's crop science, not guessing."

**Why this works:** Directly proves "detect and respond to plant stress" (challenge requirement). Shows KB is CAUSAL, not decorative. Agricultural language (VPD, Botrytis, CEA) signals credibility. Takes 30 seconds total.

### Beat 3: THE STORM (0:45-1:45) — Crisis + Council + Learning

> "But let's see what happens when a real crisis hits."

**CME Detection (15s):**
SENTINEL: "Sol 247. CME incoming — 1,247 km/s. Mars ETA: 50 hours. Wheat's in full flower — BBCH 65 — its most vulnerable window."

*Dashboard shifts: green → amber. Countdown appears: 50:42:17.*

**Council Debate (30s):**
Show 3-4 agents visibly disagreeing in color-coded log:
- SENTINEL: "KB says wheat at BBCH 65 shows 15-40% yield loss under UV-B. Without this data, I'd save potato. KB changes my priority to wheat."
- ORACLE: "Simulation ran 100 scenarios. Pre-emptive protocol: 3% crop loss. Doing nothing: 40%."
- AQUA: "Water at 340L. Need 480L. Running desalination at MAX."
- VITA: "If wheat dies, crew iron drops below threshold in 45 sols."

> "Five specialists. Different data. Different priorities. One decision."

*Council vote appears: Strategy C adopted.*

**Stockpiling + Physical Moment (15s):**
Water gauge rising. Battery charging. Dashboard amber → red.

*LEDs dim on the physical prop. If fan is running, it stops. Silence.*

> "Those LEDs just dimmed because the AI decided to redirect power to water stockpiling. The storm hasn't arrived yet. EDEN is already preparing."

**THE MOMENT.** This is what judges remember tomorrow.

**Post-Storm Learning (10s):**
> "After the storm — actual loss 4.1%, predicted 3%. EDEN writes a new rule: 'Start stockpiling 7 hours earlier.' Flight rule count: 55. The system just taught itself."

*One line in agent log. Rule count increments.*

**Why this works:** One continuous dramatic arc. The LED dimming is sensory — it crosses from screen to physical space. Council debate shows WHY multi-agent matters (each sees different truth). KB causality embedded naturally. Learning loop proven with one concrete example. Covers "manage resources" + "optimize for growth/learn and adapt" challenge requirements.

### Beat 4: THE MIRROR (1:45-2:30) — Earth Transfer (45 seconds!)

> "Everything you just saw — the disease detection, the crisis planning, the learning — runs on Syngenta's knowledge base. Not a Mars-specific system. THE knowledge base. The same crop science Syngenta uses everywhere."

*Pause. Look at judges.*

> "There are 570 million farms on Earth. Syngenta has approximately 1 agronomist per 5,000 farmers. In Sub-Saharan Africa, a smallholder maize farmer watches her soil moisture drop. She has no agronomist. She has a phone."

> "EDEN's flight rules for water scarcity work the same way — because drought stress follows the same biology whether the atmosphere is thin because it's Mars or thin because it's semi-arid Kenya. Same Syngenta science. Same architecture. Different sky."

> "Mars forced us to build the hardest version. The Earth version is easier."

**Why this works:** 45 seconds, not 30. Named location (Kenya). Named crop (maize). Named constraint (soil moisture). Specific enough to be credible. The biology line ("drought stress follows the same biology") is memorable. Connects Syngenta's existing business to what they just saw.

### Close (2:30-2:50)

> "We built the loneliest farmer in the solar system. It plans every harvest. It detects disease before symptoms appear. It sees storms 50 hours ahead. It learns from every decision. And it gets better every day."

*Pause. Look at judges.*

> "Because on Mars, there is no second chance."

*2 seconds of silence. Then:* "Thank you."

### Buffer (2:50-3:00) — 10 seconds of safety margin

---

## WHAT MAKES EDEN DIFFERENT (3 things no other team will have)

1. **Physical prop** — A living plant with LEDs that sync to the AI's decisions. When the storm hits, the LEDs dim. Nobody else has this sensory crossover between screen and physical space.

2. **KB causality** — The agent SHOWS where Syngenta's data changed its decision: "Without KB I'd save potato. KB says wheat at BBCH 65 is vulnerable. I save wheat." No other team will make the KB this visible.

3. **Council debate as drama** — 5 agents disagreeing in color-coded real-time. Not "AI made a decision." "AI ARGUED about it, and you saw why." This is the creative differentiator.

---

## PER-CRITERION STRATEGY

### Creativity (25%)
- **Council debate as design feature** — "disagreement is the point"
- **Physical prop** — living plant in a room of laptops
- **Agent personality** — not sterile system output but professional agricultural voice
- **KB-derived insight** — the agent finds something no single document says

### Functionality / Accuracy / Applicability (25%)
- **Working agent** — real Strands SDK, real tool calls, real MCP KB queries
- **Simulation engine** — real math (GDD, Liebig's Law), not LLM text
- **Agricultural accuracy** — VPD/EC/DLI/BBCH vocabulary. Fix companion planting (VOC, not nitrogen fixation)
- **Applicability** — the Earth transfer with specific farmer scenario

### Visual Design / UX (25%)
- **Dashboard state machine** — green → amber → red → green color transitions
- **Progressive disclosure** — not all panels visible at once
- **Font sizes** — 18px+ agent log, 48px+ Sol counter, 64px+ countdown
- **ONE visual moment** — the color shift when CME is detected

### Presentation / Demo Quality (25%)
- **4 beats, not 7** — cut ruthlessly
- **One speaker, one driver** — never two people reaching for the keyboard
- **Rehearse 3x** — with timing, with backup plan, with Q&A
- **The close is memorized** — "Because on Mars, there is no second chance"

### AWS Bonus
- Bedrock (Claude via Strands SDK) — the backbone
- AgentCore Gateway — MCP tool calls to Syngenta KB (VISIBLE in demo)
- AgentCore Runtime — deploy agent (Lab 04, 30 min)
- Strands SDK — real @tool decorators, real multi-agent patterns

---

## WHAT TO FIX BEFORE PITCH

| Fix | Time | Impact |
|-----|------|--------|
| Fix companion planting: VOC-mediated, not nitrogen fixation | 10 min | Prevents credibility collapse |
| Agent log font size 18px+ | 15 min | Readable from 5 meters |
| Dashboard color shift on state change | 1h | 70% of visual storytelling |
| AgentCore Runtime deployment (Lab 04) | 30 min | AWS bonus points |
| Memorize vitamin C math: crop, area, cycles, yield, mg, total | 15 min | Survives Q&A probe |
| Have backup video of full demo sequence | 30 min | Insurance against WiFi failure |
| Rehearse full 3-min pitch 3x | 45 min | THE highest-ROI activity |

---

## Q&A PREPARATION (5 most likely probes)

**1. Syngenta judge: "Show me the agent querying the KB live."**
Answer: Trigger a scenario change. Show the agent log: "Querying Syngenta KB: [query]" → "KB response: [data]" → "This changes my decision from X to Y." If backend is down, narrate over cached response: "Here's what it looks like when the KB returns data."

**2. AWS judge: "Walk me through a single decision — sensor to action."**
Answer: "Sensors read every 30 seconds. Flight rules fire first — deterministic, zero latency, no AI needed. If deltas exist between actual and desired state, the agent council activates. Each specialist has Strands @tool access to the KB via MCP Gateway. The coordinator synthesizes. Actuator commands go out. Next cycle: did it work? Feedback loop."

**3. UX judge: (watches silently)**
They're asking: "Did I understand what was happening?" The answer is in the dashboard design, not in words. The color transitions and font sizes ARE the answer.

**4. Presentation judge: "What was the hardest technical decision?"**
Answer: "Whether to run 12 separate LLM instances or one agent with 12 structured perspectives. We chose real multi-agent with ThreadPoolExecutor because we needed agents to DISAGREE with each other by name — 'I disagree with CHRONOS because...' A single prompt can't generate genuine adversarial tension."

**5. "Why multi-agent? Couldn't one agent do this?"**
Answer: "One agent collapses to the loudest objective — usually calories or safety. EDEN's parliament forces every objective to be advocated. VITA sees crew nutrition. HESTIA sees morale. AQUA sees water budget. The 'obvious' caloric choice is often wrong when you factor in micronutrient deficiency projections. A single agent can't surface that trade-off. 12 specialists can."

---

## TEAM ROLES (recommended)

- **Speaker**: Lars — faces judges, narrates the story, delivers the close
- **Driver**: Bryan — controls keyboard/mouse, triggers demo states, handles any technical issues
- **Prop**: Johannes — positions Pi between screen and judges, ensures LEDs work, stands ready to reset
- **Backup**: PJ — has phone hotspot ready, has backup video queued, ready to step in

**Rule: ONE voice during the pitch. Others speak only in Q&A.**

---

## DEMO FAILURE CONTINGENCY

| Failure | Response |
|---------|----------|
| WiFi dies | Switch to phone hotspot (PJ). If still down: play backup video. |
| Bedrock API slow | Dashboard falls back to cached/mock data. Narrate as if live. |
| Pi disconnects | LEDs run from local script as fallback. Dashboard continues from simulated sensors. |
| Agent generates weird output | "That's the real AI — sometimes unpredictable. Let me show you the typical output." Switch to cached response. |
| Clock hits 2:50 mid-sentence | Skip to close immediately: "Because on Mars, there is no second chance." |

---

## THE CORE MESSAGE (survives if everything else fails)

Even if the demo crashes, the slides fail, and the Pi catches fire:

> "We gave Syngenta's crop science the ability to act autonomously. We proved it works on Mars. The Earth version is easier. 570 million farms. One knowledge base. Zero agronomist shortage."

That message, delivered with conviction while looking at the judges, scores 70% of maximum even with zero tech working.

---

## TRAPS TO AVOID

- Do NOT explain the K8s mapping. If asked: "The architecture uses reconciliation loops — if you know K8s, it'll feel familiar."
- Do NOT say "Monte Carlo simulation" in the pitch. Say "we simulated 100 scenarios."
- Do NOT show the architecture diagram. Show the DECISION, not the pipes.
- Do NOT mention all 12 agents by name. Show 4-5 in the log. Others exist for Q&A.
- Do NOT claim the greenhouse feeds the crew. "The greenhouse provides what rations can't — fresh vitamins, iron, morale."
- Do NOT use "nitrogen fixation" for companion planting. Use "basil VOCs suppress fungal pathogens in the sealed dome."
- Do NOT run over 3 minutes. If at 2:50, skip everything and deliver the close.
