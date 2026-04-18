# EDEN — Final Pitch Strategy (v3, stress-tested)

> Survives: Syngenta scientist attack, competitor counter-pitch, pitch expert restructure, premortem simulation, and 8 adversarial red team attacks. This is the version that incorporates every correction.

---

## THE EDGE (corrected, honest, defensible)

~~"EDEN doesn't apply crop science. It creates it."~~ (Killed. Unverifiable in 3 min. Syngenta scientist will ask "name one insight" and we can't answer.)

**"EDEN makes Syngenta's crop science autonomous — reasoning across all 7 domains simultaneously, where no human expert can be present."**

Visceral version for the pitch: **"EDEN sees the future and gets smarter every day."**

Why this is the real edge: The value isn't novel science. It's Syngenta's EXISTING knowledge, acting on its own, everywhere, 24/7. That's what the 1:5000 agronomist-to-farmer ratio needs. Every other team will build a dashboard that displays KB data. EDEN is the only system where the KB ACTS autonomously AND the reasoning is visible.

---

## THE 4-BEAT PITCH (170 seconds, 10s margin)

**One message: EDEN sees the future and gets smarter every day.**

**Three proof points: Detect. Survive. Learn.** Everything else is Q&A depth.

---

### BEAT 1: THE LONELIEST FARMER (0:00 — 0:35)

*[Plant on table, LEDs warm white, dashboard live, Sol counter ticking]*

> "Four astronauts. 450 days on Mars. 22-minute signal delay to Earth. By the time Houston answers a question, the crops are already dead — or already saved."
>
> "So we built EDEN — an autonomous AI that manages every plant, every drop of water, every watt of power. Day to day, it detects disease before symptoms appear, using Syngenta's crop science knowledge base across all seven domains."
>
> "But let's see what happens when something goes wrong."

**35 seconds. Frames problem. Shows system running. Establishes KB. Transitions to crisis.**

---

### BEAT 2: THE STORM (0:35 — 1:30)

*[DONKI alert fires. Dashboard green → amber. Countdown appears: 50:42:17]*

> "A real coronal mass ejection — pulled from NASA's live database. Speed: 1,247 km/s. EDEN calculates: it hits Mars in 50 hours."

*[Council log scrolling, color-coded agents]*

> "Five specialist agents convene. SENTINEL identifies the threat. AQUA calculates the water deficit — the storm cuts solar power by 70%, which kills water production."

**THE KB CAUSALITY MOMENT (one sentence, no BBCH):**

> "FLORA consults Syngenta's knowledge base and discovers the wheat is in its most vulnerable growth phase right now. Without that data, the system would protect potatoes — more calories. The KB changes the decision."

**THE PRE-LOAD (magic technique):**

> "Standard protocol for a solar storm: shut down and wait. Typical loss: 40% of crops."

*[Water gauge climbing. Battery charging.]*

> "EDEN runs 100 simulations. Pre-emptive protocol: 3% loss. It picks C. Desalination to maximum. Water reserves climbing. Battery charging."

*[LEDs dim on plant. Fan stops. 3 SECONDS OF SILENCE.]*

> *(quietly)* "The storm hits."

**55 seconds. Real NASA data. Visible agent reasoning. KB changes decision. Simulation comparison. LED dimming = THE MOMENT.**

---

### BEAT 3: THE LEARNING (1:30 — 2:10)

*[Dashboard amber → green. LEDs brighten gradually.]*

> "The storm passes. 4.1% crop loss — against a predicted 3%. EDEN doesn't just survive. It learns."

*[Agent log: post-event debrief, one clear line]*

> "It compares prediction to reality. Finds the gap: water stockpiling started 2 hours too late. So it writes a new rule — next time, start at 60 hours, not 48."

> "On Sol 1, EDEN had 50 rules from Earth knowledge. By Sol 450, it has written over 250 — all from its own experience. The system gets smarter every single day."

**40 seconds. Shows "learn and adapt." Predicted vs actual. Self-improvement. THE differentiator.**

---

### BEAT 4: THE MIRROR (2:10 — 2:50)

> "We built this for Mars — the hardest environment imaginable."

> "But here is what matters: 800 million people on Earth are food insecure. Syngenta has one agronomist for every 5,000 farmers. Those farmers face the same constraints — limited water, extreme conditions, no expert when it counts."

> "Same Syngenta knowledge base. Same decision system. Mars forced us to build the hardest version. The Earth version is easier."

*[Pause. Look at judges. LEDs back to full warm white. Plant alive.]*

> "Because on Mars, there is no second chance."

**40 seconds. Earth transfer. Specific stat. Clean close. Plant alive = visual full circle.**

---

## WHAT WE DO NOT SAY IN THE PITCH

| Don't say | Why | Say instead |
|-----------|-----|-------------|
| "Creates new crop science" | Unverifiable, Syngenta scientist will destroy it | "Makes Syngenta's science work where no expert can be" |
| "Knowledge creation" | Academic, confuses judges | "Gets smarter every day" |
| "Monte Carlo simulation" | Jargon | "100 simulations" |
| "BBCH 65" | Judges don't know growth stages | "Most vulnerable growth phase" |
| "Kubernetes" | Only 1 judge speaks K8s | Save for Q&A: "If you know K8s, the architecture will feel familiar" |
| "12 agents" | Sounds like complexity for complexity's sake | "Five specialist agents" (show 5 in log, others exist for Q&A) |
| "Nitrogen fixation" | WRONG in hydroponics | Don't mention companion planting at all |
| "The greenhouse feeds the crew" | Math doesn't work | "Provides what rations can't — fresh vitamins, iron, morale" |

---

## THE ICEBERG RULE

**Show 10% in the pitch. Let judges discover 90% in Q&A.**

Dashboard: 4 panels maximum visible at any time.
- Agent log (scrolling, color-coded)
- Water/energy gauges
- CME countdown (appears on alert)
- Zone status (simple green/amber/red)

Everything else (nutrition tracking, triage cards, flight rules panel, simulation lab, mission timeline, companion planting, O2 indicator) exists but is NOT shown unless asked.

**Why:** The team that shows 4 polished panels beats the team that shows 12 rough ones. Judges score what they SEE, and a clean dashboard says "product" while a busy one says "hackathon project."

---

## Q&A DEPTH (the 90% iceberg)

When judges probe, you have answers:

**"Show me the KB query live."** → Trigger a scenario. Agent log shows query + response + decision change.

**"How does the simulation work?"** → "Growing Degree Days, Liebig's Law, VPD-based disease prediction — standard agronomy since 1960, parameterized from Syngenta's KB. 100 Monte Carlo runs with perturbed parameters. Pure Python, no LLM involvement in the math."

**"Why 5 agents, not 1?"** → "One agent collapses to the loudest objective. FLORA advocates for the plant. AQUA advocates for water. VITA advocates for crew health. They disagree — and the disagreement surfaces tradeoffs a single agent would miss."

**"Does it really learn?"** → "After every event, it compares predicted vs actual outcomes. When the delta exceeds a threshold, it proposes a new rule with evidence. The rule is validated by re-running simulations — with the rule active vs without. Only promoted if outcomes improve."

**"What about Earth?"** → "Same architecture, same KB, different data. Climate change creates conditions that never existed before — unprecedented heat, new pest patterns, rainfall shifts. EDEN's ability to reason under novel constraints is exactly what Earth agriculture needs."

**"Is this really multi-agent or just different prompts?"** → "Real Strands SDK agents with real @tool decorators. 3-round deliberation where agents disagree BY NAME. Round 2: 'I disagree with CHRONOS because...' A single prompt can't generate genuine adversarial tension."

**"What was the hardest decision?"** → [Team answers honestly about a real technical tradeoff from the build]

---

## CRITICAL FIXES BEFORE PITCH (priority order)

| # | Fix | Time | Why |
|---|-----|------|-----|
| 1 | **HARD STOP building 4h before pitch** | — | Sleep, eat, rehearse. Exhausted teams lose. |
| 2 | **Rehearse full pitch 3x with timer** | 45 min | THE highest-ROI activity. Time every beat. |
| 3 | **Fix companion planting → VOC or remove entirely** | 10 min | One wrong claim = all claims questioned |
| 4 | **Deploy AgentCore Runtime (Lab 04)** | 30 min | AWS bonus is not optional |
| 5 | **Dashboard: 4 panels only in demo mode** | 30 min | Iceberg rule. Hide the rest. |
| 6 | **Agent log font 18px+, Sol counter 48px+** | 15 min | Readable from 5 meters |
| 7 | **Dashboard color transitions (green→amber→red→green)** | 1h | 70% of visual storytelling |
| 8 | **Record backup video of full demo** | 30 min | Insurance |
| 9 | **Test demo on phone hotspot** | 10 min | WiFi backup |

---

## STAGING (from 662-line blueprint)

- **Plant** at front edge of table, closest to judges
- **Lars** speaks, left of plant (judges see: person + plant + screen)
- **Bryan** drives keyboard, behind screen
- **Johannes** manages prop, ready to reset
- **PJ** has phone hotspot + backup video queued
- **Fan running audibly** during nominal (its silence IS the crisis signal)
- **Verbal cues** trigger all tech transitions (not timestamps)
- **Closing line** delivered looking at judges, NOT at screen

---

## THE TEST

After the pitch, apply this test:

> *"Can a judge who zoned out for 30 seconds still explain EDEN to the judge next to them?"*

**Answer:** "It's an AI that predicted a solar storm 50 hours early on Mars, prepared the greenhouse, survived with 3% crop loss instead of 40%, and then taught itself to do it better next time. It uses Syngenta's crop science data. And it works for Earth farming too."

If your judge can say that, you win.

---

## WHAT SURVIVED 14 ADVERSARIAL AGENTS

| Claim | Status |
|-------|--------|
| "Creates new crop science" | KILLED — unverifiable |
| "Knowledge flywheel" | DEMOTED to Q&A — too abstract for pitch |
| "Sees the future and gets smarter" | SURVIVED — demonstrable in 3 minutes |
| "KB changes the decision" | SURVIVED — one sentence in Beat 2 |
| Simulation engine (real math) | SURVIVED — defensible in Q&A |
| Physical prop (LEDs dim) | SURVIVED — the moment judges remember |
| 3-second silence | SURVIVED — confirmed by 4 independent agents |
| Council debate (visible reasoning) | SURVIVED — but show 5, not 12 |
| Earth transfer (1:5000 ratio) | SURVIVED — but 30 seconds, not 45 |
| "Flight rules grow from 50 to 300" | SOFTENED to "250" — more credible |
| Honest nutritional framing | SURVIVED — strength, not weakness |
| 4-layer architecture | DEMOTED to Q&A — say it in one breath if at all |
