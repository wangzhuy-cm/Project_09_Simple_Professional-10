"""Person 4: deterministic profile/assumption checks and clarification questions.

Reuse Person 1's schema and Person 2's public engine; read Person 3's limits
without changing them. This module makes no network calls and produces no plan.
An optional engine call supplies feasibility diagnostics only, after all input
checks pass. The UI must still obtain profile AND assumption confirmation.

``assumptions=None`` selects profile-only review: status concerns the profile,
and ``can_simulate`` is False. Supply an assumptions dict for a readiness check.
No missing FinancialProfile value is replaced with zero or another default.
"""

from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import re
import unicodedata

from pydantic import ValidationError

from src.calculations import calculate_financial_metrics
from src.schemas import parse_financial_profile


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "scenario_defaults.json"
MONEY_FIELDS = (
    "monthly_primary_income", "monthly_other_income", "monthly_essential_expense",
    "monthly_discretionary_expense", "monthly_debt_payment", "current_savings",
    "emergency_fund_reserved", "goal_amount",
)
REQUIRED_FIELDS = MONEY_FIELDS + (
    "goal_name", "goal_horizon_months", "risk_tolerance", "liquidity_need",
)
ASSUMPTION_KEYS = frozenset({
    "annual_return_rate", "annual_inflation_rate", "monthly_contribution",
    "max_projection_months",
})
LABELS = {
    "monthly_primary_income": "thu nhập chính hằng tháng",
    "monthly_other_income": "thu nhập phụ hằng tháng",
    "monthly_essential_expense": "chi phí thiết yếu hằng tháng",
    "monthly_discretionary_expense": "chi phí không thiết yếu hằng tháng",
    "monthly_debt_payment": "khoản trả nợ hằng tháng",
    "current_savings": "tiền tiết kiệm hiện có",
    "emergency_fund_reserved": "quỹ dự phòng cần giữ lại",
    "goal_name": "tên một mục tiêu chính",
    "goal_amount": "số tiền mục tiêu",
    "goal_horizon_months": "thời hạn mục tiêu (số tháng nguyên từ 1 đến 120)",
    "risk_tolerance": "mức chấp nhận rủi ro (thấp, trung bình hoặc cao)",
    "liquidity_need": "nhu cầu rút tiền sớm (thấp, trung bình hoặc cao)",
    "assumptions.annual_return_rate": "lợi suất giả định theo năm, dạng thập phân",
}
HUMAN_REVIEW_CODES = frozenset({
    "unreadable_profile", "human_review_requested", "config_unavailable",
    "numeric_range_exceeded", "calculation_unavailable", "investment_intent_unclear",
})
ENGINE_WARNINGS = {
    "emergency_fund_reserved_exceeds_current_savings": (
        "emergency_fund_reserved", "Quỹ dự phòng mong muốn lớn hơn tiền hiện có; chưa đủ dự phòng."),
    "negative_monthly_cash_flow": (
        "monthly_essential_expense", "Chi phí và trả nợ vượt thu nhập. Cần điều chỉnh hoặc xác định nguồn bù thiếu hụt."),
    "monthly_contribution_exceeds_current_surplus": (
        "assumptions.monthly_contribution", "Khoản đóng góp giả định vượt dòng tiền dư; mô phỏng này cần nguồn tài trợ bổ sung."),
    "required_monthly_contribution_exceeds_current_surplus": (
        "goal_amount", "Khoản đóng góp cần thiết vượt khả năng dòng tiền hiện tại."),
    "goal_already_funded_from_available_savings": (
        "goal_amount", "Tiền khả dụng sau khi giữ quỹ dự phòng đã đủ mục tiêu hiện tại; vẫn cần kiểm tra giả định."),
    "goal_not_reached_within_projection_limit": (
        "goal_horizon_months", "Chưa đạt mục tiêu trong khoảng thời gian dự phóng."),
    "savings_rate_unavailable_zero_income": (
        "monthly_primary_income", "Không thể xác định tỷ lệ tiết kiệm khi tổng thu nhập bằng không."),
}


