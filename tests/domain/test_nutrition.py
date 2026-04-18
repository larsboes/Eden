"""Tests for eden.domain.nutrition — TDD: written BEFORE implementation."""

from eden.domain.models import CrewMember, CropProfile
from eden.domain.nutrition import NutritionTracker


# ── Fixtures ────────────────────────────────────────────────────────────


def _crew() -> list[CrewMember]:
    return [
        CrewMember("Cmdr. Chen", 2500.0, 60.0),
        CrewMember("Dr. Okafor", 2500.0, 60.0),
        CrewMember("Eng. Petrov", 2500.0, 60.0),
        CrewMember("Sci. Tanaka", 2500.0, 60.0),
    ]


def _crops() -> list[CropProfile]:
    return [
        CropProfile("tomato", "zone-a", 180.0, 9.0, 80, 3.5, 18, 29, 50, 80),
        CropProfile("potato", "zone-b", 770.0, 20.0, 90, 4.0, 15, 25, 60, 80),
        CropProfile("soybean", "zone-c", 1460.0, 360.0, 85, 2.5, 20, 30, 40, 70),
    ]


def _tracker() -> NutritionTracker:
    return NutritionTracker(_crew(), _crops(), mission_days=450)


# ── Construction ────────────────────────────────────────────────────────


class TestConstruction:
    def test_creates_with_crew_and_crops(self):
        t = _tracker()
        assert len(t.crew) == 4
        assert len(t.crops) == 3
        assert t.mission_days == 450

    def test_default_crew(self):
        crew = NutritionTracker.get_default_crew()
        assert len(crew) == 4
        for member in crew:
            assert isinstance(member, CrewMember)
            assert member.daily_kcal_target > 0
            assert member.daily_protein_target > 0

    def test_single_crew_member(self):
        t = NutritionTracker(
            [CrewMember("Solo", 2500.0, 60.0)], _crops(), mission_days=100
        )
        assert len(t.crew) == 1


# ── Record Harvest ──────────────────────────────────────────────────────


class TestRecordHarvest:
    def test_distributes_calories_evenly(self):
        t = _tracker()
        # 10 kg of potato @ 770 kcal/kg = 7700 kcal total → 1925 per crew
        t.record_harvest("potato", 10.0)
        for member in t.crew:
            assert abs(member.current_kcal_intake - 1925.0) < 0.01

    def test_distributes_protein_evenly(self):
        t = _tracker()
        # 10 kg of potato @ 20g protein/kg = 200g total → 50g per crew
        t.record_harvest("potato", 10.0)
        for member in t.crew:
            assert abs(member.current_protein_intake - 50.0) < 0.01

    def test_multiple_harvests_accumulate(self):
        t = _tracker()
        t.record_harvest("potato", 10.0)  # 1925 kcal/person
        t.record_harvest("tomato", 5.0)  # 5*180/4 = 225 kcal/person
        for member in t.crew:
            assert abs(member.current_kcal_intake - 2150.0) < 0.01

    def test_unknown_crop_ignored(self):
        t = _tracker()
        t.record_harvest("mystery_fruit", 100.0)
        for member in t.crew:
            assert member.current_kcal_intake == 0.0

    def test_zero_kg_harvest(self):
        t = _tracker()
        t.record_harvest("potato", 0.0)
        for member in t.crew:
            assert member.current_kcal_intake == 0.0


# ── Nutritional Status ──────────────────────────────────────────────────


class TestNutritionalStatus:
    def test_status_has_all_crew(self):
        t = _tracker()
        status = t.get_nutritional_status()
        assert len(status["crew"]) == 4

    def test_status_shows_zero_intake_initially(self):
        t = _tracker()
        status = t.get_nutritional_status()
        for s in status["crew"]:
            assert s["current_kcal_intake"] == 0.0
            assert s["current_protein_intake"] == 0.0

    def test_status_reflects_harvest(self):
        t = _tracker()
        t.record_harvest("potato", 10.0)
        status = t.get_nutritional_status()
        for s in status["crew"]:
            assert s["current_kcal_intake"] == 1925.0
            assert s["kcal_deficit"] == 575.0  # 2500 - 1925

    def test_status_shows_surplus(self):
        t = _tracker()
        # Enough to exceed target: 2500*4/770 ≈ 12.99 kg needed, give 15
        t.record_harvest("potato", 15.0)
        status = t.get_nutritional_status()
        for s in status["crew"]:
            # 15*770/4 = 2887.5 → surplus of 387.5
            assert s["kcal_deficit"] == 0.0
            assert abs(s["kcal_surplus"] - 387.5) < 0.01


