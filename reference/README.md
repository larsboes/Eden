# reference/ — Challenge Source Materials

This directory contains **raw inputs from the organizers and external sources** — the challenge constraints, provided tools, and API documentation. These are facts, not our decisions.

## Files

| File | What it contains | Key info |
|------|-----------------|----------|
| **CHALLENGE_BRIEF.md** | Official Syngenta challenge text | 4 astronauts, 450 days, maximize nutrients, working agent required |
| **SLIDES.md** | Annotated analysis of the 7 organizer slides | Judging criteria, architecture hints, "42" easter egg, Earth angle |
| **hackathon-overview.md** | Challenge description from START HACK site | Same as brief + Syngenta company context |
| **hackathon-getting-started.md** | Official getting-started guide | Amplify setup, MCP endpoint, Kiro IDE, Strands SDK |
| **AWS_BLUEPRINT.md** | AgentCore technical blueprint (Labs 01-06) | Code patterns for Gateway, Runtime, OpenAPI-to-MCP, deployment |
| **agriculture-on-mars.md** | Full challenge deep dive text | Users, data, technology, judging — the canonical challenge doc |
| **nasa-api-status.md** | Tested NASA API endpoints | DONKI CME/MPC (LIVE), InSight (frozen), Mars Rover Photos (DEAD) |
| **external-links.md** | All URLs — hackathon, repos, APIs, docs | MCP endpoint, NASA API key, AgentCore samples, Strands SDK |
| **enablement-session.pdf** | Original PDF of the enablement slides | Source for SLIDES.md |

## Relationship to other directories

- **`reference/`** = what we were GIVEN (challenge rules, tools, APIs, constraints)
- **`docs/`** = what we DECIDED (our architecture, PRD, strategy) — see `docs/README.md`
- **`brainstorm/`** = how we got from raw ideas to the EDEN concept

## Critical facts from these files

- **MCP Endpoint**: `https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp`
- **NASA API Key**: `YOUR_NASA_API_KEY`
- **Region**: us-east-1 (workshop), us-east-2 (Syngenta KB gateway)
- **Judging**: Creativity 25% | Functionality 25% | Visual design 25% | Pitch quality 25% | AWS bonus
- **Non-negotiable**: Working agent system behind the PoC (can't fake it), must use AgentCore