class _Review:
    """Collect JSON-safe issues without including raw provider/user payloads."""

    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.missing_fields: list[str] = []
        self.questions: list[str] = []

    def error(self, code, field, message, question=None, *, missing=False):
        issue = {"code": code, "field": field, "message": message}
        if issue not in self.errors:
            self.errors.append(issue)
        if missing and field not in self.missing_fields:
            self.missing_fields.append(field)
        if question and question not in self.questions:
            self.questions.append(question)

    def warning(self, code, field, message):
        if not any(item["code"] == code for item in self.warnings):
            self.warnings.append({"code": code, "field": field, "message": message})

    def result(self, assumptions_checked=False):
        codes = {item["code"] for item in self.errors}
        if "out_of_scope_request" in codes:
            status = "OUT_OF_SCOPE"
        elif codes & HUMAN_REVIEW_CODES:
            status = "HUMAN_REVIEW_REQUIRED"
        elif self.errors:
            status = "NEEDS_CLARIFICATION"
        elif self.warnings:
            status = "WARNING"
        else:
            status = "VALID"
        return {
            "status": status,
            "errors": deepcopy(self.errors),
            "warnings": deepcopy(self.warnings),
            "missing_fields": list(self.missing_fields),
            "clarification_questions": list(self.questions),
            "can_simulate": assumptions_checked and status in {"VALID", "WARNING"},
        }


def _normalise_text(text):
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def _nonrequest_prefix(prefix):
    """Recognize explicit nearby negation/history, without claiming full NLP."""
    negated = re.search(
        r"\bkhong(?:\s+(?:can|muon|yeu cau|de nghi|co y dinh))?"
        r"(?:\s+(?:loi khuyen|tu van|khuyen nghi))?(?:\s+duoc)?\s*$", prefix
    )
    historical = re.search(r"\b(?:da|tung)\s*$", prefix)
    return bool(negated or historical)


def _scope_checks(profile, review):
    """Screen explicit requests only; this is not a general NLP classifier.

Stage 2 extraction must preserve relevant user intent in goal_name/notes.
Unknown or paraphrased intent still needs LLM/human review, not keyword claims.
"""
    investment = re.compile(
        r"\b(?:(?:khuyen nghi|tu van|nen|goi y)\s+)?(?:mua|ban|dau tu)\s+"
        r"(?:(?:ngay|vao|cac|mot)\s+)*(?:co phieu|trai phieu|chung chi quy|"
        r"bitcoin|btc|ethereum|crypto|tien ma hoa)\b"
    )
    guarantee = re.compile(r"\b(?:bao dam|dam bao|cam ket)\s+(?:loi nhuan|sinh loi|lai)\b")
    for field in ("goal_name", "notes"):
        value = profile.get(field)
        if not isinstance(value, str):
            continue
        for sentence in re.split(r"[.!?;\n]+", value):
            text = _normalise_text(sentence)
            for pattern in (investment, guarantee):
                for match in pattern.finditer(text):
                    prefix = text[:match.start()]
                    if not _nonrequest_prefix(prefix):
                        review.error(
                            "out_of_scope_request", field,
                            "Yêu cầu mua/bán sản phẩm tài chính hoặc bảo đảm lợi nhuận nằm ngoài phạm vi của công cụ này.",
                            "Bạn có muốn chuyển sang lập một mục tiêu tiết kiệm tổng quát, không kèm khuyến nghị sản phẩm hay bảo đảm lợi nhuận không?",
                        )
            # A short uppercase identifier is not proof of a stock ticker.
            # In a buy/sell-for-profit request, ask for review instead of either
            # silently allowing the request or inventing an asset classification.
            trade_request = re.search(
                r"\b(?:nen|khuyen nghi|tu van|goi y|hay)\b.{0,60}\b(?:mua|ban)\b", text
            )
            short_identifier = re.search(r"(?<!\w)[A-Z][A-Z0-9]{1,9}(?!\w)", sentence)
            profit_context = re.search(r"\b(?:lai nhanh|loi nhuan|sinh loi)\b", text)
            already_out_of_scope = any(
                issue["code"] == "out_of_scope_request" and issue["field"] == field
                for issue in review.errors
            )
            if (trade_request and short_identifier and profit_context
                    and not _nonrequest_prefix(text[:trade_request.start()])
                    and not already_out_of_scope):
                review.error(
                    "investment_intent_unclear", field,
                    "Có yêu cầu mua/bán để sinh lời nhưng chưa rõ sản phẩm được nhắc tới.",
                    "Bạn đang yêu cầu khuyến nghị sản phẩm đầu tư hay chỉ muốn lập mục tiêu tiết kiệm tổng quát?",
                )
            if re.search(r"\b(?:hai|2|nhieu) muc tieu\b|chua chon muc tieu chinh", text):
                review.error("multiple_goals", "goal_name", "Mỗi lần lập kế hoạch chỉ hỗ trợ một mục tiêu chính.",
                             "Bạn muốn chọn một mục tiêu chính nào cho lần lập kế hoạch này?")
            if re.search(r"khong du can cu|khong the hieu|can con nguoi kiem tra|can human review", text):
                review.error("human_review_requested", field, "Nội dung cần người dùng kiểm tra lại.",
                             "Bạn hãy kiểm tra và viết lại thông tin chưa rõ hoặc nhập bằng form.")


