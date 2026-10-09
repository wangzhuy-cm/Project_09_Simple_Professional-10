from __future__ import annotations

from pathlib import Path

import pytest

streamlit = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

def load_p001() -> dict:
    return {
        "user_id": "P001",
        "monthly_primary_income": 8_000_000.0,
        "monthly_other_income": 2_000_000.0,
        "monthly_essential_expense": 5_000_000.0,
        "monthly_discretionary_expense": 2_000_000.0,
        "monthly_debt_payment": 0.0,
        "current_savings": 15_000_000.0,
        "emergency_fund_reserved": 5_000_000.0,
        "goal_name": "Higher education",
        "goal_amount": 100_000_000.0,
        "goal_horizon_months": 36,
        "risk_tolerance": "low",
        "liquidity_need": "medium",
        "expected_income_growth": 0.05,
        "notes": None,
    }


def test_cashflow_page_smoke(tmp_path: Path) -> None:
    profile = load_p001()
    app_file = tmp_path / "cashflow_smoke_app.py"
    app_file.write_text(
        "from ui.cashflow_page import render_cashflow_page\n"
        f"profile = {profile!r}\n"
        "render_cashflow_page(profile, {'annual_return_rate': 0.0})\n",
        encoding="utf-8",
    )

    at = AppTest.from_file(str(app_file)).run()
    assert not at.exception
    assert len(at.header) == 1
    assert len(at.metric) == 6
    assert len(at.warning) == 0
