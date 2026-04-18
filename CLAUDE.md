# AstroFarm - Martian Greenhouse AI Agent

Hackathon: Syngenta x AWS START HACK 2026

## Challenge

Build an autonomous AI agent system to manage a Martian greenhouse.

- Crew: 4 astronauts, 450-day Mars mission
- 22-min communication latency to Earth — agent MUST work autonomously
- Monitor & control: temperature, humidity, light, water
- Manage & recycle: water, nutrients
- Detect plant stress: nutrient deficiencies, disease → automated response
- Optimize growth: learn and adapt over time

## Deliverables

1. Working PoC — simulation or digital twin with a REAL AI agent behind it (can't fake it)
2. 3-minute pitch (PowerPoint)

## Judging (equal weight)

- Creativity 25%
- Functionality, accuracy, applicability 25%
- Visual design & ease of use 25%
- Quality of pitch 25%
- BONUS: extra points for using AWS tools

## Team

4 members: Lars, PJ, Johannes, Bryan
Each has a personal Claude agent. Coordinator agent in the "lead" tmux window.

## Tech

- AWS Bedrock for Claude models (us-west-2)
- Agent Teams enabled for inter-agent communication
- Shared repo — coordinate via RELAY.md and git

## Key Insight

Mars latency means no real-time API calls to Earth. The AI agent needs local/edge intelligence that syncs with Earth for long-term knowledge updates.