def _profile_checks(profile, review):
    for field in REQUIRED_FIELDS:
        value = profile.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            label = LABELS.get(field, field)
            question = f"Bạn vui lòng cung cấp {label}."
            if field in MONEY_FIELDS and field != "goal_amount":
                question = f"Bạn vui lòng cung cấp {label}; chỉ nhập 0 nếu thực sự bằng 0."
            elif field == "goal_amount":
                question = "Bạn muốn đạt số tiền mục tiêu bao nhiêu VND (phải lớn hơn 0)?"
            review.error("missing_required_field", field, f"Chưa có {label}.",
                         question, missing=True)
    try:
        p = parse_financial_profile(profile).to_profile_dict()
    except ValidationError as exc:
        for issue in exc.errors(include_input=False, include_url=False):
            field = ".".join(str(part) for part in issue["loc"]) or "profile"
            if issue["type"] == "missing" and field in review.missing_fields:
                continue
            if issue["type"] == "missing":
                review.error("missing_schema_key", field, "Hồ sơ đang thiếu một mục thông tin cần thiết.",
                             f"Hãy bổ sung {LABELS.get(field, field)}.", missing=True)
            else:
                review.error("invalid_profile_field", field, "Thông tin đã nhập chưa đúng định dạng hoặc giới hạn cho phép.",
                             f"Bạn hãy kiểm tra lại {LABELS.get(field, field)}.")
        return None
    except (TypeError, ValueError, ArithmeticError):
        review.error("invalid_profile_value", "profile", "Không thể đọc một hoặc nhiều giá trị trong hồ sơ.",
                     "Bạn hãy kiểm tra định dạng và độ lớn các giá trị đã nhập.")
        return None

    for field in MONEY_FIELDS:
        value = p[field]
        if value is not None and (value < 0 or (field == "goal_amount" and value == 0)):
            rule = "phải lớn hơn 0" if field == "goal_amount" else "không được âm"
            review.error("invalid_money_value", field, f"{LABELS[field].capitalize()} {rule}.",
                         f"Bạn vui lòng kiểm tra lại {LABELS[field]}.")
    horizon = p["goal_horizon_months"]
    if horizon is not None and not 1 <= horizon <= 120:
        review.error("invalid_goal_horizon", "goal_horizon_months", "Thời hạn phải từ 1 đến 120 tháng.",
                     "Bạn muốn thực hiện mục tiêu trong bao nhiêu tháng (1–120)?")

    if all(p[f] is not None and p[f] >= 0 for f in MONEY_FIELDS[:5]):
        income = p["monthly_primary_income"] + p["monthly_other_income"]
        outflow = p["monthly_essential_expense"] + p["monthly_discretionary_expense"] + p["monthly_debt_payment"]
        if not math.isfinite(income) or not math.isfinite(outflow):
            review.error("numeric_range_exceeded", "profile", "Tổng dòng tiền vượt giới hạn số hữu hạn.",
                         "Bạn hãy kiểm tra đơn vị VND và độ lớn số liệu.")
        elif income <= 0:
            review.error("non_positive_total_income", "monthly_primary_income", "Tổng thu nhập phải lớn hơn 0.",
                         "Bạn vui lòng bổ sung nguồn thu nhập hằng tháng lớn hơn 0.")
        elif outflow > income:
            field, message = ENGINE_WARNINGS["negative_monthly_cash_flow"]
            review.warning("negative_monthly_cash_flow", field, message)
    savings, reserved = p["current_savings"], p["emergency_fund_reserved"]
    if savings is not None and reserved is not None and 0 <= savings < reserved:
        field, message = ENGINE_WARNINGS["emergency_fund_reserved_exceeds_current_savings"]
        review.warning("emergency_fund_reserved_exceeds_current_savings", field, message)
    return p


