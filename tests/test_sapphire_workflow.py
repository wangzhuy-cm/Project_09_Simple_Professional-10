"""Regression tests for the Electric Sapphire rebuild. No live API calls."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path

import pytest
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from src import llm_explanation, llm_extraction
from src.market_reference import load_market_reference, MarketReferenceError
from src.report_generator import generate_report, _clean_explanation_lines
from src.report_preview import render_pdf_page
from src.presentation import what_if_change_lines
from ui.report_page import _format_explanation_for_display

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/test_cases.json").read_text(encoding="utf-8"))["cases"]


def plan_app():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=25).run()
    at.session_state["profile_draft"] = deepcopy(CASES[0]["expected_profile"])
    at.button(key="p09_nav_2. Xác nhận").click().run()
    at.checkbox(key="person4_profile_confirmed").check().run()
    at.button(key="p09_review_next").click().run()
    assert not at.exception
    return at


def test_changed_assumptions_allow_preview_but_require_explicit_confirmation():
    at = plan_app()
    assert at.button(key="p09_scenario_next").disabled
    at.checkbox(key="person3_assumptions_confirmed").check().run()
    assert not at.button(key="p09_scenario_next").disabled
    at.number_input(key="person3_inflation").set_value(3.0).run()
    assert not at.exception
    assert not at.checkbox(key="person3_assumptions_confirmed").value
    assert at.session_state["integrated_scenario_bundle"]["assumptions"]["annual_inflation_rate"] == .03
    assert at.button(key="p09_scenario_next").disabled
    at.button(key="p09_nav_4. Báo cáo").click().run()
    assert not at.exception
    assert not any(b.key == "person5_create_pdf" for b in at.button)


def test_back_navigation_preserves_profile_and_selected_scenario():
    at = plan_app()
    at.radio(key="person3_scenario_focus").set_value("optimistic").run()
    at.checkbox(key="person3_assumptions_confirmed").check().run()
    at.button(key="p09_scenario_next").click().run()
    at.button(key="p09_report_back_review").click().run()
    assert not at.exception
    assert at.checkbox(key="person4_profile_confirmed").value
    at.button(key="p09_review_next").click().run()
    assert not at.exception
    assert at.radio(key="person3_scenario_focus").value == "optimistic"
    assert at.checkbox(key="person3_assumptions_confirmed").value


def test_editing_review_after_a_plan_invalidates_report():
    at = plan_app()
    at.checkbox(key="person3_assumptions_confirmed").check().run()
    at.button(key="p09_back_review").click().run()
    at.text_input(key="person4_goal_amount").set_value("150000000").run()
    assert not at.exception
    assert at.session_state["integrated_review_bundle"] is None
    assert "integrated_scenario_bundle" not in at.session_state
    assert not at.checkbox(key="person4_profile_confirmed").value


def test_partial_income_is_not_presented_as_complete_sum():
    p = deepcopy(CASES[0]["expected_profile"])
    p["monthly_other_income"] = None
    def app(profile):
        from ui.review_page import render_review_page
        render_review_page(profile, {"annual_return_rate": 0.0})
    at = AppTest.from_function(app, args=(p,)).run()
    summary = next(m.value for m in at.markdown if "p09-review-summary" in m.value)
    assert "Tổng thu nhập</span><strong>Chưa đủ dữ liệu" in summary
    assert at.checkbox(key="person4_profile_confirmed").disabled


def test_return_to_profile_prefills_latest_review_edits():
    at = plan_app()
    at.button(key="p09_back_review").click().run()
    at.text_input(key="person4_goal_amount").set_value("160000000").run()
    at.button(key="p09_back_profile").click().run()
    assert not at.exception
    assert at.text_input(key="profile_input_goal_amount").value == "160000000"


@pytest.mark.parametrize("scenario,color", [("conservative", "#94A3B8"), ("base", "#06B6D4"), ("optimistic", "#8B5CF6")])
def test_selected_scenario_chart_has_its_own_color_and_values(scenario, color):
    from src.scenarios import build_scenarios
    from src.charts import create_scenario_detail_chart, create_cashflow_chart, create_goal_progress_chart
    item = build_scenarios(CASES[0]["expected_profile"], {"annual_return_rate": 0.0})[scenario]
    chart = create_scenario_detail_chart(item)
    assert chart.data[0].line.color == color
    assert chart.data[0].y[-1] == item["calculation_result"]["fv_total"]
    assert item["label"] in create_cashflow_chart(item).layout.title.text
    assert item["label"] in create_goal_progress_chart(item).data[0].title.text


def test_offline_explanation_never_looks_up_or_calls_provider(monkeypatch):
    payload = json.loads((ROOT / "tests/fixtures/p019_person5_demo.json").read_text(encoding="utf-8"))
    def forbidden(*args, **kwargs):
        raise AssertionError("offline must not call provider or read credentials")
    monkeypatch.setattr(llm_explanation, "_settings", forbidden)
    monkeypatch.setattr(llm_explanation, "_request_commentary", forbidden)
    result = llm_explanation.generate_explanation_result(payload["profile"], payload["calculation_result"],
        payload["scenario_result"], payload["validation_result"], use_llm=False)
    assert result["mode"] == "offline"
    assert not result["llm_attempted"]


def test_offline_profile_ui_labels_fixture_and_preserves_contract():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=25).run()
    at.button(key="p09_nav_1. Hồ sơ").click().run()
    at.radio[0].set_value("Mô tả tự nhiên").run()
    next(b for b in at.button if b.label == "Trích xuất hồ sơ").click().run()
    assert not at.exception
    assert at.session_state["profile_origin"]["mode"] == "demo"
    assert len(at.session_state["profile_draft"]) == 15
    assert any("Hồ sơ mẫu" in m.value for m in at.markdown)


def test_ai_commentary_is_visible_after_warning_section():
    text = "TÓM TẮT HỒ SƠ VÀ DÒNG TIỀN\nTóm tắt.\nGIẢ ĐỊNH VÀ CẢNH BÁO\nLưu ý.\nBÌNH LUẬN AI (ĐỊNH TÍNH)\nGiữ khoảng đệm cho chi phí phát sinh.\nChế độ: AI hỗ trợ."
    assert "Giữ khoảng đệm" in _format_explanation_for_display(text)
    assert any("Giữ khoảng đệm" in s for s in _clean_explanation_lines(text))


@pytest.mark.parametrize("field,quote,value", [
    ("monthly_primary_income", "chi phí thiết yếu 8 triệu", 8e6),
    ("monthly_essential_expense", "lương tháng 8 triệu", 8e6),
    ("monthly_primary_income", "lương 10 triệu và chi phí thiết yếu 8 triệu", 8e6),
    ("current_savings", "quỹ dự phòng 8 triệu", 8e6),
])
def test_matching_number_in_wrong_context_is_rejected(field, quote, value):
    assert not llm_extraction._grounded(field, value, quote)


def test_reference_date_is_validated_not_hardcoded(tmp_path):
    snapshot = load_market_reference()
    snapshot["retrieved_on"] = "2026-10-01"
    target = tmp_path / "reference.json"
    target.write_text(json.dumps(snapshot), encoding="utf-8")
    assert load_market_reference(target)["retrieved_on"] == "2026-10-01"
    snapshot["retrieved_on"] = "2026-02-31"
    target.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(MarketReferenceError):
        load_market_reference(target)


def test_report_clarifies_changes_timing_and_renders_vietnamese(tmp_path):
    p = json.loads((ROOT / "tests/fixtures/p019_person5_demo.json").read_text(encoding="utf-8"))
    result = llm_explanation.generate_explanation_result(p["profile"], p["calculation_result"],
        p["scenario_result"], p["validation_result"], use_llm=False)
    confirmed = {**p, "profile_confirmed": True, "assumptions_confirmed": True, "report_confirmed": True}
    target = tmp_path / "sapphire.pdf"
    generate_report(p["profile"], confirmed, result["text"], str(target))
    pdf = target.read_bytes()
    reader = PdfReader(BytesIO(pdf))
    text = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    assert len(reader.pages) == 3
    assert "cơ sở 22, sau cú sốc 25" in text
    assert "Chậm so với cơ sở: 3 tháng; trễ so với hạn gốc 24 tháng: 1 tháng" in text
    assert "Thu nhập chính:" in text
    assert "chưa gọi LLM" in text
    assert render_pdf_page(pdf, 0).startswith(b"\x89PNG")


def test_what_if_without_changes_does_not_imply_intervention():
    from src.scenarios import run_what_if
    result = run_what_if(CASES[0]["expected_profile"], {"annual_return_rate": 0.0})
    assert what_if_change_lines(result) == ["Chưa thay đổi đầu vào; kết quả bằng phương án cơ sở."]


def test_zero_cashflow_chart_does_not_invent_one_dong():
    from src.scenarios import build_scenarios
    from src.charts import create_cashflow_chart
    profile = deepcopy(CASES[0]["expected_profile"])
    for key in ("monthly_primary_income", "monthly_other_income", "monthly_essential_expense",
                "monthly_discretionary_expense", "monthly_debt_payment"):
        profile[key] = 0
    chart = create_cashflow_chart(build_scenarios(profile, {"annual_return_rate": 0.0})["base"])
    assert "<b>0 ₫</b>" in chart.layout.annotations[0].text
    assert "Không phát sinh" in chart.data[0].hovertemplate


def test_long_vietnamese_goal_exports_without_three_page_rejection(tmp_path):
    from src.scenarios import build_scenarios
    from src.validation import validate_profile
    profile = deepcopy(CASES[0]["expected_profile"])
    profile["goal_name"] = "Kế hoạch học tập nâng cao trình độ và tích lũy tài chính bền vững " * 7
    scenarios = {"scenarios": build_scenarios(profile, {"annual_return_rate": 0.0})}
    calculation = scenarios["scenarios"]["base"]["calculation_result"]
    validation = validate_profile(profile, {"annual_return_rate": 0.0})
    result = llm_explanation.generate_explanation_result(profile, calculation, scenarios, validation, use_llm=False)
    generate_report(profile, {"calculation_result": calculation, "scenario_result": scenarios,
        "validation_result": validation, "profile_confirmed": True, "assumptions_confirmed": True,
        "report_confirmed": True}, result["text"], str(tmp_path / "long.pdf"))
    assert len(PdfReader(tmp_path / "long.pdf").pages) >= 3
