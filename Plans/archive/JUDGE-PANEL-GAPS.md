# EDEN — Judge Panel Gap Analysis

> Council debate: 4 judge personas × 3 rounds. Evaluated full EDEN concept.
> Date: 2026-03-19

## Critical Gaps (Prioritized by ROI)

### DO FIRST (30min each, massive impact)

**GAP 2: BBCH Growth Stages + Precision Ag Vocabulary**
- Add to agent system prompt: BBCH codes, VPD (Vapor Pressure Deficit), EC (Electrical Conductivity), DLI (Daily Light Integral)
- Agent should say "Wheat at BBCH 60 (flowering)" not "Wheat at day 65"
- Query Syngenta KB for growth-stage-specific thresholds
- Syngenta scientist will test for this vocabulary — it signals real agricultural knowledge
- 30 minutes. System prompt + KB query update.

**GAP 3: AgentCore Runtime Deployment**
- Follow Lab 04: Docker → ECR → AgentCore Runtime (4 lines of code)
- Biggest AWS bonus point for least effort
- Shows you actually used the infrastructure they built for this hackathon
- 30 minutes following the tutorial.

### FREE (0 build time)

**GAP 6: Human Moment in Demo**
- Add ONE line referencing a crew member by name during triage
- "Dr. Chen requested spinach three times this week. The agent knows. But the math says no."
- 0 implementation time. Write it into the pitch script.

### DO AFTER DEMO WORKS (30min)

**GAP 5: Demo Backup Video**
- Pre-record 30-second video of CME → Virtual Lab → Stockpiling sequence
- Play if live demo breaks ("Let me show you what happens")
- NON-NEGOTIABLE. Every winning team has a backup.

### HIGH PRIORITY (1h each)

**GAP 4: KB Query + Response Visible in Agent Log**
- Don't just show "Querying Syngenta KB..."
- Show: "KB Response: Wheat at BBCH 60-69 is highly sensitive to UV-B. Yield reduction: 15-40%."
- Proves the integration is real, not faked
- 1 hour. Format the KB response in the agent log stream.

**GAP 8: Font Sizes for Projection**
- Agent log: 18-20px minimum
- Sol counter: 48px+
- Countdown timer: 64px+
- Max 4-5 agent log lines visible at once
- Test on external monitor/projector if possible
- 30 minute CSS pass.

### MEDIUM PRIORITY (if time allows)

**GAP 1: Dashboard State Machine (Progressive Disclosure)**
- 4 visual states: NOMINAL → ALERT → CRISIS → RECOVERY
- NOMINAL: Full dashboard, calm, muted
- ALERT: 60% screen = CME alert + countdown + Virtual Lab. Panels compress. Amber tint.
- CRISIS: Water gauge + triage primary. Countdown massive. Red accents. LEDs dim.
- RECOVERY: Gradual return to nominal. Warm colors.
- 3-4 hours frontend work. Biggest visual impact but most time-consuming.
- Alternative: just do the color shift (background tint change on alert) — 1h for 70% of the effect.

**GAP 7: Custom Gateway Target for DONKI**
- Wrap DONKI OpenAPI spec as MCP tool through own AgentCore Gateway target
- Shows you created custom gateway targets, not just used the provided one
- 1-2 hours following the OpenAPI→MCP tutorial
- High AWS bonus value.

## Scope Recommendation (Unanimous)

**BUILD WELL:**
- Tier 1: CME prediction + water stockpiling
- Tier 3: Council agents + ethical triage
- Tier 4: Nutritional tracking (answers the challenge prompt)

**SKIP ENTIRELY:**
- Tier 5: Sol Forecast Timeline (beautiful but not essential for demo)
- Tier 6: Flight Rules self-improvement (mention in pitch, don't build)

**POUR SAVED TIME INTO:**
- Dashboard polish (state machine or at minimum color transitions)
- Demo rehearsal (at least 3 full runs)
- Backup video recording

## Demo: Keep Only 5 Moments

1. "The loneliest farmer" hook + Sol counter ticking
2. CME alert + countdown appears (THE visual transition)
3. Virtual Lab: 3 strategies, C selected (agent CHOSE)
4. Water gauge climbing (agent is PREPARING)
5. Earth mirror: "4 astronauts → 4 billion farmers"

Everything else: Q&A depth only.

## Pitch Rules

- Never say "Kubernetes" (say "container orchestration principles" if needed)
- Never show architecture diagrams in the pitch (show the DASHBOARD)
- Never list AWS services (say "powered by AWS" once — list is for Q&A)
- One person touches the keyboard (Bryan)
- Pre-record backup video after demo works