def _finite_number(value):
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except (OverflowError, ValueError, TypeError):
        return False


def _load_limits():
    """Read only; validate limits needed here without inventing a fallback cap."""
    limits = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))["limits"]
    minimum = limits["min_annual_return_rate"]
    if not _finite_number(minimum) or minimum <= -1:
        raise ValueError("invalid minimum return")
    for risk in ("low", "medium", "high"):
        cap = limits["max_annual_return_rate_by_risk"][risk]
        if not _finite_number(cap) or cap < minimum:
            raise ValueError("invalid return cap")
    low, high = limits["min_annual_inflation_rate"], limits["max_annual_inflation_rate"]
    if not _finite_number(low) or not _finite_number(high) or not 0 <= low <= high:
        raise ValueError("invalid inflation bounds")
    maximum = limits["max_projection_months"]
    if isinstance(maximum, bool) or not isinstance(maximum, int) or not 120 <= maximum <= 1200:
        raise ValueError("invalid projection limit")
    return limits


def _assumption_checks(assumptions, profile, review):
    if not isinstance(assumptions, dict):
        review.error("invalid_assumptions", "assumptions", "Các giả định hiện tại không đúng định dạng.",
                     "Bạn hãy nhập lại các giả định hoặc khôi phục thiết lập ban đầu.")
        return
    for key in assumptions:
        if key not in ASSUMPTION_KEYS:
            review.error("unknown_assumption", f"assumptions.{key}", "Giả định này chưa được hỗ trợ.",
                         "Bạn hãy khôi phục thiết lập ban đầu và thử lại.")
    try:
        limits = _load_limits()
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError):
        review.error("config_unavailable", "assumptions", "Không thể tải thiết lập mô phỏng.",
                     "Hãy khởi động lại ứng dụng hoặc liên hệ người phụ trách hệ thống.")
        return

    for key in ("annual_return_rate", "annual_inflation_rate", "monthly_contribution"):
        if key == "monthly_contribution" and key not in assumptions:
            continue  # Person 2's automatic-contribution sentinel.
        # Validate effective engine defaults as well: a changed Person 3 config
        # must not let a default pass here and then fail in prepare_inputs.
        value = assumptions.get(key, 0.0 if key == "annual_inflation_rate" else None)
        field = f"assumptions.{key}"
        if key == "monthly_contribution" and value is None:
            continue  # Explicit engine sentinel: automatic contribution.
        if key == "annual_return_rate" and value is None:
            review.error("missing_annual_return_rate", field, "Chưa cung cấp lợi suất giả định theo năm.",
                         "Bạn muốn dùng lợi suất giả định bao nhiêu mỗi năm? Dùng số thập phân; 0 nghĩa là chủ động giả định không có lợi suất.", missing=True)
            continue
        if not _finite_number(value):
            review.error("invalid_assumption_number", field, "Giả định phải là số hữu hạn, không dùng chuỗi hoặc bool.",
                         f"Bạn hãy kiểm tra lại {key} và nhập bằng số.")
            continue
        if key == "annual_return_rate":
            cap = limits["max_annual_return_rate_by_risk"].get(profile["risk_tolerance"])
            outside = value < limits["min_annual_return_rate"] or (cap is not None and value > cap)
        elif key == "annual_inflation_rate":
            outside = not limits["min_annual_inflation_rate"] <= value <= limits["max_annual_inflation_rate"]
        else:
            outside = value < 0
        if outside:
            review.error("assumption_out_of_range", field, "Giả định vượt giới hạn mô phỏng đã thống nhất hoặc không phù hợp mức rủi ro.",
                         "Bạn hãy điều chỉnh lại giá trị hoặc khôi phục thiết lập ban đầu.")
    maximum = assumptions.get("max_projection_months", 1200)  # documented engine default
    horizon = profile["goal_horizon_months"]
    if (isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1
            or maximum > limits["max_projection_months"]
            or (horizon is not None and maximum < horizon)):
        review.error("invalid_projection_limit", "assumptions.max_projection_months",
                     "Giới hạn dự phóng phải là số nguyên, không nhỏ hơn thời hạn và không vượt giới hạn cấu hình.",
                     "Bạn hãy kiểm tra max_projection_months; đây không phải thời hạn mục tiêu.")


