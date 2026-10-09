"""Review regressions: no API use, no invented resources, fresh confirmation."""
from copy import deepcopy
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src import llm_extraction

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / "data/example_profile_valid.json").read_text())


def _review(profile):
    from ui.review_page import render_review_page
    render_review_page(profile, {"annual_return_rate": 0.0})


def _goal_table(at):
    return next(table.value for table in at.dataframe
                if "Thông tin từ hồ sơ và kiểm tra" in table.value.columns)


def test_review_table_never_calls_provider_and_edit_requires_new_confirmation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Review must not call an LLM")
    monkeypatch.setattr(llm_extraction, "_request_structured", forbidden)
    at = AppTest.from_function(_review, args=(deepcopy(PROFILE),)).run()
    assert not at.exception
    assert not any("Python" in c.value or "bằng chứng LLM" in c.value for c in at.caption)
    at.checkbox(key="person4_profile_confirmed").check().run()
    assert at.session_state["person4_result"] is not None
    at.text_input(key="person4_goal_amount").set_value("150000000").run()
    assert not at.exception
    assert "150.000.000" in _goal_table(at).iloc[0, 1]
    assert not at.checkbox(key="person4_profile_confirmed").value
    assert at.session_state["person4_result"] is None


def test_partial_income_requires_question_and_is_not_presented_as_zero():
    profile = deepcopy(PROFILE)
    profile["monthly_other_income"] = None
    at = AppTest.from_function(_review, args=(profile,)).run()
    assert not at.exception
    rows = _goal_table(at).set_index("Nội dung").iloc[:, 0]
    assert "Chưa đủ dữ liệu" in rows["Dòng tiền hằng tháng"]
    assert "thu nhập phụ" in rows["Thông tin cần bổ sung"]
    assert at.checkbox(key="person4_profile_confirmed").disabled


def test_negative_cashflow_is_a_shortfall_and_keeps_existing_warning_policy():
    profile = deepcopy(PROFILE)
    profile["monthly_primary_income"] = 1000000
    profile["monthly_other_income"] = 0
    profile["monthly_essential_expense"] = 2000000
    profile["monthly_discretionary_expense"] = 0
    profile["monthly_debt_payment"] = 0
    at = AppTest.from_function(_review, args=(profile,)).run()
    assert not at.exception
    rows = _goal_table(at).set_index("Nội dung").iloc[:, 0]
    assert "Thiếu 1.000.000" in rows["Dòng tiền hằng tháng"]
    assert any("chi" in w.value.lower() and "thu" in w.value.lower() for w in at.warning)
    assert not at.checkbox(key="person4_profile_confirmed").disabled
