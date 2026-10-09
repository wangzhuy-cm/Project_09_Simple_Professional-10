"""Offline review of the main goal using supplied profile and validation only.

This is a Python presentation helper, not a language-model decomposition.
It neither calls a provider nor changes the profile or simulation formulas.
"""
from __future__ import annotations

import math


def _amount(value) -> str:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0):
        return "Chưa đủ dữ liệu hợp lệ"
    return f"{value:,.0f}".replace(",", ".") + " ₫"


def _sum_fields(profile: dict, fields: tuple[str, ...]) -> float | None:
    values = [profile.get(field) for field in fields]
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not math.isfinite(v) or v < 0 for v in values):
        return None
    total = sum(values)
    return total if math.isfinite(total) else None


def build_goal_review(profile: dict, validation: dict) -> list[dict[str, str]]:
    """Describe known resources without treating missing input as zero.

    The existing validator remains the authority for readiness and questions.
    Unknown/invalid inputs never become an affordable contribution or a result.
    """
    income = _sum_fields(profile, ("monthly_primary_income", "monthly_other_income"))
    outflow = _sum_fields(profile, ("monthly_essential_expense",
                                   "monthly_discretionary_expense", "monthly_debt_payment"))
    surplus = None if income is None or outflow is None else income - outflow
    savings = _sum_fields(profile, ("current_savings",))
    reserve = _sum_fields(profile, ("emergency_fund_reserved",))
    available = None if savings is None or reserve is None else max(0, savings - reserve)
    horizon = profile.get("goal_horizon_months")
    horizon_text = (f"{horizon} tháng" if type(horizon) is int and 1 <= horizon <= 120
                    else "Chưa đủ dữ liệu hợp lệ")
    levels = {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}
    goal = profile.get("goal_name")
    goal_text = goal.strip() if isinstance(goal, str) and goal.strip() else "Chưa xác định"
    if surplus is None or not math.isfinite(surplus):
        flow_text = "Chưa đủ dữ liệu hợp lệ; không tự coi khoản còn thiếu là 0."
    elif surplus < 0:
        flow_text = f"Thiếu {_amount(-surplus)}/tháng; chưa có phần dư từ thu nhập để góp cho mục tiêu."
    else:
        flow_text = f"Còn {_amount(surplus)}/tháng trước khoản góp cho mục tiêu."
    issues = [issue["message"] for key in ("errors", "warnings")
              for issue in validation.get(key, []) if isinstance(issue, dict) and issue.get("message")]
    rows = [
        ("Mục tiêu chính", f"{goal_text} · {_amount(profile.get('goal_amount'))} theo giá hôm nay."),
        ("Thời hạn", horizon_text),
        ("Nguồn lực ban đầu", f"Tiết kiệm {_amount(savings)}; giữ lại quỹ dự phòng {_amount(reserve)}; "
                                f"có thể dùng {_amount(available)} cho mục tiêu."),
        ("Dòng tiền hằng tháng", flow_text),
        ("Ràng buộc khi lập kế hoạch", "Giữ lại quỹ dự phòng; khoản góp không vượt dòng tiền có thể dành. "
                                       "Lợi suất chỉ là giả định, không bảo đảm đạt mục tiêu."),
        ("Rủi ro và thanh khoản", "Mức rủi ro: " + levels.get(profile.get("risk_tolerance"), "Chưa cung cấp")
                                 + "; nhu cầu rút tiền sớm: "
                                 + levels.get(profile.get("liquidity_need"), "Chưa cung cấp")
                                 + ". Nhu cầu rút tiền sớm chỉ được ghi nhận, chưa tác động công thức."),
        ("Điểm cần kiểm tra", " | ".join(dict.fromkeys(issues)) if issues
                             else "Chưa phát hiện lỗi hoặc cảnh báo trong bước kiểm tra này; chưa phải xác nhận của bạn."),
        ("Thông tin cần bổ sung", " | ".join(validation.get("clarification_questions", []))
                                 or "Không có câu hỏi bổ sung từ bộ kiểm tra hiện tại."),
    ]
    return [{"Nội dung": label, "Thông tin từ hồ sơ và kiểm tra": value} for label, value in rows]
