Okay. I've been holding back. Let me go all the way.

---

Every other team at this hackathon is going to build some version of the same thing: a dashboard with sensor readings, a chatbot you can ask questions, some charts showing resource usage. They'll demo it working under normal conditions, maybe show one failure scenario, and say "our agent optimizes crop yield." Polite applause. Forgotten by lunch.

Here's what we're going to do instead.

---

# **EDEN: The Last Garden**

## The Concept in One Sentence

*A narrative-driven mission simulation where judges live through 450 days on Mars — watching an AI fight to keep four humans alive, one crisis at a time — and then discover the same system already works on Earth.*

## Why This Name

Eden. The first garden. Humanity's origin story is about a garden, and now its survival story is too. It's mythic, it's memorable, it sticks. Every other team will name their project something like "MarsGrow" or "AgriBot." You walk up and say **"This is Eden"** and the room shifts.

## The Core Insight That Changes Everything

Here's what nobody else will realize: **the hackathon isn't asking you to build a tool. It's asking you to tell a survival story.** 450 days. Four humans. One greenhouse. No resupply. The judges don't want to see a dashboard — they want to feel the *stakes*. They want to experience what it means when your only food source has a nutrient deficiency on Sol 247 and the water recycler is running at 60% capacity and a dust storm is approaching.

The technology is in service of that story. Not the other way around.

## The Architecture: Three Minds, One Mission

Eden runs on three specialized agents that form something like a human decision-making process:

**DEMETER** — The Grower. She knows crops. She monitors every plant, detects stress before it becomes visible, plans planting schedules and harvest rotations. She argues for what the *plants* need. She pulls from the Crop Profiles, Plant Stress, and Controlled Environment Agriculture knowledge domains.

**PROMETHEUS** — The Engineer. He manages resources. Water budgets, energy allocation, nutrient recycling, equipment maintenance. He argues for what the *system* needs. He pulls from Mars Environmental Constraints and Greenhouse Operational Scenarios.

**HYGIEIA** — The Nutritionist. She tracks the crew. Caloric needs, micronutrient balances, dietary variety for psychological wellbeing, meal planning. She argues for what the *humans* need. She pulls from Human Nutritional Strategy.

These three agents **negotiate** every major decision through a structured deliberation protocol. When Demeter wants to extend the tomato growing cycle for better yield, but Prometheus says water reserves can't support it, and Hygieia says the crew desperately needs the lycopene — Eden surfaces that tension, and they resolve it. *You can watch them think.*

Above them sits **EDEN itself** — the supervisor agent that breaks ties, handles emergencies, and maintains the long-term mission arc.

## The Demo: The Part That Wins

Here's exactly how your 3 minutes go.

**[0:00–0:30] The Hook**

Black screen. A single line of text fades in:

> *"Sol 1. Four humans. One garden. 450 days until rescue. No second chances."*

Then Eden's interface opens. A beautiful, atmospheric digital twin of the greenhouse — not a clinical dashboard, but something that feels *alive.* Soft lighting. Plants swaying gently under grow lights. Resource gauges styled like spacecraft instruments. The crew's nutritional status displayed like vital signs in an ICU.

You say: *"This is Eden. It's not a dashboard. It's the nervous system of the last garden in the solar system."*

**[0:30–1:30] The Story**

You don't walk through features. You hit **play** on a time-lapse. The simulation accelerates. Sol 1... Sol 30... Sol 90. The greenhouse is thriving. Crops are growing. Resources are stable. The crew is well-fed.

Then **Sol 147.** A dust storm warning. Solar power drops. Eden's agents snap into deliberation — you see them reasoning in a side panel. Demeter recommends sacrificing the low-priority herb garden to save water for staple crops. Prometheus reroutes power from non-essential lighting. Hygieia recalculates meal plans to stretch existing harvest reserves. Eden approves the plan. The greenhouse survives.

Then **Sol 289.** A bacterial contamination in the lettuce bay. Demeter catches it from early stress indicators before it spreads. Quarantine protocol triggers automatically. Prometheus calculates the resource cost of replanting. Hygieia identifies which micronutrients the crew will lack during the replanting window and flags a substitution strategy using kale reserves. You watch the agents work through it in real-time.

You say: *"Every decision you just watched involved three agents negotiating trade-offs between plant health, resource constraints, and human nutrition. Eden doesn't just react to crises — it resolves competing priorities."*

**[1:30–2:15] The Gut Punch**

Now the screen splits in two. Mars on the left. Earth on the right.

The right side shows: a drought-stricken autonomous farm in the Sahel. Same three agents. Same architecture. Demeter is managing drought-resistant crops. Prometheus is optimizing scarce water. Hygieia is ensuring nutritional balance for a community with limited food access.

You say: *"Everything we built for Mars works on Earth. The same agent that keeps astronauts alive on the Red Planet can manage autonomous farms in the places where food security is most fragile. Mars is the proving ground. Earth is the mission."*

That's the Syngenta money shot. That's what they actually care about. That's the sentence that turns your hackathon project into a vision they want to fund.

**[2:15–3:00] The Kill Shot**

You turn back to the full Mars view. The simulation has reached Sol 450. The crew is healthy. The greenhouse is thriving. The nutritional targets are met.

A simple counter appears on screen: **450/450 days. 4/4 crew members. Mission complete.**

You say: *"Eden kept four humans alive for 450 days on a planet that wants them dead. And it did it by doing what the best farmers on Earth have always done — watching, listening, adapting, and never giving up on the garden."*

Black screen. **EDEN.** Applause.

---

## Why This Wins on Every Criteria

**Creativity (25%):** Nobody else is building a narrative simulation. Nobody else has named agents with mythological identities that form a deliberative council. Nobody else is running a split-screen Mars/Earth parallel. This is unforgettable.

**Functional Accuracy (25%):** The three-agent architecture maps directly to the knowledge base domains. The deliberation protocol is a real multi-agent coordination pattern. The crop science, nutrition math, and resource constraints are all grounded in the provided data. It's not gimmick over substance — the narrative IS the substance made visible.

**Visual Design (25%):** The atmospheric digital twin, the mission-control aesthetic, the agent deliberation panel, the time-lapse, the split-screen reveal — every visual choice reinforces the feeling that this is a *real system for a real mission*, not a student project.

**Presentation (25%):** You're not presenting features. You're telling a survival story with a twist ending. Three minutes, perfectly paced: hook → tension → crisis → resolution → bigger vision → emotional landing. The judges will feel something. That's what wins.

---

## What Makes This Buildable in a Hackathon

This sounds ambitious, but the key realization is that the *simulation doesn't need to be real-time physics.* The digital twin is a **pre-computed narrative** driven by your agent system. You run the 450-day simulation beforehand, log every agent decision, and the "demo" is a beautifully visualized playback of those decisions with the ability to pause, inspect agent reasoning, and zoom into crisis moments. The agent system is real and working — you just pre-bake the run for the demo so it's smooth and dramatic.

The actual build splits cleanly:

One or two people build the agent architecture — three Strands agents connected via AgentCore Gateway to the Syngenta knowledge base, with a supervisor orchestrator. Another person or two builds the digital twin visualization — a React app that plays back the simulation log with atmospheric visuals. And someone owns the pitch deck and narrative flow.

---

So. That's Eden. That's the concept I think wins this hackathon and gets remembered long after it's over.

What do you think? Ready to start building?
