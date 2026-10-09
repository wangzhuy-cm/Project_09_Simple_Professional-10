"""Auditable market-reference snapshot used to seed simulation assumptions.

The snapshot is intentionally local and dated: the app remains fully usable
offline and never presents an external rate as a forecast or guarantee.
"""
from __future__ import annotations

import json
import math
from datetime import date
from copy import deepcopy
from pathlib import Path
from typing import Any


REFERENCE_PATH = Path(__file__).resolve().parents[1] / "config" / "market_reference.json"


class MarketReferenceError(ValueError):
    """Raised when the packaged reference snapshot is missing or malformed."""


def load_market_reference(path: Path | str = REFERENCE_PATH) -> dict[str, Any]:
    """Load and validate the dated market reference without network access."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError("schema_version must be 1")
        stamp = payload.get("retrieved_on")
        if not isinstance(stamp, str) or date.fromisoformat(stamp).isoformat() != stamp:
            raise ValueError("reference date must be an ISO calendar date")
        indicators = payload["indicators"]
        for key in ("annual_return_rate", "annual_inflation_rate"):
            item = indicators[key]
            value = item["value"]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{key} must be finite")
            if not 0 <= float(value) <= 0.15:
                raise ValueError(f"{key} is outside the educational range")
            for text_key in ("label", "source", "source_url", "reference_period"):
                if not isinstance(item.get(text_key), str) or not item[text_key].strip():
                    raise ValueError(f"{key}.{text_key} is required")
        return deepcopy(payload)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise MarketReferenceError(f"Không đọc được bộ chỉ số tham chiếu: {exc}") from exc


def reference_assumptions(path: Path | str = REFERENCE_PATH) -> dict[str, float]:
    """Return engine-ready annual decimal assumptions from the snapshot."""

    indicators = load_market_reference(path)["indicators"]
    return {
        "annual_return_rate": float(indicators["annual_return_rate"]["value"]),
        "annual_inflation_rate": float(indicators["annual_inflation_rate"]["value"]),
    }


__all__ = [
    "MarketReferenceError",
    "REFERENCE_PATH",
    "load_market_reference",
    "reference_assumptions",
]
