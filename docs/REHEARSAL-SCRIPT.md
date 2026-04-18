# EDEN — Rehearsal Script (FINAL)

> **Storyline B: "Two Farms, One Problem"**
> This is the script the speaker memorizes. 165 seconds. 15 seconds margin.
> Rehearse 3x with a timer before the pitch.

---

## BEFORE YOU START

- Plant on table, LEDs warm white, card: "SOL 280 | EDEN OPERATIONAL"
- Dashboard live on screen behind you
- Fan running softly (audible)
- Lars speaks. Bryan drives. Johannes on prop. PJ on backup.
- Speaker faces judges. NEVER reads from screen.

---

## THE SCRIPT

### BEAT 1: GRACE (0:00 — 0:30)

> Grace Wanjiku has two acres outside Nakuru, Kenya. She grows maize and kale for her family and sells the surplus at the Thursday market.
>
> Last March, the rains didn't come. She stood in her field and watched the leaves curl inward, one row at a time. She knows exactly what a dying plant looks like. She just doesn't know what to do about it.
>
> No agronomist is coming. The nearest one serves five thousand other farmers.

*[~70 words, ~28 seconds. Speak calmly. No rush. Let Grace be real.]*

---

### BEAT 2: THE CUT (0:30 — 1:00)

> Now. Different sky. Same problem.

*[PAUSE 2 seconds. Let the transition land.]*

> 227 million kilometers away, four astronauts have a greenhouse. Their only source of fresh food for 450 days. NASA calls fresh food a psychological countermeasure — same category as exercise. Because after 60 days of freeze-dried meals, food stops being food. It becomes chewing.
>
> The water is running out. A dust storm is building. And the same question Grace has: which crops do I save? Which do I let die? Nobody is coming to help.

*[~75 words, ~30 seconds. The NASA "psychological countermeasure" line legitimizes the food-morale angle.]*

---

### BEAT 3: THE SAME KNOWLEDGE (1:00 — 1:35)

> We built an AI called EDEN to answer that question. And the strange thing is — it gives Grace and the astronaut the same answer. Because the crop science is the same.

*[Gesture to the basil plant.]*

> This is a real plant. Real sensors. Our AI is monitoring it right now, using Syngenta's crop science knowledge base — the same data agronomists use in the field.
>
> "The drought-tolerant crop survives three more days without water. The vulnerable one doesn't. Redirect the water. Save what matters most."
>
> That decision works on both planets.

*[~80 words, ~32 seconds. The gesture to the plant is casual, not theatrical.]*

---

### BEAT 4: THE STORM (1:35 — 2:05)

> On Mars, the storm hits.

*[Bryan triggers CME on dashboard. Green → amber.]*

> EDEN detects a solar event 50 hours out using live NASA data. It runs three strategies in simulation and picks the one that loses 3 percent instead of 40.

*[Water gauge climbing on screen. Battery charging.]*

> It starts stockpiling water while the sun still shines. Pre-harvests the fragile herbs to lock in nutrition. Five specialist agents disagree about priorities — and you can watch the argument happen in real time.

*[LEDs dim. Fan stops. SILENCE — count 1... 2... 3...]*

> *(quietly)* In Kenya, Grace doesn't have EDEN. She loses 40 percent.
>
> Same crop science could have saved both.

*[~80 words + 3 second silence, ~35 seconds. The silence is THE moment. Do not rush it.]*

---

### BEAT 5: THE LEARNING (2:05 — 2:20)

> After every crisis, EDEN writes a new rule. "Start stockpiling earlier." "These crops are tougher than we thought."
>
> Day one: fifty rules from textbooks. Day 450: three hundred rules from experience. The system teaches itself.

*[~35 words, ~15 seconds. Short and punchy.]*

---

### BEAT 6: THE BRIDGE (2:20 — 2:45)

> Mars forced us to build the hardest version of something the world desperately needs: an expert that's always there, that knows the science, that learns from every season, and that works when no one else is coming.
>
> Eight hundred million people are food insecure. They don't need a Mars greenhouse. They need what's inside it.

