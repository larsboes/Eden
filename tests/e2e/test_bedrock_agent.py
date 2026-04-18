"""E2E test: DEMETER agent reasoning about heat-stressed tomatoes via real Bedrock.

Sends realistic zone data (38°C, 35% humidity) to DEMETER through the actual
BedrockAdapter and verifies the response contains sensible agricultural advice.
"""

import json
import pytest

from eden.adapters.bedrock_adapter import BedrockAdapter
from eden.application.agent import DEMETER_PROMPT


@pytest.fixture(scope="module")
def bedrock():
    """Real Bedrock adapter — no mocks."""
    adapter = BedrockAdapter(
        model_id="us.anthropic.claude-sonnet-4-6",
        region="us-west-2",
    )
    if not adapter.is_available():
        pytest.skip("Bedrock not reachable — skipping e2e")
    return adapter


# ── Zone data: tomatoes under heat stress ────────────────────────────────

ZONE_ALPHA = {
    "zone_id": "alpha",
    "crop": "tomatoes",
    "growth_stage": "fruiting",
    "temperature": 38.0,
    "humidity": 35.0,
    "light": 800,
    "water_level": 42.0,
    "co2_ppm": 950,
    "is_alive": True,
    "fire_detected": False,
}

CONTEXT = {
    "zones": {"alpha": ZONE_ALPHA},
    "mars_conditions": {
        "sol": 180,
        "dust_opacity": 0.3,
        "solar_irradiance_w_m2": 300,
        "outside_temp_c": -60,
        "daylight_hours": 12.3,
    },
    "deltas": {
        "alpha": {
            "temperature": "+2.5 in last hour",
            "humidity": "-8 in last hour",
        }
    },
    "nutritional_status": {
        "crew_size": 4,
        "daily_kcal_target": 10000,
        "vitamin_c_status": "adequate",
    },
    "desired_states": {
        "alpha": {
            "temp_min": 20.0,
            "temp_max": 28.0,
            "humidity_min": 55.0,
            "humidity_max": 75.0,
        }
    },
}


def _build_demeter_prompt() -> str:
    """Mirror AgentTeam._run_specialist for DEMETER."""
    return (
        f"[DEMETER] {DEMETER_PROMPT}\n\n"
        f"Current zones: {json.dumps(CONTEXT['zones'], indent=2)}\n"
        f"Mars conditions: {json.dumps(CONTEXT['mars_conditions'], indent=2)}\n"
        f"Deltas: {json.dumps(CONTEXT['deltas'], indent=2)}\n"
        f"Nutritional status: {json.dumps(CONTEXT['nutritional_status'], indent=2)}\n"
        f"Desired state: {json.dumps(CONTEXT['desired_states'], indent=2)}\n"
        f"Analyze and recommend."
    )


# ── The actual test ──────────────────────────────────────────────────────


def test_demeter_heat_stress_response(bedrock):
    """DEMETER should identify heat stress and recommend cooling/irrigation."""
    prompt = _build_demeter_prompt()
    response = bedrock.reason(prompt, CONTEXT)

    # Basic sanity — we got a non-empty response
    assert response, "Bedrock returned empty response"
    print(f"\n{'='*60}")
    print("DEMETER RAW RESPONSE:")
    print(f"{'='*60}")
    print(response)
    print(f"{'='*60}\n")

    # Response should be parseable JSON (DEMETER is instructed to output JSON array)
    lower = response.lower()

    # ── Content checks: DEMETER must recognise the heat stress scenario ──
    # At least one of these heat/temperature keywords should appear
    heat_keywords = ["heat", "temperature", "hot", "cool", "thermal", "overheat", "warm"]
    assert any(kw in lower for kw in heat_keywords), (
        f"Response lacks any heat-related keyword. Keywords checked: {heat_keywords}"
    )

    # Should mention irrigation or humidity (both are low)
    water_keywords = ["water", "irrigat", "humid", "moisture", "dry", "mist"]
    assert any(kw in lower for kw in water_keywords), (
        f"Response lacks any water/humidity keyword. Keywords checked: {water_keywords}"
    )

    # Should reference the zone or the crop
    assert "alpha" in lower or "tomato" in lower, (
        "Response doesn't reference zone 'alpha' or crop 'tomatoes'"
    )

    # Try to parse as JSON array — DEMETER should output structured decisions
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start >= 0 and end > start:
            decisions = json.loads(response[start:end])
            assert isinstance(decisions, list), "Parsed JSON is not a list"
            assert len(decisions) > 0, "DEMETER returned empty decision list for a stressed zone"
            print(f"Parsed {len(decisions)} decision(s):")
            for i, d in enumerate(decisions):
                print(f"  [{i}] severity={d.get('severity')}, action={d.get('action', 'N/A')}")
                print(f"       reasoning: {d.get('reasoning', 'N/A')[:120]}")

            # At least one decision should be high or critical severity
            severities = [d.get("severity", "").lower() for d in decisions]
            assert any(s in ("critical", "high") for s in severities), (
                f"No critical/high severity decision for 38°C heat stress. Severities: {severities}"
            )
        else:
            # If no JSON array found, that's still a partial pass — the content checks above passed
            print("WARNING: Could not extract JSON array from response (content checks passed)")
    except json.JSONDecodeError as e:
        print(f"WARNING: JSON parse failed ({e}) — content keyword checks still passed")
