"""Read-only, shared descriptions of scenario changes and provenance."""
LABELS = {
    "monthly_primary_income": "Thu nhập chính", "monthly_other_income": "Thu nhập phụ",
    "monthly_essential_expense": "Chi phí thiết yếu", "monthly_discretionary_expense": "Chi phí linh hoạt",
    "monthly_debt_payment": "Trả nợ", "current_savings": "Tiết kiệm",
    "emergency_fund_reserved": "Quỹ dự phòng", "goal_amount": "Giá trị mục tiêu",
    "goal_horizon_months": "Thời hạn", "monthly_contribution": "Khoản góp mỗi tháng",
    "annual_return_rate": "Lợi suất", "annual_inflation_rate": "Lạm phát",
    "max_projection_months": "Giới hạn dự phóng",
}


def what_if_change_lines(what_if: dict) -> list[str]:
    lines = []
    def display(key, value):
        if value is None:
            return "tự động theo dòng tiền còn lại"
        if key.endswith("months"):
            return f"{int(value)} tháng"
        if key.endswith("rate"):
            return f"{value * 100:.2f}%/năm".replace(".", ",")
        unit = " VND/tháng" if key.startswith("monthly_") else " VND"
        return f"{value:,.0f}".replace(",", ".") + unit
    for section, changes in what_if.get("changes", {}).items():
        source_key = "profile_used" if section == "profile_updates" else "assumptions"
        before = what_if["baseline"].get(source_key, {})
        after = what_if["modified"].get(source_key, {})
        for key in changes:
            if before.get(key) != after.get(key):
                lines.append(f"{LABELS.get(key, key)}: {display(key, before.get(key))} → {display(key, after.get(key))}.")
    return lines or ["Chưa thay đổi đầu vào; kết quả bằng phương án cơ sở."]


def explanation_mode_label(text: str) -> str:
    if "BÌNH LUẬN AI (ĐỊNH TÍNH)" in text:
        return "AI hỗ trợ nhận xét định tính; số liệu do Python tính."
    if "phản hồi AI không khả dụng" in text:
        return "AI chưa khả dụng hoặc chưa qua kiểm tra; dùng diễn giải từ Python."
    return "Diễn giải ngoại tuyến từ Python; chưa gọi LLM."