*[~55 words, ~22 seconds. Slow down here. This is the thesis.]*

---

### BEAT 7: CLOSE (2:45 — 2:55)

*[LEDs return to full warm white. Fan resumes. Plant alive.]*

*[Look directly at the judges.]*

> We built this for Mars. But we built it for Grace.

*[Hold. 2 seconds of silence. Then:]* "Thank you."

*[~15 words, ~10 seconds. Do NOT look at the screen during the close.]*

---

**TOTAL: ~410 words at 150 wpm = ~164 seconds. + 5 seconds of pauses = ~169 seconds. 11 seconds margin.**

---

## CHALLENGE REQUIREMENTS CHECKLIST

| Requirement | Where it appears | How judges see it |
|---|---|---|
| **Monitor & Control Environment** | Beat 3: "Real sensors. Our AI is monitoring it right now" | Live dashboard, real plant |
| **Manage Resources** | Beat 4: "Stockpiling water while the sun still shines" | Water gauge climbing on screen |
| **Detect & Respond to Stress** | Beat 4: "Detects a solar event 50 hours out" + Beat 2: food-as-morale | CME detection, KB query |
| **Optimize / Learn / Adapt** | Beat 5: "Day one: 50 rules. Day 450: 300" | Agent log shows new rule |

---

## PROP CHOREOGRAPHY

| Time | Plant LEDs | Fan | Dashboard |
|---|---|---|---|
| 0:00-1:35 | Warm white (on) | Running (audible) | Nominal, green |
| 1:35 | Begin dimming | — | Green → amber |
| 1:38 | Dim | Stops | Amber, countdown appears |
| 1:38-1:41 | Dim | Off | **3 SECONDS SILENCE** |
| 1:41-2:05 | Dim | Off | Red, agent debate, water climbing |
| 2:05-2:45 | Gradually brightening | — | Returning to green |
| 2:45 | Full warm white | Resumes | Green, nominal |

---

## IF THINGS GO WRONG

| Problem | Response |
|---|---|
| WiFi dies | PJ switches to phone hotspot. Dashboard has cached data. Keep talking. |
| Dashboard freezes | "Let me show you what this looks like" — describe while Bryan troubleshoots |
| LEDs don't dim | Skip the silence. Say "On the dashboard, the system enters crisis mode" |
| Agent call slow | Narrate over it: "The agents are reasoning right now — here's what they'll decide" |
| Over time at 2:45 | Skip Beat 6 entirely. Go straight to close: "We built this for Mars. But we built it for Grace." |
| Brain freeze | Look at plant. Touch it. "This plant is alive because an AI is taking care of it. That's what we built." Reset from there. |

---

## Q&A READY (keep in back pocket)

**"How does this use Syngenta's KB?"**
> "Every decision the AI makes references Syngenta's crop science data — stress thresholds, growth stages, nutritional profiles. In the demo, you can see the agent querying the knowledge base and the result changing its decision."

**"What about the AWS architecture?"**
> "We use Bedrock with the Strands Agents SDK for the AI backbone, and AgentCore Gateway for the Syngenta knowledge base connection. The multi-agent debate runs in parallel using real tool calls, not scripted responses."

**"Does it actually learn?"**
> "After every event, it compares what it predicted to what happened. When it finds a gap, it writes a new rule. We can show you one being created right now."

**"Why multiple agents?"**
> "One agent collapses to the loudest objective — usually calories. With specialists, the nutritionist catches what the resource manager misses. The disagreement IS the value."

**"What about the food psychology angle?"**
> "NASA formally classifies fresh food as a psychological countermeasure. In isolated environments, food variety is ranked the number one habitability factor — above sleep, above privacy. The greenhouse isn't a luxury. It's mental health infrastructure."

**"Is the plant real?"**
> "Yes. Real basil, real sensors reading right now, real AI making decisions about it. Touch it."

---

## THE ONE THING TO REMEMBER

If you forget everything else, remember this:

**Tell them about Grace. Show them the plant. Let the lights go dark. And hold the silence.**

That's the pitch. Everything else is detail.
