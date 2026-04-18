"""Tests for EDEN multi-agent parliament system — 12 specialists + coordinator."""

from __future__ import annotations

import time

import pytest

from eden.domain.models import (
    AgentDecision,
    CropProfile,
    CrewMember,
    DesiredState,
    MarsConditions,
    SensorReading,
    SensorType,
    Severity,
    Tier,
    ZoneState,
)
from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.nutrition import NutritionTracker


# ── Fixtures ────────────────────────────────────────────────────────────


def _make_zone(zone_id: str = "alpha", **overrides) -> ZoneState:
    defaults = dict(
        zone_id=zone_id,
        temperature=22.0,
        humidity=55.0,
        pressure=700.0,
        light=500.0,
        water_level=80.0,
        fire_detected=False,
        last_updated=time.time(),
        is_alive=True,
        source="test",
    )
    defaults.update(overrides)
    return ZoneState(**defaults)


def _make_mars() -> MarsConditions:
    return MarsConditions(
        exterior_temp=-60.0,
        dome_temp=20.0,
        pressure_hpa=636.0,
        solar_irradiance=590.0,
        dust_opacity=0.3,
        sol=42,
        storm_active=False,
        radiation_alert=False,
    )


def _make_nutrition() -> NutritionTracker:
    crew = NutritionTracker.get_default_crew()
    crops = [
        CropProfile("Tomato", "alpha", 180.0, 9.0, 80, 3.5, 18.0, 27.0, 50.0, 80.0),
        CropProfile("Lettuce", "beta", 150.0, 13.0, 45, 2.0, 15.0, 22.0, 40.0, 70.0),
    ]
    return NutritionTracker(crew, crops)


# ── Mock implementations ────────────────────────────────────────────────


class MockModel:
    """Predictable model for testing agent responses."""

    def __init__(self, responses: dict[str, str] | None = None, available: bool = True):
        self.responses = responses or {}
        self._available = available
        self.calls: list[tuple[str, dict]] = []

    def reason(self, prompt: str, context: dict) -> str | None:
        self.calls.append((prompt, context))
        for key, resp in self.responses.items():
            if key.lower() in prompt.lower():
                return resp
        return ""

    def is_available(self) -> bool:
        return self._available


