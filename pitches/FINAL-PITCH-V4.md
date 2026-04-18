# EDEN — Final Pitch V4

> Apple rules: If the demo shows it, don't say it. Three movements. 650 words. The plant is the product.

---

## BEFORE

- Valentina on table. LEDs warm white. Fan humming softly.
- Card: "SOL 280 | EDEN OPERATIONAL"
- Dashboard live. Dark. Atmospheric. Sol counter ticking.
- Gently crush two basil leaves. Say nothing about it.
- As previous team packs up, Lars turns to judges: "This is Valentina. Real basil. Three weeks old."
- Then turns back. Sets up. Says nothing else until the clock starts.

---

## MOVEMENT 1 — "Valentina" (0:00–1:00)

*"She's alive."*

**3 seconds. Let them look at her.**

*"For the last 24 hours, an AI has been watering her, adjusting her light, checking her soil. Every decision logged. Every reading live. Nobody asked it to. Nobody was awake."*

**Gesture to dashboard. Don't explain it. Let it breathe.**

*"We were asked to build an autonomous AI to manage a greenhouse on Mars. Four astronauts. 450 days. 22 minutes from the nearest help."*

*"On Mars, what you grow is what you eat. And after 60 days of the same freeze-dried meals, food stops being food. NASA calls fresh produce a psychological countermeasure — same category as exercise. The greenhouse isn't a luxury. It's how people stay human."*

*"So we built EDEN. And it's running right now. On this table."*

**~120 words. ~50 seconds. 10 seconds of silence built in.**

---

## MOVEMENT 2 — "Watch" (1:00–3:30)

*"Let me show you what it does. Live. On a real plant."*

**Walk to Valentina. Block the light sensor.**

*"I just cut her light."*

**5 seconds. Say nothing. Let the dashboard update. Let judges watch.**

*"Flight rules caught it. Under a second. Deterministic. No AI needed."*

**Point to agent log. Let it scroll.**

*"But underneath — twelve specialists are reasoning about this right now. AQUA is checking the energy budget. VITA is checking if this crop is on a nutritional timeline."*

**Point to one line in the log.**

*"See that? That's FLORA. She speaks as the plant."*

**Read it quietly, as if discovering it with the judges:**

*"'I can feel the light dropping. I need it back. I'm mid-growth.'"*

**Let it sit for 2 seconds.**

*"No other system gives voice to what it's protecting."*

**Restore light. Readings normalize.**

*"Back to nominal."*

**Brief pause. Shift tone — quieter, more serious.**

*"Now let's see what happens when something worse comes."*

**Bryan triggers CME. Dashboard: green → amber. Countdown appears.**

*"A real coronal mass ejection. NASA data. 1,247 kilometers per second. EDEN calculates: 50 hours to impact."*

**Point to log. Agents debating. Water gauge climbing.**

*"ORACLE ran 100 simulations. Standard protocol: 40% crop loss. EDEN's protocol: 3%. It picked that. Water reserves climbing. Battery charging."*

**LEDs shift: warm white → amber → dim red. Fan slows.**

*"And now the triage."*

**LEDs go dim. Fan stops.**

**[THREE SECONDS. SAY NOTHING. COUNT IT.]**

*Quietly:*

*"EDEN chose to save the wheat. The basil had to go. Commander Chen requested it three times this week."*

**Beat.**

*"The system remembered what she wanted. And it let it die anyway."*

**Beat.**

*"Because the crew needs vitamin C more than they need variety. And EDEN doesn't hide that cost."*

**Another beat. Then, matter-of-fact:**

*"After the storm: predicted 3%, actual 4.1%. EDEN wrote a new rule — start stockpiling two hours earlier. That rule didn't exist yesterday. It does now."*

**LEDs warming back. Fan resumes.**

*"Sol 1: fifty rules from Earth. Sol 450: over 250. All self-taught."*

**~250 words + 15 seconds of silence. ~150 seconds total.**

---

## MOVEMENT 3 — "Grace" (3:30–5:00)

**Step back to speaking position. Face judges directly. No screen.**

*"Everything you just saw runs on Syngenta's crop science knowledge base. The same data your agronomists use in the field."*

**Pause.**

*"Grace Wanjiku has two hectares outside Nakuru, Kenya. Family of six. The rains didn't come last March. She stood in her field and watched the leaves curl, one row at a time."*

*"She's making the same decisions EDEN just made. What to save. What to let go. She's making them alone."*

*"Same Syngenta science. Same constraints. Different sky."*

**Pause.**

*"Cropwise tells farmers their field has a problem. EDEN tells itself what to do about it — and does it."*

*"Mars forced us to build the hardest version. The Earth version is easier."*

**Walk to Valentina. Look at her for 1 second. Then back to judges.**

*"Whoever built Syngenta's crop science knowledge base — their work just kept four astronauts fed for 450 days."*

**Half-step toward judges. Eye contact. One judge.**

