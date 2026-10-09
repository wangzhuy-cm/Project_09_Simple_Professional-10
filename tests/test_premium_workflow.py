"""Presentation smoke tests for fresh state and the explicit reset boundary."""
from pathlib import Path
import json

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_profile_change_discards_every_downstream_bundle():
    at = AppTest.from_file(str(APP)).run()
    assert not at.exception
    at.session_state["profile_draft"] = {"goal_amount": None}
    at.session_state["integrated_review_bundle"] = {"stale": True}
    at.session_state["integrated_scenario_bundle"] = {"stale": True}
    at.session_state["integrated_report_bundle"] = {"stale": True}
    at.run()
    assert not at.exception
    for key in ("integrated_review_bundle", "integrated_scenario_bundle", "integrated_report_bundle"):
        assert key not in at.session_state


def test_report_route_without_confirmation_stays_blocked():
    at = AppTest.from_file(str(APP)).run()
    at.button(key="p09_nav_4. Báo cáo").click().run()
    assert not at.exception
    assert at.warning
    assert "Bước 3" in at.warning[0].value


def test_explicit_reset_clears_project_state():
    at = AppTest.from_file(str(APP)).run()
    at.session_state["profile_draft"] = {"goal_amount": None}
    at.session_state["integrated_review_bundle"] = {"stale": True}
    at.checkbox(key="integrated_reset_confirm").set_value(True).run()
    at.button(key="integrated_reset").click().run()
    assert not at.exception
    assert "profile_draft" not in at.session_state
    assert "integrated_review_bundle" not in at.session_state
    assert at.session_state["integrated_page"] == "Tổng quan"


def test_offline_p001_ui_flow_reaches_current_pdf():
    cases = json.loads((APP.parent / "data" / "test_cases.json").read_text(encoding="utf-8"))["cases"]
    profile = next(case["expected_profile"] for case in cases if case["case_id"] == "P001")
    at = AppTest.from_file(str(APP), default_timeout=25).run()
    at.session_state["profile_draft"] = profile
    at.button(key="p09_nav_2. Xác nhận").click().run()
    at.checkbox(key="person4_profile_confirmed").set_value(True).run()
    assert at.session_state["integrated_review_bundle"]
    at.button(key="p09_nav_3. Mô phỏng").click().run()
    bundle = at.session_state["integrated_scenario_bundle"]
    assert bundle["calculation_result"]["fv_total"] > 0
    assert bundle["assumptions"]["annual_return_rate"] == 0.059
    assert bundle["assumptions"]["annual_inflation_rate"] == 0.0489
    assert not bundle["assumptions_confirmed"]
    at.checkbox(key="person3_assumptions_confirmed").check().run()
    at.button(key="p09_nav_4. Báo cáo").click().run()
    at.button(key="person5_explain").click().run()
    at.checkbox(key="person5_report_confirmed").set_value(True).run()
    at.button(key="person5_create_pdf").click().run()
    assert not at.exception
    assert at.session_state["integrated_report_bundle"]["report_bytes"].startswith(b"%PDF")