# ── Reset Daily Intake ──────────────────────────────────────────────────


class TestResetDailyIntake:
    def test_zeros_all_intake(self):
        t = _tracker()
        t.record_harvest("potato", 10.0)
        t.reset_daily_intake()
        for member in t.crew:
            assert member.current_kcal_intake == 0.0
            assert member.current_protein_intake == 0.0


# ── Deficiency Risks ────────────────────────────────────────────────────


class TestDeficiencyRisks:
    def test_no_risks_when_fully_fed(self):
        t = _tracker()
        # Record enough days at target
        for _ in range(10):
            t.record_harvest("potato", 13.0)  # ~2502.5 kcal/person
            t.record_harvest("soybean", 1.0)  # extra protein boost
            t.advance_day()
        risks = t.get_deficiency_risks(days_ahead=30)
        # Should have no critical/warning for kcal
        kcal_risks = [r for r in risks if r["nutrient"] == "calories"]
        assert all(r["level"] != "critical" for r in kcal_risks)

    def test_warning_when_below_80_pct(self):
        t = _tracker()
        # Feed at 70% of target for 10 days
        # 2500*0.7 = 1750 kcal/person/day → need 1750*4/770 ≈ 9.09 kg potato
        for _ in range(10):
            t.record_harvest("potato", 9.0)  # ~1732.5 kcal/person
            t.advance_day()
        risks = t.get_deficiency_risks(days_ahead=30)
        kcal_risks = [r for r in risks if r["nutrient"] == "calories"]
        assert any(r["level"] == "warning" for r in kcal_risks)

    def test_critical_when_below_60_pct(self):
        t = _tracker()
        # Feed at 50% of target for 10 days
        for _ in range(10):
            t.record_harvest("potato", 6.5)  # ~1251 kcal/person
            t.advance_day()
        risks = t.get_deficiency_risks(days_ahead=30)
        kcal_risks = [r for r in risks if r["nutrient"] == "calories"]
        assert any(r["level"] == "critical" for r in kcal_risks)

    def test_no_history_returns_critical(self):
        t = _tracker()
        risks = t.get_deficiency_risks(days_ahead=30)
        # No food at all → critical
        kcal_risks = [r for r in risks if r["nutrient"] == "calories"]
        assert any(r["level"] == "critical" for r in kcal_risks)


# ── Mission Projection ──────────────────────────────────────────────────


class TestMissionProjection:
    def test_projection_total_required(self):
        t = _tracker()
        proj = t.get_mission_projection()
        # 4 crew × 2500 kcal × 450 days = 4,500,000
        assert proj["total_kcal_required"] == 4_500_000.0
        # 4 crew × 60g protein × 450 days = 108,000
        assert proj["total_protein_required"] == 108_000.0

    def test_projection_with_no_harvests(self):
        t = _tracker()
        proj = t.get_mission_projection()
        assert proj["total_kcal_harvested"] == 0.0
        assert proj["total_protein_harvested"] == 0.0
        assert proj["kcal_coverage_pct"] == 0.0

    def test_projection_accumulates_harvests(self):
        t = _tracker()
        t.record_harvest("potato", 10.0)  # 7700 kcal, 200g protein
        t.advance_day()
        proj = t.get_mission_projection()
        assert proj["total_kcal_harvested"] == 7700.0
        assert proj["total_protein_harvested"] == 200.0

    def test_projection_coverage_pct(self):
        t = _tracker()
        t.record_harvest("potato", 10.0)  # 7700 kcal
        t.advance_day()
        proj = t.get_mission_projection()
        expected_pct = (7700.0 / 4_500_000.0) * 100
        assert abs(proj["kcal_coverage_pct"] - expected_pct) < 0.01


# ── Edge Cases ──────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_no_crops(self):
        t = NutritionTracker(_crew(), [], mission_days=450)
        t.record_harvest("potato", 10.0)
        for member in t.crew:
            assert member.current_kcal_intake == 0.0

    def test_advance_day_increments_sol(self):
        t = _tracker()
        assert t.current_sol == 0
        t.advance_day()
        assert t.current_sol == 1

    def test_advance_day_resets_intake(self):
        t = _tracker()
        t.record_harvest("potato", 10.0)
        t.advance_day()
        for member in t.crew:
            assert member.current_kcal_intake == 0.0
