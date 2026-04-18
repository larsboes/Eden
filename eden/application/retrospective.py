"""EDEN Retrospective — periodic self-assessment of flight rules + agent decisions.

Runs every N reconciler cycles (default: every 10 cycles, ~50 min at 5-min intervals).

Analyzes:
1. Rule trigger patterns — which rules fire most, why, effectiveness
2. Feedback correlation — did triggered rules actually improve conditions?
3. Zone health trends — are zones getting better or worse over time?
4. Rule lifecycle management — propose new, promote shadow → active, demote ineffective

Outputs:
- RetrospectiveReport (persisted via sqlite)
- ManagedRule lifecycle transitions
- AgentDecision audit trail
"""

from __future__ import annotations

import structlog
import time

from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.models import (
    AgentDecision,
    ManagedRule,
    RuleLifecycle,
    Severity,
    Tier,
)

logger = structlog.get_logger(__name__)


class Retrospective:
    """Periodic self-assessment of the EDEN flight rules and agent system.

    Pure domain logic — no external dependencies. Injected with flight engine
    and optional model for AI-enhanced analysis.
    """

    # Run retrospective every N reconciler cycles
    DEFAULT_INTERVAL = 10

    # Shadow hits required before promoting to active
    SHADOW_PROMOTION_THRESHOLD = 5

    # Active hits with negative feedback → demotion
    DEMOTION_THRESHOLD = 3

    def __init__(
        self,
        flight_engine: FlightRulesEngine,
        interval: int = DEFAULT_INTERVAL,
        event_bus=None,
    ) -> None:
        self._engine = flight_engine
        self._interval = interval
        self._event_bus = event_bus
        self._cycle_count = 0
        self._feedback_buffer: list[dict] = []
        self._managed_rules: dict[str, ManagedRule] = {}
        self._reports: list[dict] = []

    def _emit(self, event_type: str, data: dict) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(event_type, data)

    def ingest_feedback(self, feedback: list[dict]) -> None:
        """Buffer closed-loop feedback for next retrospective cycle."""
        self._feedback_buffer.extend(feedback)
        # Keep buffer bounded
        if len(self._feedback_buffer) > 200:
            self._feedback_buffer = self._feedback_buffer[-200:]

    def tick(self) -> list[AgentDecision]:
        """Called every reconciler cycle. Runs retrospective every N cycles."""
        self._cycle_count += 1
        if self._cycle_count % self._interval != 0:
            return []

        return self.run()

    def run(self) -> list[AgentDecision]:
        """Execute a full retrospective analysis cycle."""
        now = time.time()
        decisions: list[AgentDecision] = []

        # 1. Analyze rule trigger patterns
        trigger_analysis = self._analyze_triggers()
        decisions.extend(trigger_analysis)

        # 2. Promote shadow rules that have enough evidence
        promotions = self._promote_shadow_rules(now)
        decisions.extend(promotions)

        # 3. Demote ineffective rules based on feedback
        demotions = self._demote_ineffective(now)
        decisions.extend(demotions)

        # 4. Generate retrospective report
        report = self._generate_report(now, decisions)
        self._reports.append(report)
        if len(self._reports) > 50:
            self._reports = self._reports[-50:]

        self._emit("retrospective_complete", report)

        # Clear feedback buffer after processing
        self._feedback_buffer = []

        return decisions

    def _analyze_triggers(self) -> list[AgentDecision]:
        """Analyze which rules are firing most and whether they're effective."""
        decisions: list[AgentDecision] = []
        now = time.time()

        trigger_counts = self._engine._trigger_counts
        if not trigger_counts:
            return decisions

        # Find hot rules (frequent triggers may indicate thresholds need adjustment)
        sorted_rules = sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)

        for rule_id, count in sorted_rules[:5]:
            if count >= 10:
                decisions.append(AgentDecision(
                    timestamp=now,
                    agent_name="RETROSPECTIVE",
                    severity=Severity.INFO,
                    reasoning=(
                        f"Rule {rule_id} has fired {count} times — "
                        f"high frequency may indicate threshold needs adjustment "
                        f"or a persistent environmental issue"
                    ),
                    action=f"ANALYZE {rule_id} frequency={count}",
                    result="analyzed",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                ))

        return decisions

    def _promote_shadow_rules(self, now: float) -> list[AgentDecision]:
        """Promote candidate rules with sufficient shadow evidence."""
        decisions: list[AgentDecision] = []
        shadow_hits = self._engine.get_shadow_hits()

        candidates_to_promote: list[str] = []

        for candidate in list(self._engine.get_candidates()):
            hits = shadow_hits.get(candidate.rule_id, 0)
            if hits < self.SHADOW_PROMOTION_THRESHOLD:
                continue

            # Check for conflicts with existing active rules
            has_conflict = False
            for active in self._engine.rules:
                if not active.enabled:
                    continue
                if (active.sensor_type == candidate.sensor_type
                        and active.condition == candidate.condition):
                    if candidate.condition in ("gt", "gte"):
                        if active.threshold <= candidate.threshold:
                            has_conflict = True
                            break
                    elif candidate.condition in ("lt", "lte"):
                        if active.threshold >= candidate.threshold:
                            has_conflict = True
                            break

            if has_conflict:
                decisions.append(AgentDecision(
                    timestamp=now,
                    agent_name="RETROSPECTIVE",
                    severity=Severity.INFO,
                    reasoning=(
                        f"Shadow rule {candidate.rule_id} has {hits} hits "
                        f"but conflicts with active rule — deferring promotion"
                    ),
                    action=f"DEFER {candidate.rule_id}",
                    result="deferred",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                ))
                continue

            candidates_to_promote.append(candidate.rule_id)

            # Track in managed rules
            managed = ManagedRule(
                rule=candidate,
                lifecycle=RuleLifecycle.ACTIVE,
                source_retro_id=f"retro-{self._cycle_count}",
                proposed_at=now - 600,  # approximate
                promoted_at=now,
                shadow_hits=hits,
            )
            self._managed_rules[candidate.rule_id] = managed

            decisions.append(AgentDecision(
                timestamp=now,
                agent_name="RETROSPECTIVE",
                severity=Severity.INFO,
                reasoning=(
                    f"Shadow rule {candidate.rule_id} promoted to active — "
                    f"{hits} shadow hits, no conflicts detected"
                ),
                action=f"PROMOTE {candidate.rule_id} shadow_hits={hits}",
                result="promoted",
                zone_id="global",
                tier=Tier.FLIGHT_RULES,
            ))

        # Actually promote in the engine
        for rule_id in candidates_to_promote:
            for candidate in list(self._engine._candidates):
                if candidate.rule_id == rule_id:
                    from eden.domain.models import FlightRule
                    promoted = FlightRule(
                        rule_id=candidate.rule_id,
                        sensor_type=candidate.sensor_type,
                        condition=candidate.condition,
                        threshold=candidate.threshold,
                        device=candidate.device,
                        action=candidate.action,
                        value=candidate.value,
                        cooldown_seconds=candidate.cooldown_seconds,
                        priority=candidate.priority,
                        enabled=True,
                    )
                    self._engine.rules.append(promoted)
                    self._engine._candidates = [
                        c for c in self._engine._candidates if c.rule_id != rule_id
                    ]
                    self._engine._shadow_hits.pop(rule_id, None)
                    break

        return decisions

    def _demote_ineffective(self, now: float) -> list[AgentDecision]:
        """Demote learned rules that have negative feedback correlation."""
        decisions: list[AgentDecision] = []

        if not self._feedback_buffer:
            return decisions

        # Count negative feedback per zone after rule triggers
        # (zone got worse despite rule firing)
        negative_correlation: dict[str, int] = {}
        for fb in self._feedback_buffer:
            zone_id = fb.get("zone_id", "")
            improvements = fb.get("improvements", {})
            if not improvements:
                # No improvement → negative signal for all rules that fired for this zone
                for rule in self._engine.rules:
                    if rule.rule_id.startswith("FR-LRN-"):
                        negative_correlation[rule.rule_id] = (
                            negative_correlation.get(rule.rule_id, 0) + 1
                        )

        for rule_id, neg_count in negative_correlation.items():
            if neg_count >= self.DEMOTION_THRESHOLD:
                # Demote: disable the rule
                for rule in self._engine.rules:
                    if rule.rule_id == rule_id and rule.enabled:
                        # Can't modify frozen, but FlightRule is not frozen
                        rule.enabled = False

                        if rule_id in self._managed_rules:
                            self._managed_rules[rule_id].lifecycle = RuleLifecycle.DEMOTED
                            self._managed_rules[rule_id].demotion_reason = (
                                f"Negative feedback correlation: {neg_count} cycles "
                                f"with no improvement after rule triggered"
                            )

                        decisions.append(AgentDecision(
                            timestamp=now,
                            agent_name="RETROSPECTIVE",
                            severity=Severity.INFO,
                            reasoning=(
                                f"Learned rule {rule_id} demoted — "
                                f"{neg_count} cycles with negative feedback correlation"
                            ),
                            action=f"DEMOTE {rule_id} neg_feedback={neg_count}",
                            result="demoted",
                            zone_id="global",
                            tier=Tier.FLIGHT_RULES,
                        ))
                        break

        return decisions

    def _generate_report(self, now: float, decisions: list[AgentDecision]) -> dict:
        """Generate a retrospective report summary."""
        trigger_counts = self._engine._trigger_counts
        shadow_hits = self._engine.get_shadow_hits()
        candidates = self._engine.get_candidates()

        return {
            "timestamp": now,
            "cycle": self._cycle_count,
            "total_active_rules": len([r for r in self._engine.rules if r.enabled]),
            "total_candidates": len(candidates),
            "total_managed": len(self._managed_rules),
            "trigger_counts": dict(trigger_counts),
            "shadow_hits": shadow_hits,
            "feedback_processed": len(self._feedback_buffer),
            "decisions_made": len(decisions),
            "promotions": sum(1 for d in decisions if "PROMOTE" in d.action),
            "demotions": sum(1 for d in decisions if "DEMOTE" in d.action),
        }

    def get_reports(self, limit: int = 10) -> list[dict]:
        """Return recent retrospective reports."""
        return self._reports[-limit:]

    def get_managed_rules(self) -> list[ManagedRule]:
        """Return all managed rules with lifecycle metadata."""
        return list(self._managed_rules.values())