class MockSensor:
    def __init__(self, zones: dict[str, ZoneState] | None = None):
        self._zones = zones or {}

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def get_latest(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def subscribe(self, callback) -> None:
        pass


class MockActuator:
    def __init__(self):
        self.commands: list = []

    def send_command(self, command) -> bool:
        self.commands.append(command)
        return True


class MockStateStore:
    def __init__(self):
        self._zone_states: dict = {}
        self._desired_states: dict = {}

    def get_zone_state(self, zone_id: str) -> ZoneState | None:
        return self._zone_states.get(zone_id)

    def put_zone_state(self, zone_id: str, state: ZoneState) -> None:
        self._zone_states[zone_id] = state

    def get_desired_state(self, zone_id: str) -> DesiredState | None:
        return self._desired_states.get(zone_id)

    def put_desired_state(self, zone_id: str, state: DesiredState) -> None:
        self._desired_states[zone_id] = state


class MockTelemetryStore:
    def __init__(self):
        self.entries: list = []

    def append(self, reading: SensorReading) -> None:
        self.entries.append(reading)

    def query(self, zone_id: str, since: float, limit: int) -> list[SensorReading]:
        return [e for e in self.entries if e.zone_id == zone_id and e.timestamp >= since][:limit]


class MockAgentLog:
    def __init__(self):
        self.decisions: list[AgentDecision] = []

    def append(self, decision: AgentDecision) -> None:
        self.decisions.append(decision)

    def query(self, since: float, limit: int) -> list[AgentDecision]:
        return [d for d in self.decisions if d.timestamp >= since][:limit]


def _all_agent_responses() -> dict[str, str]:
    """MockModel responses that match every specialist name + coordinator."""
    return {
        # COORDINATOR resolution — keyed on unique prompt text, must be first
        # so it matches before individual agent names in the coordinator prompt
        "CONSENSUS RESOLUTION": '{"resolution": "[COORDINATOR] CONSENSUS RESOLUTION — Sol 42:\\n1. IMMEDIATE: All zones nominal — no action required (all agents agree)\\n\\nPriority: No immediate actions. All items logged for crew briefing.", "immediate_count": 0, "highest_severity": "info"}',
        "DEMETER": "crop rotation on track",
        "FLORA": "I am the tomato. I feel good.",
        "TERRA": "soil pH balanced",
        "AQUA": "water budget ok",
        "HELIOS": "solar nominal",
        "ATMOS": "atmosphere stable",
        "VITA": "nutrition on track",
        "HESTIA": "crew morale high",
        "SENTINEL": "no threats",
        "ORACLE": "projections nominal",
        "CHRONOS": "mission on schedule",
        "PATHFINDER": "no pathogens detected",
    }


# ── Test: AgentTeam construction and basic analyze ──────────────────────


class TestAgentTeam:
    def _make_team(self, model=None, **kwargs):
        from eden.application.agent import AgentTeam

        return AgentTeam(
            model=model or MockModel(_all_agent_responses()),
            sensor=kwargs.get("sensor", MockSensor()),
            actuator=kwargs.get("actuator", MockActuator()),
            state_store=kwargs.get("state_store", MockStateStore()),
            telemetry_store=kwargs.get("telemetry_store", MockTelemetryStore()),
            agent_log=kwargs.get("agent_log", MockAgentLog()),
            nutrition=kwargs.get("nutrition", _make_nutrition()),
        )

    def test_analyze_returns_decisions(self):
        """Normal zones with deltas produce AgentDecision list."""
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        decisions = team.analyze(zones, mars, deltas)

        assert isinstance(decisions, list)
        for d in decisions:
            assert isinstance(d, AgentDecision)

    def test_analyze_model_unavailable_returns_empty(self):
        """When model is unavailable, analyze returns empty list."""
        model = MockModel(available=False)
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        decisions = team.analyze(zones, mars, deltas)

        assert decisions == []

    def test_analyze_empty_deltas_still_runs(self):
        """Even with no deltas, agents should still analyze."""
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        decisions = team.analyze(zones, mars, deltas)
        assert isinstance(decisions, list)

    def test_decisions_tagged_with_valid_agent_names(self):
        """Each decision must be tagged with a known agent name."""
        from eden.application.agent import ALL_AGENT_NAMES

        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        decisions = team.analyze(zones, mars, deltas)

        assert len(decisions) > 0
        valid_names = ALL_AGENT_NAMES | {"COORDINATOR"}
        for d in decisions:
            # FLORA-{zone} names are dynamic — validated via prefix
            assert d.agent_name in valid_names or d.agent_name.startswith("FLORA-"), (
                f"Unknown agent: {d.agent_name}"
            )

    def test_all_twelve_specialists_called(self):
        """Model called once per non-FLORA specialist + once per FLORA zone + deliberation."""
        from eden.application.agent import _SPECIALISTS

        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        team.analyze(zones, mars, deltas)

        # 11 fixed specialists + 1 FLORA per zone (1 zone here)
        # + deliberation agents (3-4 additional calls)
        non_flora = [s for s in _SPECIALISTS if s != "FLORA"]
        round1_expected = len(non_flora) + len(zones)
        assert len(model.calls) >= round1_expected

    def test_decisions_logged_to_agent_log(self):
        """All decisions should be appended to the agent log."""
        agent_log = MockAgentLog()
        team = self._make_team(agent_log=agent_log)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        decisions = team.analyze(zones, mars, deltas)

        assert len(agent_log.decisions) == len(decisions)

    def test_flora_runs_per_zone(self):
        """FLORA should run once per zone, producing zone-specific decisions."""
        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {
            "alpha": _make_zone("alpha"),
            "beta": _make_zone("beta"),
            "gamma": _make_zone("gamma"),
        }
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        decisions = team.analyze(zones, mars, deltas)

        # Check FLORA decisions exist (named FLORA-{zone_id})
        flora_decisions = [d for d in decisions if d.agent_name.startswith("FLORA")]
        assert len(flora_decisions) >= 3  # one per zone

    def test_flora_prompt_contains_zone_id(self):
        """FLORA prompts should include the specific zone_id."""
        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        team.analyze(zones, mars, deltas)

        # Find FLORA calls in model
        flora_calls = [
            (prompt, ctx) for prompt, ctx in model.calls
            if "[FLORA" in prompt
        ]
        assert len(flora_calls) >= 1
        # The prompt should mention the zone
        assert "alpha" in flora_calls[0][0].lower()

    def test_multiple_zones_multiple_flora(self):
        """Each zone spawns its own FLORA agent with zone-specific context."""
        from eden.application.agent import _SPECIALISTS

        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {
            "alpha": _make_zone("alpha"),
            "beta": _make_zone("beta"),
        }
        mars = _make_mars()
        deltas = {}

        team.analyze(zones, mars, deltas)

        non_flora = [s for s in _SPECIALISTS if s != "FLORA"]
        round1_expected = len(non_flora) + 2  # 2 FLORA instances
        # + deliberation agents (3-4 additional calls)
        assert len(model.calls) >= round1_expected


# ── Test: Deliberation round ─────────────────────────────────────────────


class TestDeliberation:
    def _make_team(self, model=None, **kwargs):
        from eden.application.agent import AgentTeam

        return AgentTeam(
            model=model or MockModel(_all_agent_responses()),
            sensor=kwargs.get("sensor", MockSensor()),
            actuator=kwargs.get("actuator", MockActuator()),
            state_store=kwargs.get("state_store", MockStateStore()),
            telemetry_store=kwargs.get("telemetry_store", MockTelemetryStore()),
            agent_log=kwargs.get("agent_log", MockAgentLog()),
            nutrition=kwargs.get("nutrition", _make_nutrition()),
        )

    def test_deliberation_runs_after_round1(self):
        """Deliberation adds extra model calls beyond the Round 1 specialists."""
        from eden.application.agent import _SPECIALISTS

        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        team.analyze(zones, mars, deltas)

        non_flora = [s for s in _SPECIALISTS if s != "FLORA"]
        round1_count = len(non_flora) + len(zones)
        # Deliberation should add at least 1 extra call
        assert len(model.calls) > round1_count

    def test_deliberation_prompts_contain_round1_proposals(self):
        """Deliberation prompts must include 'Round 1 Proposals' and 'DELIBERATION'."""
        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        team.analyze(zones, mars, deltas)

        # Filter for actual agent deliberation prompts (e.g. "[SENTINEL DELIBERATION]")
        # — not the COORDINATOR prompt which also mentions "DELIBERATION" in its transcript
        delib_calls = [
            (prompt, ctx) for prompt, ctx in model.calls
            if " DELIBERATION]" in prompt
        ]
        assert len(delib_calls) >= 1
        # Each deliberation prompt should contain the Round 1 summary
        for prompt, _ in delib_calls:
            assert "Round 1 Proposals:" in prompt

    def test_deliberation_prompts_ask_agents_to_reference_by_name(self):
        """Deliberation prompt should instruct agents to reference each other BY NAME."""
        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        team.analyze(zones, mars, deltas)

        # Filter for actual agent deliberation prompts (not the COORDINATOR prompt)
        delib_calls = [
            prompt for prompt, _ in model.calls
            if " DELIBERATION]" in prompt
        ]
        for prompt in delib_calls:
            assert "BY NAME" in prompt

    def test_deliberation_decisions_tagged_response_or_disagree(self):
        """Deliberation decisions should have [RESPONSE] or [DISAGREE] in action."""
        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        decisions = team.analyze(zones, mars, deltas)

        delib_decisions = [
            d for d in decisions
            if "[RESPONSE]" in d.action or "[DISAGREE]" in d.action
        ]
        # At least some deliberation decisions should exist
        assert len(delib_decisions) >= 1

    def test_deliberation_skipped_when_model_unavailable(self):
        """If model becomes unavailable, deliberation is skipped gracefully."""
        model = MockModel(available=False)
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        decisions = team.analyze(zones, mars, deltas)

        # Model unavailable → no Round 1, no deliberation
        assert decisions == []

    def test_deliberation_skipped_when_no_proposals(self):
        """If Round 1 produces no proposals, deliberation is skipped."""
        # Model returns empty for everything → no proposals
        model = MockModel(responses={}, available=True)
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        decisions = team.analyze(zones, mars, deltas)

        # No round 1 proposals means no deliberation calls beyond round 1
        assert len(model.calls) > 0  # Round 1 still ran
        # All calls should be round 1 (no DELIBERATION in prompts)
        delib_calls = [p for p, _ in model.calls if "DELIBERATION" in p]
        assert len(delib_calls) == 0

    def test_deliberation_max_4_agents(self):
        """Deliberation should run at most 4 agents."""
        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {
            "alpha": _make_zone("alpha"),
            "beta": _make_zone("beta"),
            "gamma": _make_zone("gamma"),
        }
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        team.analyze(zones, mars, deltas)

        delib_calls = [p for p, _ in model.calls if "DELIBERATION" in p]
        assert len(delib_calls) <= 4

    def test_build_deliberation_context_format(self):
        """_build_deliberation_context produces readable summary with agent names."""
        team = self._make_team()
        proposals = [
            AgentDecision(
                timestamp=time.time(),
                agent_name="CHRONOS",
                severity=Severity.HIGH,
                reasoning="Rotate gamma basil to soybeans for protein",
                action="rotate_crop",
                result="proposed",
                zone_id="gamma",
                tier=Tier.CLOUD_MODEL,
            ),
            AgentDecision(
                timestamp=time.time(),
                agent_name="FLORA",
                severity=Severity.MEDIUM,
                reasoning="I need humidity support, trending down",
                action="request_humidity",
                result="proposed",
                zone_id="gamma",
                tier=Tier.CLOUD_MODEL,
            ),
        ]

        context = team._build_deliberation_context(proposals)

        assert "Round 1 Proposals:" in context
        assert "[CHRONOS]" in context
        assert "[FLORA]" in context
        assert "gamma" in context


# ── Test: COORDINATOR consensus resolution ───────────────────────────────


class TestCoordinatorResolution:
    def _make_team(self, model=None, **kwargs):
        from eden.application.agent import AgentTeam

        return AgentTeam(
            model=model or MockModel(_all_agent_responses()),
            sensor=kwargs.get("sensor", MockSensor()),
            actuator=kwargs.get("actuator", MockActuator()),
            state_store=kwargs.get("state_store", MockStateStore()),
            telemetry_store=kwargs.get("telemetry_store", MockTelemetryStore()),
            agent_log=kwargs.get("agent_log", MockAgentLog()),
            nutrition=kwargs.get("nutrition", _make_nutrition()),
        )

    def test_coordinator_resolution_is_first_decision(self):
        """The COORDINATOR consensus resolution should be the first item returned."""
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        decisions = team.analyze(zones, mars, deltas)

        assert len(decisions) > 1
        assert decisions[0].agent_name == "COORDINATOR"
        assert decisions[0].action == "CONSENSUS_RESOLUTION"

    def test_coordinator_resolution_contains_consensus_text(self):
        """The resolution reasoning should contain the synthesized consensus."""
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        decisions = team.analyze(zones, mars, deltas)

        resolution = decisions[0]
        assert "CONSENSUS RESOLUTION" in resolution.reasoning

    def test_coordinator_result_is_resolved(self):
        """Coordinator decisions should have result='resolved'."""
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        decisions = team.analyze(zones, mars, deltas)

        resolution = decisions[0]
        assert resolution.result == "resolved"

    def test_coordinator_prompt_contains_debate_transcript(self):
        """COORDINATOR prompt should include both Round 1 and Round 2 debate."""
        model = MockModel(_all_agent_responses())
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        team.analyze(zones, mars, deltas)

        coordinator_calls = [
            prompt for prompt, _ in model.calls
            if "CONSENSUS RESOLUTION" in prompt and "ROUND 1 PROPOSALS" in prompt
        ]
        assert len(coordinator_calls) == 1
        assert "=== ROUND 1 PROPOSALS ===" in coordinator_calls[0]

    def test_coordinator_logged_to_agent_log(self):
        """COORDINATOR resolution should appear in the agent log."""
        agent_log = MockAgentLog()
        team = self._make_team(agent_log=agent_log)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        team.analyze(zones, mars, deltas)

        coordinator_entries = [
            d for d in agent_log.decisions
            if d.agent_name == "COORDINATOR"
        ]
        assert len(coordinator_entries) == 1
        assert coordinator_entries[0].action == "CONSENSUS_RESOLUTION"

    def test_coordinator_parses_json_resolution(self):
        """COORDINATOR should parse JSON response with resolution text and severity."""
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        decisions = team.analyze(zones, mars, deltas)

        resolution = decisions[0]
        # The mock returns a JSON object with resolution text
        assert "Sol 42" in resolution.reasoning

    def test_individual_decisions_follow_resolution(self):
        """After the resolution, individual specialist decisions should follow."""
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        decisions = team.analyze(zones, mars, deltas)

        # First is COORDINATOR, rest are individual specialists
        assert decisions[0].agent_name == "COORDINATOR"
        specialist_decisions = decisions[1:]
        assert len(specialist_decisions) > 0
        for d in specialist_decisions:
            assert d.agent_name != "COORDINATOR"

    def test_coordinator_skipped_when_no_proposals(self):
        """If no proposals exist, coordinator should not run."""
        model = MockModel(responses={}, available=True)
        team = self._make_team(model=model)
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        decisions = team.analyze(zones, mars, deltas)

        coordinator_decisions = [d for d in decisions if d.agent_name == "COORDINATOR"]
        assert len(coordinator_decisions) == 0


# ── Test: Context building ──────────────────────────────────────────────


class TestContextBuilding:
    def _make_team(self):
        from eden.application.agent import AgentTeam

        return AgentTeam(
            model=MockModel(),
            sensor=MockSensor(),
            actuator=MockActuator(),
            state_store=MockStateStore(),
            telemetry_store=MockTelemetryStore(),
            agent_log=MockAgentLog(),
            nutrition=_make_nutrition(),
        )

    def test_context_contains_zones(self):
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        ctx = team._build_context(zones, mars, deltas)

        assert "zones" in ctx
        assert "alpha" in ctx["zones"]

    def test_context_contains_mars_conditions(self):
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "mars_conditions" in ctx
        assert ctx["mars_conditions"]["sol"] == 42

    def test_context_contains_deltas(self):
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {"alpha": {"temperature": 3.0}}

        ctx = team._build_context(zones, mars, deltas)

        assert "deltas" in ctx
        assert ctx["deltas"] == deltas

    def test_context_contains_nutritional_status(self):
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "nutritional_status" in ctx
        assert "crew" in ctx["nutritional_status"]

    def test_context_contains_deficiency_risks(self):
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "deficiency_risks" in ctx
        assert isinstance(ctx["deficiency_risks"], list)

    def test_context_contains_mission_projection(self):
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "mission_projection" in ctx
        assert "mission_days" in ctx["mission_projection"]
        assert "current_sol" in ctx["mission_projection"]

    def test_context_contains_desired_states(self):
        from eden.domain.models import DesiredState

        store = MockStateStore()
        ds = DesiredState("alpha", 18.0, 26.0, 40.0, 70.0, 16.0, 30.0, 60.0, 5.0)
        store.put_desired_state("alpha", ds)

        from eden.application.agent import AgentTeam
        team = AgentTeam(
            model=MockModel(),
            sensor=MockSensor(),
            actuator=MockActuator(),
            state_store=store,
            telemetry_store=MockTelemetryStore(),
            agent_log=MockAgentLog(),
            nutrition=_make_nutrition(),
        )
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "desired_states" in ctx
        assert "alpha" in ctx["desired_states"]
        assert ctx["desired_states"]["alpha"]["temp_min"] == 18.0

    def test_context_contains_resource_budgets(self):
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "resource_budgets" in ctx
        assert isinstance(ctx["resource_budgets"], dict)

    def test_context_contains_recent_decisions(self):
        agent_log = MockAgentLog()
        agent_log.append(AgentDecision(
            timestamp=time.time(),
            agent_name="SENTINEL",
            severity=Severity.HIGH,
            reasoning="test",
            action="test",
            result="proposed",
            zone_id="alpha",
            tier=Tier.CLOUD_MODEL,
        ))

        from eden.application.agent import AgentTeam
        team = AgentTeam(
            model=MockModel(),
            sensor=MockSensor(),
            actuator=MockActuator(),
            state_store=MockStateStore(),
            telemetry_store=MockTelemetryStore(),
            agent_log=agent_log,
            nutrition=_make_nutrition(),
        )
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "recent_decisions" in ctx
        assert len(ctx["recent_decisions"]) == 1
        assert ctx["recent_decisions"][0]["agent_name"] == "SENTINEL"

    def test_context_contains_telemetry_trends(self):
        store = MockTelemetryStore()
        store.append(SensorReading("alpha", SensorType.TEMPERATURE, 22.0, "celsius", time.time(), "test"))
        store.append(SensorReading("alpha", SensorType.TEMPERATURE, 24.0, "celsius", time.time(), "test"))

        from eden.application.agent import AgentTeam
        team = AgentTeam(
            model=MockModel(),
            sensor=MockSensor(),
            actuator=MockActuator(),
            state_store=MockStateStore(),
            telemetry_store=store,
            agent_log=MockAgentLog(),
            nutrition=_make_nutrition(),
        )
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "telemetry_trends" in ctx
        assert "alpha" in ctx["telemetry_trends"]
        assert "temperature" in ctx["telemetry_trends"]["alpha"]
        assert ctx["telemetry_trends"]["alpha"]["temperature"]["min"] == 22.0
        assert ctx["telemetry_trends"]["alpha"]["temperature"]["max"] == 24.0
        assert ctx["telemetry_trends"]["alpha"]["temperature"]["avg"] == 23.0

    def test_context_contains_zone_crops(self):
        from eden.application.agent import AgentTeam
        team = AgentTeam(
            model=MockModel(),
            sensor=MockSensor(),
            actuator=MockActuator(),
            state_store=MockStateStore(),
            telemetry_store=MockTelemetryStore(),
            agent_log=MockAgentLog(),
            nutrition=_make_nutrition(),
            zone_crops={"alpha": "Tomato", "beta": "Lettuce"},
        )
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert "zone_crops" in ctx
        assert ctx["zone_crops"]["alpha"] == "Tomato"

    def test_context_contains_mission_timeline(self):
        team = self._make_team()
        zones = {"alpha": _make_zone("alpha")}
        mars = _make_mars()  # sol=42
        deltas = {}

        ctx = team._build_context(zones, mars, deltas)

        assert ctx["current_sol"] == 42
        assert ctx["mission_day"] == 42
        assert ctx["days_remaining"] == 408  # 450 - 42


# ── Test: Conflict resolution (12-agent priority) ──────────────────────


class TestConflictResolution:
    def _make_team(self):
        from eden.application.agent import AgentTeam

        return AgentTeam(
            model=MockModel(),
            sensor=MockSensor(),
            actuator=MockActuator(),
            state_store=MockStateStore(),
            telemetry_store=MockTelemetryStore(),
            agent_log=MockAgentLog(),
            nutrition=_make_nutrition(),
        )

    def _make_decision(self, agent_name: str, severity: Severity, action: str, zone_id: str = "alpha") -> AgentDecision:
        return AgentDecision(
            timestamp=time.time(),
            agent_name=agent_name,
            severity=severity,
            reasoning=f"{agent_name} reasoning",
            action=action,
            result="proposed",
            zone_id=zone_id,
            tier=Tier.CLOUD_MODEL,
        )

    def test_safety_overrides_everything(self):
        """SENTINEL critical alerts should override all other proposals."""
        team = self._make_team()
        proposals = [
            self._make_decision("DEMETER", Severity.MEDIUM, "irrigate +2L"),
            self._make_decision("SENTINEL", Severity.CRITICAL, "emergency_shutdown"),
            self._make_decision("AQUA", Severity.LOW, "conserve water"),
        ]

        resolved = team._resolve_conflicts(proposals)

        assert resolved[0].agent_name == "SENTINEL"
        assert resolved[0].severity == Severity.CRITICAL

    def test_crop_survival_over_optimization(self):
        """DEMETER critical > AQUA optimization."""
        team = self._make_team()
        proposals = [
            self._make_decision("AQUA", Severity.LOW, "reduce water 20%"),
            self._make_decision("DEMETER", Severity.HIGH, "irrigate now - wilting"),
        ]

        resolved = team._resolve_conflicts(proposals)

        demeter_idx = next(i for i, d in enumerate(resolved) if d.agent_name == "DEMETER")
        aqua_idx = next(i for i, d in enumerate(resolved) if d.agent_name == "AQUA")
        assert demeter_idx < aqua_idx

    def test_resources_over_nutrition_optimization(self):
        """AQUA water systems > VITA nutrition at same severity (can't eat without water)."""
        team = self._make_team()
        proposals = [
            self._make_decision("VITA", Severity.MEDIUM, "maintain crop for vitamin C"),
            self._make_decision("AQUA", Severity.MEDIUM, "reduce water allocation"),
        ]

        resolved = team._resolve_conflicts(proposals)

        aqua_idx = next(i for i, d in enumerate(resolved) if d.agent_name == "AQUA")
        vita_idx = next(i for i, d in enumerate(resolved) if d.agent_name == "VITA")
        assert aqua_idx < vita_idx

    def test_full_12_agent_priority_order(self):
        """Full 12-agent priority at same severity:
        SENTINEL > FLORA > PATHFINDER > TERRA > DEMETER > ATMOS > AQUA > HELIOS > VITA > CHRONOS > HESTIA > ORACLE
        """
        team = self._make_team()
        proposals = [
            self._make_decision("ORACLE", Severity.MEDIUM, "forecast"),
            self._make_decision("HESTIA", Severity.MEDIUM, "morale"),
            self._make_decision("CHRONOS", Severity.MEDIUM, "timeline"),
            self._make_decision("VITA", Severity.MEDIUM, "nutrition"),
            self._make_decision("HELIOS", Severity.MEDIUM, "power"),
            self._make_decision("AQUA", Severity.MEDIUM, "water"),
            self._make_decision("ATMOS", Severity.MEDIUM, "atmosphere"),
            self._make_decision("DEMETER", Severity.MEDIUM, "crops"),
            self._make_decision("TERRA", Severity.MEDIUM, "soil"),
            self._make_decision("PATHFINDER", Severity.MEDIUM, "pathogens"),
            self._make_decision("FLORA", Severity.MEDIUM, "plant voice"),
            self._make_decision("SENTINEL", Severity.MEDIUM, "safety"),
        ]

        resolved = team._resolve_conflicts(proposals)
        names = [d.agent_name for d in resolved]

        # SENTINEL first, ORACLE last
        assert names[0] == "SENTINEL"
        assert names[-1] == "ORACLE"
        # Verify ordering clusters
        assert names.index("SENTINEL") < names.index("FLORA")
        assert names.index("FLORA") < names.index("DEMETER")
        assert names.index("DEMETER") < names.index("VITA")
        assert names.index("VITA") < names.index("ORACLE")

    def test_severity_trumps_agent_priority(self):
        """Higher severity always wins regardless of agent priority."""
        team = self._make_team()
        proposals = [
            self._make_decision("ORACLE", Severity.CRITICAL, "imminent storm"),
            self._make_decision("SENTINEL", Severity.LOW, "routine check"),
        ]

        resolved = team._resolve_conflicts(proposals)

        assert resolved[0].agent_name == "ORACLE"
        assert resolved[0].severity == Severity.CRITICAL

    def test_flora_and_pathfinder_before_demeter(self):
        """Plant health (FLORA/PATHFINDER) > crop yield (DEMETER) at same severity."""
        team = self._make_team()
        proposals = [
            self._make_decision("DEMETER", Severity.MEDIUM, "optimize yield"),
            self._make_decision("FLORA", Severity.MEDIUM, "I'm wilting"),
            self._make_decision("PATHFINDER", Severity.MEDIUM, "fungal risk"),
        ]

        resolved = team._resolve_conflicts(proposals)
        names = [d.agent_name for d in resolved]

        assert names.index("FLORA") < names.index("DEMETER")
        assert names.index("PATHFINDER") < names.index("DEMETER")

    def test_hestia_morale_before_oracle_predictions(self):
        """Crew morale (HESTIA) > predictions (ORACLE) at same severity."""
        team = self._make_team()
        proposals = [
            self._make_decision("ORACLE", Severity.MEDIUM, "30-day forecast"),
            self._make_decision("HESTIA", Severity.MEDIUM, "birthday harvest"),
        ]

        resolved = team._resolve_conflicts(proposals)

        assert resolved[0].agent_name == "HESTIA"


# ── Test: All 12 system prompts ─────────────────────────────────────────


class TestSystemPrompts:
    def test_demeter_prompt_has_crop_keywords(self):
        from eden.application.agent import DEMETER_PROMPT

        prompt = DEMETER_PROMPT.lower()
        assert "crop" in prompt or "plant" in prompt
        assert "rotation" in prompt or "yield" in prompt or "growth" in prompt

    def test_flora_prompt_has_plant_persona_keywords(self):
        from eden.application.agent import FLORA_PROMPT

        prompt = FLORA_PROMPT.lower()
        assert "speak" in prompt or "voice" in prompt or "i am" in prompt or "persona" in prompt
        assert "zone" in prompt

    def test_terra_prompt_has_soil_keywords(self):
        from eden.application.agent import TERRA_PROMPT

        prompt = TERRA_PROMPT.lower()
        assert "soil" in prompt or "substrate" in prompt
        assert "nutrient" in prompt or "ph" in prompt or "microbiome" in prompt

    def test_aqua_prompt_has_water_keywords(self):
        from eden.application.agent import AQUA_PROMPT

        prompt = AQUA_PROMPT.lower()
        assert "water" in prompt or "resource" in prompt
        assert "recycl" in prompt or "conservation" in prompt or "budget" in prompt

    def test_helios_prompt_has_energy_keywords(self):
        from eden.application.agent import HELIOS_PROMPT

        prompt = HELIOS_PROMPT.lower()
        assert "solar" in prompt or "energy" in prompt or "power" in prompt
        assert "light" in prompt or "battery" in prompt or "spectrum" in prompt

    def test_atmos_prompt_has_atmosphere_keywords(self):
        from eden.application.agent import ATMOS_PROMPT

        prompt = ATMOS_PROMPT.lower()
        assert "temperature" in prompt or "atmosphere" in prompt
        assert "humidity" in prompt or "co2" in prompt or "o2" in prompt

    def test_vita_prompt_has_nutrition_keywords(self):
        from eden.application.agent import VITA_PROMPT

        prompt = VITA_PROMPT.lower()
        assert "nutrition" in prompt or "crew" in prompt
        assert "calori" in prompt or "protein" in prompt

    def test_hestia_prompt_has_morale_keywords(self):
        from eden.application.agent import HESTIA_PROMPT

        prompt = HESTIA_PROMPT.lower()
        assert "morale" in prompt or "psychological" in prompt or "comfort" in prompt
        assert "crew" in prompt or "meal" in prompt or "culture" in prompt

    def test_sentinel_prompt_has_safety_keywords(self):
        from eden.application.agent import SENTINEL_PROMPT

        prompt = SENTINEL_PROMPT.lower()
        assert "threat" in prompt or "safety" in prompt
        assert "storm" in prompt or "alert" in prompt

    def test_oracle_prompt_has_prediction_keywords(self):
        from eden.application.agent import ORACLE_PROMPT

        prompt = ORACLE_PROMPT.lower()
        assert "predict" in prompt or "forecast" in prompt or "project" in prompt
        assert "trend" in prompt or "sol" in prompt or "future" in prompt

    def test_chronos_prompt_has_mission_keywords(self):
        from eden.application.agent import CHRONOS_PROMPT

        prompt = CHRONOS_PROMPT.lower()
        assert "mission" in prompt or "timeline" in prompt or "450" in prompt
        assert "strategy" in prompt or "milestone" in prompt or "rotation" in prompt

    def test_pathfinder_prompt_has_disease_keywords(self):
        from eden.application.agent import PATHFINDER_PROMPT

        prompt = PATHFINDER_PROMPT.lower()
        assert "pathogen" in prompt or "disease" in prompt or "fungi" in prompt
        assert "detection" in prompt or "prevention" in prompt or "biocontrol" in prompt

    def test_all_prompts_request_json_output(self):
        """Every prompt should instruct the agent to output JSON decisions."""
        from eden.application.agent import _SPECIALIST_PROMPTS

        for name, prompt in _SPECIALIST_PROMPTS.items():
            assert "json" in prompt.lower() or "severity" in prompt.lower(), (
                f"{name} prompt missing JSON output instruction"
            )


# ── Test: Tool functions ────────────────────────────────────────────────


class TestToolFunctions:
    def test_read_sensors(self):
        from eden.application.agent import read_sensors

        zone = _make_zone("alpha", temperature=25.0)
        sensor = MockSensor({"alpha": zone})

        result = read_sensors(sensor, "alpha")

        assert result["zone_id"] == "alpha"
        assert result["temperature"] == 25.0

    def test_read_sensors_missing_zone(self):
        from eden.application.agent import read_sensors

        sensor = MockSensor({})
        result = read_sensors(sensor, "nonexistent")
        assert result is None

    def test_read_all_zones(self):
        from eden.application.agent import read_all_zones

        zones = {
            "alpha": _make_zone("alpha"),
            "beta": _make_zone("beta"),
        }
        sensor = MockSensor(zones)

        result = read_all_zones(sensor)

        assert "alpha" in result
        assert "beta" in result

    def test_log_decision(self):
        from eden.application.agent import log_decision

        agent_log = MockAgentLog()
        log_decision(agent_log, "DEMETER", "medium", "temp is high", "reduce heater")

        assert len(agent_log.decisions) == 1
        assert agent_log.decisions[0].agent_name == "DEMETER"
        assert agent_log.decisions[0].severity == Severity.MEDIUM

    def test_get_mars_conditions(self):
        from eden.application.agent import get_mars_conditions

        result = get_mars_conditions(sol=42, dust_opacity=0.5)

        assert result["sol"] == 42
        assert result["dust_opacity"] == 0.5

    def test_set_actuator(self):
        from eden.application.agent import set_actuator

        actuator = MockActuator()
        result = set_actuator(actuator, "alpha", "fan", "on", 75.0, "temp high")

        assert result is True
        assert len(actuator.commands) == 1
        assert actuator.commands[0].zone_id == "alpha"

    def test_get_desired_state(self):
        from eden.application.agent import get_desired_state

        store = MockStateStore()
        ds = DesiredState("alpha", 18.0, 26.0, 40.0, 70.0, 16.0, 30.0, 60.0, 5.0)
        store.put_desired_state("alpha", ds)

        result = get_desired_state(store, "alpha")

        assert result["temp_min"] == 18.0
        assert result["temp_max"] == 26.0

    def test_get_desired_state_missing(self):
        from eden.application.agent import get_desired_state

        store = MockStateStore()
        result = get_desired_state(store, "nonexistent")
        assert result is None

    def test_update_desired_state(self):
        from eden.application.agent import update_desired_state

        store = MockStateStore()
        ds = DesiredState("alpha", 18.0, 26.0, 40.0, 70.0, 16.0, 30.0, 60.0, 5.0)
        store.put_desired_state("alpha", ds)

        update_desired_state(store, "alpha", "temp", 20.0, 28.0)

        updated = store.get_desired_state("alpha")
        assert updated.temp_min == 20.0
        assert updated.temp_max == 28.0

    def test_get_nutritional_status(self):
        from eden.application.agent import get_nutritional_status

        nutrition = _make_nutrition()
        result = get_nutritional_status(nutrition)

        assert "crew" in result
        assert len(result["crew"]) == 4

    def test_query_telemetry(self):
        from eden.application.agent import query_telemetry

        store = MockTelemetryStore()
        reading = SensorReading("alpha", SensorType.TEMPERATURE, 22.0, "celsius", time.time(), "test")
        store.append(reading)

        result = query_telemetry(store, "alpha", hours=1.0)

        assert len(result) == 1

    def test_triage_zone(self):
        from eden.application.agent import triage_zone

        zone = _make_zone("alpha", temperature=22.0, water_level=80.0)
        sensor = MockSensor({"alpha": zone})
        nutrition = _make_nutrition()

        result = triage_zone(sensor, nutrition, "alpha")

        assert "zone_id" in result
        assert "salvageability" in result

    def test_request_crew_intervention(self):
        from eden.application.agent import request_crew_intervention

        agent_log = MockAgentLog()
        request_crew_intervention(agent_log, "repair sensor", "high", 30)

        assert len(agent_log.decisions) == 1
        assert "repair sensor" in agent_log.decisions[0].action

    def test_inject_chaos(self):
        from eden.application.agent import inject_chaos

        result = inject_chaos("dust_storm")

        assert "event_type" in result
        assert result["event_type"] == "dust_storm"

    def test_inject_chaos_unknown_type(self):
        from eden.application.agent import inject_chaos

        result = inject_chaos("unknown_event")

        assert "event_type" in result

    def test_propose_flight_rule(self):
        from eden.application.agent import propose_flight_rule

        engine = FlightRulesEngine()
        propose_flight_rule(
            engine,
            rule_id="FR-CUSTOM-001",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            device="fan",
            action="on",
            value=80.0,
            cooldown_seconds=120,
            priority="high",
        )

        assert len(engine.get_candidates()) == 1
        assert engine.get_candidates()[0].rule_id == "FR-CUSTOM-001"