*"What if the first farm on Mars was designed by an AI that learned from Syngenta?"*

**[3 SECONDS. SILENCE. DO NOT MOVE.]**

Softly: *"Thank you."*

**~165 words. ~90 seconds. Plant glowing. Fan humming. Alive.**

---

**TOTAL: ~535 words spoken + ~30 seconds of deliberate silence = ~4:50. 10 seconds margin.**

---

## What's NOT in the pitch (saved for Q&A)

| Topic | When to deploy |
|---|---|
| Twelve agents by name | "How many agents?" → "Twelve. PATHFINDER the mycologist, HESTIA the crew psychologist, CHRONOS the mission planner..." |
| The Architect (farm designer) | "What else can it do?" → "Before Sol 1, EDEN designs the entire farm from constraints. Give it crew size, cargo, seeds — it outputs a 450-day plan." |
| Immune system metaphor | "How does the architecture work?" → "Skin stops what it can — flight rules. White blood cells handle what gets through — agent council. Every infection it survives, it remembers." |
| Strands SDK / ThreadPoolExecutor | "How does multi-agent work?" → "Real Strands SDK agents with @tool decorators. Parallel via ThreadPoolExecutor. Three-round deliberation. They disagree by name." |
| Food psychology research | "Why does food matter?" → "Stuster's research: food is the #1 habitability factor. Above sleep. Above privacy." |
| Mock pricing slide | "What would you build next?" → "Funny you should ask." [show slide] |
| The reconciler | "How often does it check?" → "Every 30 seconds. Reality vs plan. Match: do nothing. Diverge: council convenes." |
| Honest nutritional framing | "Can the greenhouse feed the crew?" → "No. Rations cover 82% of calories. The greenhouse provides what rations can't — fresh vitamin C, iron, folate. And morale." |
| AgentCore Runtime | "How does this use AWS?" → "Bedrock via Strands. AgentCore Gateway for Syngenta KB. AgentCore Runtime for deployment. Real MCP tool calls." |
| "What if AI is wrong?" | "Flight rules are the safety net. Deterministic, no AI. The AI proposes. Rules constrain. Crew overrides. Autonomous-with-guardrails." |
| Polyculture intelligence | "What about crop diversity?" → "Industrial farming chose monoculture because diversity was too hard to manage. EDEN proves that's no longer true." |

---

## The Apple Test

Read the pitch aloud. At every sentence ask: **"Does the demo already show this?"**

If yes → cut the sentence.

What remains is the pitch.

---

## Timing

| Movement | Start | End | Words | Silence | Feel |
|---|---|---|---|---|---|
| 1: Valentina | 0:00 | 1:00 | 120 | 10s | Quiet curiosity → understanding |
| 2: Watch | 1:00 | 3:30 | 250 | 15s | Tension builds → silence → gravity → relief |
| 3: Grace | 3:30 | 5:00 | 165 | 5s | Expansion → conviction → open question |

---

## Three Silences

These are the pitch. Everything else is connective tissue.

| When | Duration | What judges feel |
|---|---|---|
| 0:03 — after "She's alive." | 3 seconds | Curiosity. "Wait, the plant?" |
| ~2:30 — LEDs dim, fan stops | 3 seconds | Dread. Something is wrong. The plant. |
| 4:50 — after the open question | 3 seconds | The question hangs. Unanswered. They carry it into deliberation. |

---

## Cue Sheet

| Lars says | Who acts | What happens |
|---|---|---|
| "I just cut her light" | Lars | Physically blocks sensor |
| — (5 seconds later) | Bryan | Dashboard shows detection |
| "Now let's see what happens when something worse comes" | Bryan | Trigger CME alert. Green → amber. Countdown. |
| Lars moves toward plant | Johannes | LED shift: warm → amber (slow) |
| "And now the triage" | Johannes | LED amber → dim red (fast). Fan OFF. |
| "Sol 1: fifty rules" | Johannes | LED recovery: dim → warm white. Fan ON. |

---

## If Things Break

| Problem | Response |
|---|---|
| Demo doesn't respond | "Watch the dashboard." Wait 5 more seconds. If still nothing: "The system is reasoning — here's what it decides" and narrate. |
| LEDs fail | The silence still works. Lars still stops talking. The dashboard still goes red. |
| WiFi dies | PJ: hotspot. Dashboard falls back to cached state. |
| Over time at 4:30 | Cut Grace to one sentence: "Same Syngenta science. Different sky." Then close. |
| Brain freeze | Touch Valentina. "This plant is alive because an AI is taking care of her. That's what we built." |

---

## The Water Cooler Sentence

What judges say at dinner:

> *"Did you see the team with the real plant — Valentina? The AI argued about whether to save her, and then the lights went out and nobody spoke for three seconds. And the presenter just stood there. And then he said the AI remembered what the astronaut wanted and let it die anyway. I'm still thinking about it."*
