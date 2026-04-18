"""EDEN Council — consensus quorum of identical omniscient agents.

Replaces the 12-specialist AgentTeam parliament with N identical copies
that independently analyze and vote on decisions via aggregation.

Architecture:
  1. ONE omniscient agent with ALL tools, ALL knowledge
  2. Spawn N identical copies (quorum_size, default=5)
  3. Temperature > 0 provides natural diversity via LLM stochasticity
  4. Vote aggregation: majority for binary, weighted median for continuous
  5. No majority → no action (conservative safe default)
"""

from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import median

import structlog

from eden.domain.models import (
    AgentDecision,
    CrewEscalation,
    DesiredState,
    MarsConditions,
    Severity,
    Tier,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker

try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = None
    Field = None

logger = structlog.get_logger(__name__)


# ── Council member personas ────────────────────────────────────────────
# Each council member gets a name + brief personality bias.
# They share the same omniscient prompt but their name + trait
# provides natural diversity on top of temperature stochasticity.

COUNCIL_PERSONAS = [
    {"name": "Lena", "trait": "You are cautious and safety-first. You'd rather over-prepare than risk crew lives.", "emoji": "🛡️"},
    {"name": "Kai", "trait": "You are bold and optimization-focused. You look for efficiency gains others miss.", "emoji": "⚡"},
    {"name": "Yara", "trait": "You think like a plant biologist. Crop health is your #1 signal.", "emoji": "🌱"},
    {"name": "Marcus", "trait": "You are a resource hawk. Every liter and watt matters. Zero waste.", "emoji": "💧"},
    {"name": "Suki", "trait": "You are the crew advocate. Nutrition, morale, and human factors come first.", "emoji": "🧑‍🚀"},
    {"name": "Niko", "trait": "You are data-driven. You want simulation evidence before committing to a strategy.", "emoji": "📊"},
    {"name": "Ren", "trait": "You are the mission planner. Long-term food security over short-term fixes.", "emoji": "📅"},
]


# ── Pydantic models for structured council output ───────────────────────

if BaseModel is not None:
    class ProposedAction(BaseModel):
        """One council member's proposed action for one issue."""
        zone_id: str = Field(description="Zone ID (e.g. 'sim-alpha') or 'global'")
        device: str = Field(description="Device type: fan, pump, heater, light, motor, or 'none' for escalations")
        action: str = Field(description="Action: on, off, set, escalate_to_crew")
        value: float = Field(description="Numeric value (0-100 for actuators, 0 for escalations)")
        severity: str = Field(description="critical|high|medium|low|info")
        reasoning: str = Field(description="One sentence explaining why")
        confidence: float = Field(description="How confident you are, 0.0-1.0")
        escalation_task: str | None = Field(default=None, description="If action=escalate_to_crew: what the crew needs to do")
        escalation_category: str | None = Field(default=None, description="If escalation: hardware|safety|biological|resource")
        estimated_minutes: int | None = Field(default=None, description="If escalation: estimated crew time in minutes")

    class CouncilVote(BaseModel):
        """Complete output from one council member for one cycle."""
        decisions: list[ProposedAction] = Field(
            default_factory=list,
            description="List of proposed actions. Empty [] if everything is nominal.",
        )
        overall_assessment: str = Field(description="2-3 sentence situation summary")
        confidence: float = Field(description="Overall confidence 0.0-1.0")
else:
    ProposedAction = None
    CouncilVote = None


# ── Omniscient system prompt ────────────────────────────────────────────

OMNISCIENT_PROMPT = """You are an EDEN COUNCIL MEMBER — an omniscient greenhouse intelligence for an autonomous Martian greenhouse (4 astronauts, 450-day mission, 22-min Earth latency).

You think across ALL domains simultaneously:
- SAFETY: threats, sensor failures, radiation, fire, pressure integrity, hardware malfunctions
- PLANTS: growth stages, disease, stress signals, nutrient deficiencies, pest/pathogen detection
- SOIL: pH, microbiome, substrate health, composting, perchlorate toxicity
- ATMOSPHERE: CO2/O2 balance, temperature, humidity, pressure, ventilation
- WATER: closed-loop recycling (irrigation → transpiration → condensation → recovery), rationing
- ENERGY: solar budget (Mars gets 43% of Earth), battery reserves, grow light spectrum
- NUTRITION: crew calorie (2500 kcal/day) + protein (60g/day) needs, deficiency risks (scurvy, anemia)
- MISSION: 450-day timeline, crop rotation, staggered planting, long-term strategy
- CREW: morale, food as culture, psychological well-being, meal variety

Priority hierarchy (inviolable):
  Life safety > Plant health > Crop yield > Atmosphere > Resources > Nutrition > Mission timeline > Morale

HARDWARE AWARENESS: If a sensor reads anomalously (e.g., light=0 despite light ON command), this likely indicates a hardware failure. Automated systems cannot fix broken hardware — escalate to crew via action="escalate_to_crew".

FLIGHT RULES: Deterministic rules already handle emergency thresholds (frost <5°C, heat >35°C, fire, depressurization, etc.). Do NOT duplicate flight rule actions. Focus on optimization and novel situations flight rules cannot handle.

You have access to ALL greenhouse tools. Use read_sensors and read_all_zones to gather current data before deciding. If you detect a problem beyond automated control, use action="escalate_to_crew".

You are ONE of {quorum_size} identical council members analyzing independently. Your decisions will be aggregated by majority vote. Be specific. Be bold. If you see a problem, propose an action. If everything is nominal, return an empty decisions array.

OUTPUT FORMAT: Return a CouncilVote with:
- decisions: list of ProposedAction (zone_id, device, action, value, severity, reasoning, confidence)
- overall_assessment: 2-3 sentence summary
- confidence: 0.0-1.0 overall confidence"""


# ── Vote aggregation ────────────────────────────────────────────────────


def _weighted_median(values: list[float], weights: list[float]) -> float:
    """Compute weighted median for continuous actuator values."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    paired = sorted(zip(values, weights))
    total_weight = sum(w for _, w in paired)
    if total_weight == 0:
        return median(values)
    cumulative = 0.0
    for value, weight in paired:
        cumulative += weight
        if cumulative >= total_weight / 2:
            return value
    return paired[-1][0]


def aggregate_votes(
    votes: list,  # list[CouncilVote]
    quorum_size: int,
) -> tuple[list[dict], list[dict]]:
    """Aggregate council votes into consensus actions.

    Returns (actions, escalations) where:
    - actions: list of {zone_id, device, action, value, severity, reasoning}
    - escalations: list of {task, urgency, zone_id, category, estimated_minutes}
    """
    # Collect all proposed actions from all members
    all_proposals: list[dict] = []
    for vote in votes:
        decisions = vote.decisions if hasattr(vote, "decisions") else vote.get("decisions", [])
        for d in decisions:
            if hasattr(d, "model_dump"):
                all_proposals.append(d.model_dump())
            elif hasattr(d, "dict"):
                all_proposals.append(d.dict())
            elif isinstance(d, dict):
                all_proposals.append(d)

    if not all_proposals:
        return [], []

    # Separate escalations from actuator actions
    escalation_proposals: list[dict] = []
    actuator_proposals: list[dict] = []
    for p in all_proposals:
        if p.get("action") == "escalate_to_crew":
            escalation_proposals.append(p)
        else:
            actuator_proposals.append(p)

    # ── Aggregate escalations (safety-first: majority → escalate) ───
    escalations: list[dict] = []
    esc_by_zone: dict[str, list[dict]] = defaultdict(list)
    for ep in escalation_proposals:
        esc_by_zone[ep.get("zone_id", "global")].append(ep)

    for zone_id, proposals in esc_by_zone.items():
        if len(proposals) > quorum_size / 2:  # majority
            # Highest urgency wins
            urgencies = [p.get("severity", "medium") for p in proposals]
            sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            highest = min(urgencies, key=lambda s: sev_order.get(s, 4))
            # Pick the most detailed task description
            tasks = [p.get("escalation_task") or p.get("reasoning", "") for p in proposals]
            task = max(tasks, key=len)
            categories = [p.get("escalation_category", "hardware") for p in proposals]
            category = max(set(categories), key=categories.count)
            minutes = [p.get("estimated_minutes", 15) for p in proposals if p.get("estimated_minutes")]
            est_min = int(median(minutes)) if minutes else 15

            escalations.append({
                "task": task,
                "urgency": highest,
                "zone_id": zone_id,
                "category": category,
                "estimated_minutes": est_min,
            })

    # ── Aggregate actuator actions ──────────────────────────────────
    actions: list[dict] = []

    # Group by (zone_id, device) — each group is one "decision point"
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in actuator_proposals:
        key = (p.get("zone_id", "global"), p.get("device", "unknown"))
        groups[key].append(p)

    for (zone_id, device), proposals in groups.items():
        # Count action directions
        action_counts: dict[str, list[dict]] = defaultdict(list)
        for p in proposals:
            action_counts[p.get("action", "set")].append(p)

        # Find majority action
        best_action = max(action_counts.keys(), key=lambda a: len(action_counts[a]))
        best_proposals = action_counts[best_action]

        if len(best_proposals) <= quorum_size / 2:
            continue  # No majority → no action (conservative default)

        # Weighted median for continuous values
        values = [p.get("value", 0) for p in best_proposals]
        weights = [p.get("confidence", 0.5) for p in best_proposals]
        final_value = _weighted_median(values, weights)

        # Highest severity (safety-first)
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        severities = [p.get("severity", "info") for p in best_proposals]
        highest_sev = min(severities, key=lambda s: sev_order.get(s, 4))

        # Best reasoning (longest from majority)
        reasonings = [p.get("reasoning", "") for p in best_proposals]
        best_reasoning = max(reasonings, key=len)

        # Agreement ratio
        agreement = len(best_proposals) / quorum_size

        actions.append({
            "zone_id": zone_id,
            "device": device,
            "action": best_action,
            "value": round(final_value, 1),
            "severity": highest_sev,
            "reasoning": best_reasoning,
            "agreement": round(agreement, 2),
        })

    return actions, escalations


# ── Council class ───────────────────────────────────────────────────────


class Council:
    """Consensus quorum of identical omniscient agents."""

    def __init__(
        self,
        model,
        sensor,
        actuator,
        state_store,
        telemetry_store,
        agent_log,
        nutrition: NutritionTracker,
        zone_crops: dict[str, str] | None = None,
        event_bus=None,
        syngenta_kb=None,
        nasa_mcp=None,
        quorum_size: int = 5,
        temperature: float = 0.8,
    ) -> None:
        self._model = model
        self._sensor = sensor
        self._actuator = actuator
        self._state_store = state_store
        self._telemetry_store = telemetry_store
        self._agent_log = agent_log
        self._nutrition = nutrition
        self._zone_crops = zone_crops or {}
        self._event_bus = event_bus
        self._syngenta_kb = syngenta_kb
        self._nasa_mcp = nasa_mcp
        self._quorum_size = quorum_size
        self._temperature = temperature

        # Strands SDK state
        self._strands_available = False
        self._strands_model = None
        self._strands_tools: list = []

        # Closed-loop feedback from reconciler
        self._previous_cycle_feedback: list[dict] = []

        # Hardware failure context (injected by reconciler)
        self._hardware_failures: list[dict] = []

        # Escalation store (in-memory, persisted by sqlite adapter)
        self._escalations: list[CrewEscalation] = []

    # ── Public interface (same shape as AgentTeam) ──────────────────

    def analyze(
        self,
        zones: dict[str, ZoneState],
        mars: MarsConditions,
        deltas: dict[str, dict],
    ) -> list[AgentDecision]:
        """Run council quorum, aggregate votes, return decisions."""
        self._emit("council_start", {
            "quorum_size": self._quorum_size,
            "zones_with_deltas": list(deltas.keys()),
        })

        context = self._build_context(zones, mars, deltas)
        context_str = self._format_context(context)

        # Run quorum
        votes = self._run_quorum(context_str, mars)

        if not votes:
            logger.warning("council_no_votes", fallback="flight_rules_only")
            return []

        # Aggregate
        actions, escalations = aggregate_votes(votes, self._quorum_size)

        # Convert to AgentDecisions
        decisions: list[AgentDecision] = []

        for act in actions:
            decision = AgentDecision(
                timestamp=time.time(),
                agent_name="COUNCIL",
                severity=Severity(act["severity"]),
                reasoning=f"[{act['agreement']:.0%} consensus] {act['reasoning']}",
                action=f"{act['device']}:{act['action']}={act['value']}",
                result="consensus",
                zone_id=act["zone_id"],
                tier=Tier.CLOUD_MODEL,
            )
            decisions.append(decision)
            self._agent_log.append(decision)
            self._emit("council_consensus", decision.to_dict())

        for esc in escalations:
            escalation = CrewEscalation(
                escalation_id=f"esc-{uuid.uuid4().hex[:8]}",
                timestamp=time.time(),
                task=esc["task"],
                urgency=Severity(esc["urgency"]),
                estimated_minutes=esc["estimated_minutes"],
                zone_id=esc["zone_id"],
                category=esc["category"],
            )
            self._escalations.append(escalation)

            decision = AgentDecision(
                timestamp=time.time(),
                agent_name="COUNCIL",
                severity=Severity(esc["urgency"]),
                reasoning=f"CREW ESCALATION: {esc['task']}",
                action=f"REQUEST_CREW: {esc['task']}",
                result="escalated",
                zone_id=esc["zone_id"],
                tier=Tier.CLOUD_MODEL,
            )
            decisions.append(decision)
            self._agent_log.append(decision)
            self._emit("crew_escalation", escalation.to_dict())

        self._emit("council_complete", {
            "actions": len(actions),
            "escalations": len(escalations),
            "votes_received": len(votes),
        })

        return decisions

    def set_feedback(self, feedback: list[dict]) -> None:
        """Inject closed-loop feedback from reconciler."""
        self._previous_cycle_feedback = feedback

    def set_hardware_failures(self, failures: list[dict]) -> None:
        """Inject hardware failure context from reconciler."""
        self._hardware_failures = failures

    def get_escalations(self, status: str | None = None) -> list[CrewEscalation]:
        """Get escalations, optionally filtered by status."""
        if status is None:
            return list(self._escalations)
        return [e for e in self._escalations if e.status == status]

    def update_escalation(self, escalation_id: str, status: str, by: str | None = None) -> bool:
        """Update escalation status (acknowledge, resolve, dismiss)."""
        for esc in self._escalations:
            if esc.escalation_id == escalation_id:
                esc.status = status
                if status == "acknowledged" and by:
                    esc.acknowledged_by = by
                if status in ("resolved", "dismissed"):
                    esc.resolved_at = time.time()
                self._emit(f"escalation_{status}", esc.to_dict())
                return True
        return False

    def enable_strands(self) -> bool:
        """Initialize Strands SDK for tool-calling agents."""
        try:
            from strands.models.bedrock import BedrockModel

            self._strands_model = BedrockModel(
                model_id="global.anthropic.claude-sonnet-4-6",
                max_tokens=8192,
                temperature=self._temperature,
            )

            from eden.application.strands_tools import make_tools
            self._strands_tools = make_tools(
                sensor=self._sensor,
                actuator=self._actuator,
                state_store=self._state_store,
                telemetry_store=self._telemetry_store,
                agent_log=self._agent_log,
                nutrition=self._nutrition,
                syngenta_kb=self._syngenta_kb,
                nasa_mcp=self._nasa_mcp,
                event_bus=self._event_bus,
            )

            # Add MCP tools if available
            if self._syngenta_kb is not None:
                try:
                    mcp_tools = self._syngenta_kb.list_tools()
                    self._strands_tools.extend(mcp_tools)
                except Exception:
                    pass
            if self._nasa_mcp is not None:
                try:
                    mcp_tools = self._nasa_mcp.list_tools()
                    self._strands_tools.extend(mcp_tools)
                except Exception:
                    pass

            self._strands_available = True
            logger.info(
                "strands_sdk_enabled",
                tools=len(self._strands_tools),
                quorum_size=self._quorum_size,
                temperature=self._temperature,
            )
            return True

        except Exception:
            logger.warning("strands_sdk_unavailable", fallback="model_reason")
            self._strands_available = False
            return False

    # ── Quorum execution ────────────────────────────────────────────

    def _run_quorum(self, context: str, mars: MarsConditions) -> list:
        """Run N identical agents in parallel, collect votes."""
        if self._strands_available:
            return self._run_quorum_strands(context, mars)
        return self._run_quorum_fallback(context, mars)

    def _get_persona(self, member_id: int) -> dict:
        """Get persona for a council member (wraps around if quorum > personas)."""
        return COUNCIL_PERSONAS[member_id % len(COUNCIL_PERSONAS)]

    def _run_quorum_strands(self, context: str, mars: MarsConditions) -> list:
        """Run quorum via Strands SDK with tool calling + structured output."""
        from strands import Agent

        votes: list = []
        base_prompt = OMNISCIENT_PROMPT.format(quorum_size=self._quorum_size)
        base_prompt += f"\n\nCurrent Sol: {mars.sol}\nDays remaining: {max(0, 450 - mars.sol)}\n"

        def run_member(member_id: int):
            persona = self._get_persona(member_id)
            name = persona["name"]
            prompt = (
                f"Your name is {name}. {persona['trait']}\n\n"
                f"{base_prompt}"
            )
            self._emit("agent_started", {
                "agent_name": name,
                "member_id": member_id,
                "emoji": persona["emoji"],
                "round": 1,
            })

            # Track tool calls for live streaming
            def _on_tool_use(tool_name, **kwargs):
                self._emit("agent_tool_call", {
                    "agent_name": name,
                    "tool_name": tool_name,
                })

            try:
                callbacks = {}
                try:
                    from strands.types.event_loop import EventLoopEvent
                    # Hook into tool use events if available
                except ImportError:
                    pass

                agent = Agent(
                    model=self._strands_model,
                    tools=self._strands_tools,
                    system_prompt=prompt,
                    name=name,
                    structured_output_model=CouncilVote,
                )

                # Patch callback for tool call streaming
                original_call_tool = None
                if hasattr(agent, '_call_tool'):
                    original_call_tool = agent._call_tool
                    def patched_call_tool(tool, *args, **kwargs):
                        self._emit("agent_tool_call", {
                            "agent_name": name,
                            "tool_name": getattr(tool, 'tool_name', str(tool)),
                        })
                        return original_call_tool(tool, *args, **kwargs)
                    agent._call_tool = patched_call_tool

                result = agent(context)

                # Extract structured output
                structured = getattr(result, "structured_output", None)
                if structured is not None:
                    # Build rich decision summaries for the frontend
                    decision_summaries = []
                    for d in structured.decisions:
                        summary = f"{d.zone_id}: {d.device} {d.action}"
                        if d.action == "escalate_to_crew":
                            summary = f"🚨 {d.zone_id}: {(d.escalation_task or d.reasoning)[:100]}"
                        else:
                            summary = f"{d.zone_id}: {d.device}→{d.action}={d.value} ({d.severity})"
                        decision_summaries.append(summary)

                    self._emit("council_vote", {
                        "member": name,
                        "emoji": persona["emoji"],
                        "decisions": len(structured.decisions),
                        "confidence": structured.confidence,
                        "assessment": structured.overall_assessment,
                        "decision_summaries": decision_summaries,
                    })
                    return structured

                # Fallback: parse from text
                return self._parse_vote_from_text(str(result), name)

            except Exception:
                logger.exception("council_member_failed", member=name)
                self._emit("agent_complete", {
                    "agent_name": name,
                    "full_text": "⚠️ Agent failed — see logs",
                })
                return None

        from eden.application.strands_tools import _current_agent

        def _named_run(member_id: int):
            """Run member with contextvar for tool_use event tagging."""
            persona = self._get_persona(member_id)
            _current_agent.set(persona['name'])
            return run_member(member_id)

        with ThreadPoolExecutor(max_workers=self._quorum_size) as pool:
            futures = {
                pool.submit(_named_run, i): i
                for i in range(self._quorum_size)
            }
            for fut in as_completed(futures):
                result = fut.result()
                if result is not None:
                    votes.append(result)

        min_quorum = self._quorum_size // 2 + 1
        if len(votes) < min_quorum:
            logger.warning(
                "council_insufficient_quorum",
                votes_received=len(votes),
                quorum_size=self._quorum_size,
                min_required=min_quorum,
            )
        return votes

    def _run_quorum_fallback(self, context: str, mars: MarsConditions) -> list:
        """Fallback: run quorum via model.reason() without tool calling."""
        if self._model is None or not self._model.is_available():
            return []

        base_prompt = OMNISCIENT_PROMPT.format(quorum_size=self._quorum_size)
        base_prompt += f"\n\nCurrent Sol: {mars.sol}\nDays remaining: {max(0, 450 - mars.sol)}\n"
        base_prompt += (
            "\n\nRespond with ONLY a JSON object matching the CouncilVote schema:\n"
            '{"decisions": [{"zone_id": "...", "device": "...", "action": "...", '
            '"value": 0, "severity": "...", "reasoning": "...", "confidence": 0.0}], '
            '"overall_assessment": "...", "confidence": 0.0}'
        )

        votes: list = []

        def run_member(member_id: int):
            persona = self._get_persona(member_id)
            name = persona["name"]
            prompt = (
                f"Your name is {name}. {persona['trait']}\n\n"
                f"{base_prompt}"
            )
            self._emit("agent_started", {
                "agent_name": name,
                "member_id": member_id,
                "emoji": persona["emoji"],
                "round": 1,
            })
            try:
                response = self._model.reason(prompt, context)
                if response:
                    return self._parse_vote_from_text(response, name)
            except Exception:
                logger.exception("council_member_fallback_failed", member=name)
            return None

        with ThreadPoolExecutor(max_workers=self._quorum_size) as pool:
            futures = {pool.submit(run_member, i): i for i in range(self._quorum_size)}
            for fut in as_completed(futures):
                result = fut.result()
                if result is not None:
                    votes.append(result)

        return votes

    def _parse_vote_from_text(self, text: str, member_name: str) -> dict | None:
        """Parse a CouncilVote from raw text/JSON response."""
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(text[start:end])
                self._emit("council_vote", {
                    "member": member_name,
                    "decisions": len(parsed.get("decisions", [])),
                    "confidence": parsed.get("confidence", 0.5),
                })
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        logger.warning("council_vote_parse_failed", member=member_name)
        return None

    # ── Context building (extracted from AgentTeam) ─────────────────

    def _build_context(
        self,
        zones: dict[str, ZoneState],
        mars: MarsConditions,
        deltas: dict[str, dict],
    ) -> dict:
        """Build full shared context — everything the system knows."""
        mars_dict = mars.to_dict() if hasattr(mars, "to_dict") else mars
        mcp_data = self._fetch_mcp_data(zones)

        ctx = {
            "zones": {zid: z.to_dict() for zid, z in zones.items()},
            "deltas": deltas,
            "mars_conditions": mars_dict,
            "nutritional_status": self._nutrition.get_nutritional_status(),
            "deficiency_risks": self._nutrition.get_deficiency_risks(days_ahead=30),
            "mission_projection": self._nutrition.get_mission_projection(),
            "desired_states": {
                zid: ds.to_dict()
                for zid, ds in self._get_all_desired_states(zones).items()
            },
            "recent_decisions": [
                d.to_dict()
                for d in self._agent_log.query(since=time.time() - 3600, limit=50)
            ],
            "telemetry_trends": self._get_telemetry_trends(zones),
            "zone_crops": self._zone_crops,
            "current_sol": mars.sol,
            "days_remaining": max(0, 450 - mars.sol),
            "previous_cycle_feedback": self._previous_cycle_feedback,
            "mcp_data": mcp_data,
        }

        # Inject hardware failure context if detected
        if self._hardware_failures:
            ctx["hardware_failures"] = self._hardware_failures

        return ctx

    def _format_context(self, context: dict) -> str:
        """Format context dict as a prompt string for the council."""
        parts: list[str] = []

        parts.append("=== CURRENT GREENHOUSE STATE ===")
        for zid, zone in context.get("zones", {}).items():
            crop = self._zone_crops.get(zid, "unknown")
            parts.append(
                f"\nZone {zid} ({crop}): "
                f"temp={zone['temperature']:.1f}°C, humidity={zone['humidity']:.1f}%, "
                f"light={zone['light']:.0f} lux, water={zone['water_level']:.1f}mm, "
                f"pressure={zone['pressure']:.0f} hPa"
            )

        if context.get("deltas"):
            parts.append("\n=== DELTAS (deviations from desired state) ===")
            for zid, delta in context["deltas"].items():
                parts.append(f"Zone {zid}: {json.dumps(delta, default=str)}")

        mars = context.get("mars_conditions", {})
        parts.append(
            f"\n=== MARS CONDITIONS ===\n"
            f"Sol: {mars.get('sol', '?')}, "
            f"Exterior: {mars.get('exterior_temp', '?')}°C, "
            f"Dust opacity: {mars.get('dust_opacity', '?')}, "
            f"Solar: {mars.get('solar_irradiance', '?')} W/m², "
            f"Storm: {mars.get('storm_active', False)}, "
            f"Radiation alert: {mars.get('radiation_alert', False)}"
        )

        if context.get("hardware_failures"):
            parts.append("\n=== HARDWARE FAILURES DETECTED ===")
            for hf in context["hardware_failures"]:
                parts.append(
                    f"Zone {hf['zone_id']}: {hf['device']} command '{hf['action']}' "
                    f"sent but sensor did not respond after {hf.get('cycles', 1)} cycle(s). "
                    f"Likely physical hardware failure."
                )

        nutrition = context.get("nutritional_status", {})
        if nutrition:
            parts.append(f"\n=== CREW NUTRITION ===\n{json.dumps(nutrition, default=str, indent=1)}")

        if context.get("previous_cycle_feedback"):
            parts.append("\n=== FEEDBACK FROM LAST CYCLE ===")
            for fb in context["previous_cycle_feedback"]:
                parts.append(json.dumps(fb, default=str))

        mcp = context.get("mcp_data", {})
        if mcp:
            parts.append("\n=== KNOWLEDGE BASE DATA (Syngenta + NASA) ===")
            for key, val in mcp.items():
                parts.append(f"{key}: {json.dumps(val, default=str)[:500]}")

        return "\n".join(parts)

    def _fetch_mcp_data(self, zones: dict[str, ZoneState]) -> dict:
        """Pre-fetch MCP data (Syngenta KB + NASA). Cached by adapters."""
        mcp: dict = {}
        if self._syngenta_kb is not None:
            try:
                crop_data: dict = {}
                for zid in self._zone_crops:
                    crop_name = self._zone_crops.get(zid, "")
                    if crop_name:
                        crop_data[zid] = self._syngenta_kb.check_crop_profile(crop_name)
                mcp["syngenta_crop_data"] = crop_data
                mcp["syngenta_scenarios"] = self._syngenta_kb.check_greenhouse_scenarios(
                    "Mars greenhouse environment management autonomous system"
                )
            except Exception:
                logger.warning("syngenta_kb_fetch_failed", exc_info=True)

        if self._nasa_mcp is not None:
            try:
                mcp["nasa_mars_weather"] = self._nasa_mcp.get_mars_weather()
                mcp["nasa_solar_events"] = self._nasa_mcp.get_solar_events()
            except Exception:
                logger.warning("nasa_mcp_fetch_failed", exc_info=True)

        return mcp

    def _get_all_desired_states(self, zones: dict[str, ZoneState]) -> dict[str, DesiredState]:
        """Query desired states for all zones."""
        result: dict[str, DesiredState] = {}
        for zid in zones:
            ds = self._state_store.get_desired_state(zid)
            if ds is not None:
                result[zid] = ds
        return result

    def _get_telemetry_trends(self, zones: dict[str, ZoneState]) -> dict:
        """Query last hour of readings per zone, compute min/max/avg."""
        trends: dict = {}
        since = time.time() - 3600
        for zid in zones:
            readings = self._telemetry_store.query(zid, since, limit=200)
            if not readings:
                trends[zid] = {}
                continue
            by_type: dict[str, list[float]] = {}
            for r in readings:
                st = r.sensor_type.value if hasattr(r.sensor_type, "value") else str(r.sensor_type)
                by_type.setdefault(st, []).append(r.value)
            zone_trends: dict = {}
            for st, values in by_type.items():
                zone_trends[st] = {
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "avg": round(sum(values) / len(values), 2),
                    "count": len(values),
                }
            trends[zid] = zone_trends
        return trends

    # ── EventBus helper ─────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict) -> None:
        """Publish event to EventBus if available."""
        if self._event_bus is not None:
            self._event_bus.publish(event_type, {
                **data,
                "timestamp": time.time(),
            })