def _feasibility_checks(profile, assumptions, review):
    try:
        result = calculate_financial_metrics(deepcopy(profile), deepcopy(assumptions))
        for key in ("total_monthly_income", "total_monthly_outflow", "monthly_surplus",
                    "initial_available_amount", "fv_total", "adjusted_goal_amount", "goal_gap",
                    "required_monthly_contribution", "contribution_affordability_gap", "required_contribution_gap"):
            if not _finite_number(result[key]):
                raise ValueError("non-finite engine result")
        codes = result["calculation_warnings"]
        if not isinstance(codes, list) or any(not isinstance(code, str) for code in codes):
            raise ValueError("invalid engine warnings")
        for code in codes:
            field, message = ENGINE_WARNINGS.get(code, ("profile", "Kế hoạch có một điểm cần được kiểm tra thêm."))
            review.warning(code, field, message)
        if result["goal_gap"] > 0:
            review.warning("goal_not_reached_by_horizon", "goal_amount",
                           "Kế hoạch hiện tại chưa đủ tiền tại thời hạn mục tiêu theo các giả định đã chọn.")
    except Exception:
        # Dependency failures must not crash UI or expose a raw exception payload.
        review.error("calculation_unavailable", "assumptions", "Tạm thời chưa thể kiểm tra tính khả thi của kế hoạch.",
                     "Hãy kiểm tra lại dữ liệu hoặc thử khởi động lại ứng dụng.")


def validate_profile(profile: dict, assumptions: dict | None = None) -> dict:
    """Validate the shared profile and optionally check simulation readiness.

    Args:
        profile: Person 1's exact 15-key FinancialProfile. Unknown optional
            user_id, notes and expected_income_growth may remain None. All cash
            amounts, the main goal, risk and liquidity must be supplied.
        assumptions: None for profile-only review; otherwise engine assumptions
            with explicit annual_return_rate and Person 2's optional keys.
            Annual decimal rates are checked against Person 3's config.

    Returns:
        A fresh JSON-safe dict with status, errors, warnings, missing_fields,
        clarification_questions and can_simulate. Each issue contains code,
        field and a Vietnamese message. Status priority: OUT_OF_SCOPE >
        HUMAN_REVIEW_REQUIRED > NEEDS_CLARIFICATION > WARNING > VALID.
        can_simulate is data/assumption readiness, NOT human confirmation or
        permission to generate a final report. It is always False in profile-
        only mode. Missing assumption names use the 'assumptions.' prefix.

    Errors:
        Malformed input returns NEEDS_CLARIFICATION (unreadable root profiles
        return HUMAN_REVIEW_REQUIRED). Missing/invalid config and failed engine
        diagnostics return HUMAN_REVIEW_REQUIRED. No expected input/dependency
        error escapes; imports require the documented dependencies to exist.
        This function never repairs or mutates profile, assumptions or config.
    """
    review = _Review()
    if not isinstance(profile, dict):
        review.error("unreadable_profile", "profile", "Không thể đọc hồ sơ hiện tại.",
                     "Bạn hãy nhập lại thông tin trong biểu mẫu.")
        return review.result()
    _scope_checks(profile, review)
    p = _profile_checks(profile, review)
    if p is None:
        return review.result()
    if assumptions is not None:
        _assumption_checks(assumptions, p, review)
        if not review.errors:
            _feasibility_checks(p, assumptions, review)
    return review.result(assumptions_checked=assumptions is not None)


__all__ = ["validate_profile"]
