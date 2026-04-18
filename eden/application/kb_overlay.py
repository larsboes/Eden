"""KB Parameterization Overlay — enriches CROP_LIBRARY from Syngenta MCP KB.

Queries the KB at startup for each crop, extracts numerical parameters,
and patches CROP_LIBRARY defaults. Falls back gracefully if KB is offline.

Layer 2 of the 3-layer parameterization strategy:
  Layer 1: Hardcoded agronomic defaults in CROP_LIBRARY (always works)
  Layer 2: Syngenta KB overlay (this module — query once, cache forever)
  Layer 3: Mars-specific adjustments (applied in simulation physics)
"""

from __future__ import annotations

import structlog
import re

from eden.domain.simulation import CROP_LIBRARY, CropSimParams

logger = structlog.get_logger(__name__)

# Patterns for extracting numbers from KB narrative text
_NUMBER_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")


def _extract_first_number(text: str, default: float) -> float:
    """Extract the first number from a text string."""
    match = _NUMBER_PATTERN.search(text)
    if match:
        return float(match.group(1))
    return default


def _extract_range(text: str) -> tuple[float, float] | None:
    """Extract a numeric range like '15-25' or '15 to 25' from text."""
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)", text)
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))
    return None


def overlay_from_kb(kb_adapter, model=None) -> dict[str, dict]:
    """Query Syngenta KB for each crop and extract simulation parameter overrides.

    Args:
        kb_adapter: SyngentaKBAdapter instance (can be offline).
        model: Optional ModelPort for LLM-assisted parameter extraction.
               If None, uses regex-based extraction (less accurate but no LLM cost).

    Returns:
        Dict of crop_name -> parameter overrides applied to CROP_LIBRARY.
    """
    if kb_adapter is None or not kb_adapter.is_available():
        logger.info("KB offline — using Layer 1 defaults only")
        return {}

    overrides: dict[str, dict] = {}

    for crop_name in CROP_LIBRARY:
        try:
            raw = kb_adapter.query_simulation_params(crop_name)
            extracted = _extract_params_regex(crop_name, raw)

            if model is not None and model.is_available():
                llm_extracted = _extract_params_llm(crop_name, raw, model)
                extracted.update(llm_extracted)

            if extracted:
                overrides[crop_name] = extracted
                logger.info(
                    "KB overlay for %s: %d parameters extracted",
                    crop_name, len(extracted),
                )
        except Exception:
            logger.warning("KB overlay failed for %s — keeping defaults", crop_name)

    return overrides


def _extract_params_regex(crop_name: str, raw: dict) -> dict:
    """Regex-based extraction of numerical parameters from KB response text."""
    params: dict = {}

    # Extract from crop profile response
    profile_text = str(raw.get("crop_profile", {}).get("result", ""))
    stress_text = str(raw.get("stress_thresholds", {}).get("result", ""))

    # Temperature range
    for pattern in [
        r"optimal.*?temp.*?(\d+)\s*[-–to]+\s*(\d+)\s*[°C]",
        r"(\d+)\s*[-–to]+\s*(\d+)\s*°?C.*?optimal",
    ]:
        match = re.search(pattern, profile_text, re.IGNORECASE)
        if match:
            params["optimal_temp_min_c"] = float(match.group(1))
            params["optimal_temp_max_c"] = float(match.group(2))
            break

    # Base temperature for GDD
    for pattern in [
        r"base\s*temp.*?(\d+(?:\.\d+)?)\s*°?C",
        r"(\d+(?:\.\d+)?)\s*°?C\s*base",
    ]:
        match = re.search(pattern, profile_text, re.IGNORECASE)
        if match:
            params["base_temp_c"] = float(match.group(1))
            break

    # GDD to maturity
    for pattern in [
        r"(\d{3,5})\s*(?:GDD|growing\s*degree\s*days)",
        r"thermal\s*time.*?(\d{3,5})",
    ]:
        match = re.search(pattern, profile_text, re.IGNORECASE)
        if match:
            params["gdd_maturity"] = float(match.group(1))
            break

    # Harvest index
    match = re.search(r"harvest\s*index.*?(\d+(?:\.\d+)?)", profile_text, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        params["harvest_index"] = val if val <= 1.0 else val / 100.0

    return params


def _extract_params_llm(crop_name: str, raw: dict, model) -> dict:
    """LLM-assisted extraction for parameters regex can't reliably parse."""
    combined_text = ""
    for key in ("crop_profile", "stress_thresholds", "transpiration"):
        result = raw.get(key, {}).get("result", "")
        if isinstance(result, str):
            combined_text += f"\n{result}"

    if len(combined_text.strip()) < 50:
        return {}

    prompt = (
        f"Extract numerical crop simulation parameters for {crop_name} "
        f"from the following Syngenta KB text. Return ONLY a JSON object "
        f"with any of these keys you can find values for:\n"
        f"  base_temp_c, optimal_temp_min_c, optimal_temp_max_c, gdd_maturity,\n"
        f"  harvest_index, max_growth_rate, yield_kg_per_m2\n"
        f"If a value is not clearly stated, omit it. JSON only, no explanation.\n\n"
        f"Text:\n{combined_text[:2000]}"
    )

    try:
        import json
        response = model.reason(prompt, {})
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except Exception:
        logger.debug("LLM extraction failed for %s", crop_name)

    return {}


def apply_overrides(overrides: dict[str, dict]) -> None:
    """Patch CROP_LIBRARY in-place with KB-derived overrides.

    Only updates fields that exist on CropSimParams. Skips unknown keys.
    """
    import dataclasses

    valid_fields = {f.name for f in dataclasses.fields(CropSimParams)}

    for crop_name, params in overrides.items():
        if crop_name not in CROP_LIBRARY:
            continue

        current = CROP_LIBRARY[crop_name]
        updates = {k: v for k, v in params.items() if k in valid_fields}

        if updates:
            # Reconstruct frozen dataclass with updates
            current_dict = {f.name: getattr(current, f.name) for f in dataclasses.fields(current)}
            current_dict.update(updates)
            CROP_LIBRARY[crop_name] = CropSimParams(**current_dict)
            logger.info("Patched %s with KB overrides: %s", crop_name, list(updates.keys()))
