"""Crew nutritional tracking for 4 astronauts × 450-day Mars mission.

PURE PYTHON. Zero external imports. Only stdlib + domain models. THIS IS THE LAW.
"""

from __future__ import annotations

from eden.domain.models import CrewMember, CropProfile


class NutritionTracker:
    """Track crew nutrition across the mission arc.

    Records harvests, distributes calories/protein evenly across crew,
    flags deficiency risks, and projects mission-wide nutritional status.
    """

    def __init__(
        self,
        crew: list[CrewMember],
        crops: list[CropProfile],
        mission_days: int = 450,
    ) -> None:
        self.crew = crew
        self.crops = {c.name: c for c in crops}
        self.mission_days = mission_days
        self.current_sol: int = 0

        # Historical tracking for deficiency risk analysis
        self._daily_history: list[dict] = []  # per-day average intake ratios
        self._total_kcal_harvested: float = 0.0
        self._total_protein_harvested: float = 0.0

    # ── Class methods ───────────────────────────────────────────────────

    @staticmethod
    def get_default_crew() -> list[CrewMember]:
        """Return 4 default crew members with standard Mars mission targets."""
        return [
            CrewMember("Cmdr. Chen", 2500.0, 60.0),
            CrewMember("Dr. Okafor", 2500.0, 60.0),
            CrewMember("Eng. Petrov", 2500.0, 60.0),
            CrewMember("Sci. Tanaka", 2500.0, 60.0),
        ]

    # ── Core operations ─────────────────────────────────────────────────

    def record_harvest(self, crop_name: str, kg: float) -> None:
        """Distribute harvested crop calories/protein evenly across crew."""
        crop = self.crops.get(crop_name)
        if crop is None or kg <= 0 or not self.crew:
            return

        total_kcal = crop.calories_per_kg * kg
        total_protein = crop.protein_per_kg * kg
        per_member_kcal = total_kcal / len(self.crew)
        per_member_protein = total_protein / len(self.crew)

        for member in self.crew:
            member.current_kcal_intake += per_member_kcal
            member.current_protein_intake += per_member_protein

    def reset_daily_intake(self) -> None:
        """Zero out current intake for all crew (called at start of each sol)."""
        for member in self.crew:
            member.current_kcal_intake = 0.0
            member.current_protein_intake = 0.0

    def advance_day(self) -> None:
        """End current sol: snapshot intake ratios, reset, increment sol."""
        # Snapshot today's intake ratios before resetting
        if self.crew:
            day_total_kcal = sum(m.current_kcal_intake for m in self.crew)
            day_total_protein = sum(m.current_protein_intake for m in self.crew)
            self._total_kcal_harvested += day_total_kcal
            self._total_protein_harvested += day_total_protein

            avg_kcal_ratio = sum(
                m.current_kcal_intake / m.daily_kcal_target
                for m in self.crew
                if m.daily_kcal_target > 0
            ) / len(self.crew)
            avg_protein_ratio = sum(
                m.current_protein_intake / m.daily_protein_target
                for m in self.crew
                if m.daily_protein_target > 0
            ) / len(self.crew)

            self._daily_history.append(
                {"kcal_ratio": avg_kcal_ratio, "protein_ratio": avg_protein_ratio}
            )

        self.reset_daily_intake()
        self.current_sol += 1

    # ── Queries ─────────────────────────────────────────────────────────

    def get_nutritional_status(self) -> dict:
        """Per-crew-member status: targets, intake, deficit/surplus."""
        crew_status = []
        for m in self.crew:
            kcal_diff = m.daily_kcal_target - m.current_kcal_intake
            protein_diff = m.daily_protein_target - m.current_protein_intake
            crew_status.append(
                {
                    "name": m.name,
                    "daily_kcal_target": m.daily_kcal_target,
                    "daily_protein_target": m.daily_protein_target,
                    "current_kcal_intake": m.current_kcal_intake,
                    "current_protein_intake": m.current_protein_intake,
                    "kcal_deficit": max(0.0, kcal_diff),
                    "kcal_surplus": max(0.0, -kcal_diff),
                    "protein_deficit": max(0.0, protein_diff),
                    "protein_surplus": max(0.0, -protein_diff),
                }
            )
        return {"sol": self.current_sol, "crew": crew_status}

    def get_deficiency_risks(self, days_ahead: int = 30) -> list[dict]:
        """Project deficiency risks based on recent intake history.

        - Warning: average intake <80% of target for >7 days
        - Critical: average intake <60% of target OR no data at all
        """
        risks: list[dict] = []
        history = self._daily_history

        for nutrient, ratio_key in [
            ("calories", "kcal_ratio"),
            ("protein", "protein_ratio"),
        ]:
            if not history:
                # No data at all → critical
                risks.append(
                    {
                        "nutrient": nutrient,
                        "level": "critical",
                        "message": f"No intake data — {nutrient} deficiency imminent",
                        "projected_days_until_critical": 0,
                    }
                )
                continue

            # Use last 7 days (or all available) for trend
            recent = history[-7:]
            avg_ratio = sum(d[ratio_key] for d in recent) / len(recent)

            if avg_ratio < 0.6:
                risks.append(
                    {
                        "nutrient": nutrient,
                        "level": "critical",
                        "message": f"{nutrient} intake at {avg_ratio * 100:.0f}% — critical deficiency",
                        "projected_days_until_critical": 0,
                    }
                )
            elif avg_ratio < 0.8:
                # Estimate days until critical (linear projection to 60%)
                days_to_critical = int(
                    days_ahead * (avg_ratio - 0.6) / (1.0 - 0.6)
                ) if avg_ratio > 0.6 else 0
                risks.append(
                    {
                        "nutrient": nutrient,
                        "level": "warning",
                        "message": f"{nutrient} intake at {avg_ratio * 100:.0f}% — warning",
                        "projected_days_until_critical": days_to_critical,
                    }
                )

        return risks

    def get_mission_projection(self) -> dict:
        """Project total calories/protein vs required over the full mission."""
        total_kcal_required = sum(
            m.daily_kcal_target * self.mission_days for m in self.crew
        )
        total_protein_required = sum(
            m.daily_protein_target * self.mission_days for m in self.crew
        )

        # Include current day's unharvested intake in totals
        current_day_kcal = sum(m.current_kcal_intake for m in self.crew)
        current_day_protein = sum(m.current_protein_intake for m in self.crew)
        harvested_kcal = self._total_kcal_harvested + current_day_kcal
        harvested_protein = self._total_protein_harvested + current_day_protein

        kcal_coverage = (
            (harvested_kcal / total_kcal_required * 100)
            if total_kcal_required > 0
            else 0.0
        )
        protein_coverage = (
            (harvested_protein / total_protein_required * 100)
            if total_protein_required > 0
            else 0.0
        )

        # Project daily rate forward
        days_elapsed = max(self.current_sol, 1)
        daily_kcal_rate = harvested_kcal / days_elapsed
        daily_protein_rate = harvested_protein / days_elapsed
        remaining_days = max(0, self.mission_days - self.current_sol)
        projected_total_kcal = harvested_kcal + daily_kcal_rate * remaining_days
        projected_total_protein = (
            harvested_protein + daily_protein_rate * remaining_days
        )

        return {
            "mission_days": self.mission_days,
            "current_sol": self.current_sol,
            "total_kcal_required": total_kcal_required,
            "total_protein_required": total_protein_required,
            "total_kcal_harvested": harvested_kcal,
            "total_protein_harvested": harvested_protein,
            "kcal_coverage_pct": kcal_coverage,
            "protein_coverage_pct": protein_coverage,
            "projected_total_kcal": projected_total_kcal,
            "projected_total_protein": projected_total_protein,
        }
