"""Minimal Streamlit cash-flow page for Project 09 (Person 2).

No styling/dashboard work is included at this stage.  The page is a thin UI
adapter around ``calculate_financial_metrics`` and intentionally does not own
validation, scenarios, charts, LLM explanation, or report generation.
"""

from __future__ import annotations

from typing import Any

from src.calculations import CalculationInputError, calculate_financial_metrics
from ui.theme import money, percent


def _vnd(value: float | None) -> str:
    return money(value)


def render_cashflow_page(profile: dict, assumptions: dict) -> dict[str, Any] | None:
    """Render Person 2's core cash-flow metrics in Streamlit.

    Args:
        profile: FinancialProfile-compatible dictionary already reviewed by the
            upstream validation workflow.
        assumptions: Calculation assumptions accepted by
            ``calculate_financial_metrics``.

    Returns:
        Calculation result dictionary when successful, otherwise ``None``.

    Raises:
        No expected application-level exception.  Calculation input errors are
        displayed in the UI and converted to ``None`` so the app can continue.
    """

    import streamlit as st

    st.header("Dòng tiền và mục tiêu")
    st.caption("Các chỉ số được tính từ đúng thông tin bạn đã xác nhận.")

    try:
        result = calculate_financial_metrics(profile, assumptions)
    except (CalculationInputError, TypeError) as exc:
        st.error(f"Chưa thể tính toán: {exc}")
        return None

    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng thu nhập / tháng", _vnd(result["total_monthly_income"]), help="Thu nhập chính cộng thu nhập phụ.")
    col2.metric("Tổng chi / tháng", _vnd(result["total_monthly_outflow"]), help="Chi thiết yếu, không thiết yếu và trả nợ.")
    col3.metric("Dòng tiền dư / tháng", _vnd(result["monthly_surplus"]), help="Thu nhập trừ toàn bộ chi phí.")

    col4, col5, col6 = st.columns(3)
    savings_rate = result["savings_rate"]
    col4.metric("Tỷ lệ tiết kiệm", percent(savings_rate))
    col5.metric("Vốn ban đầu khả dụng", _vnd(result["initial_available_amount"]), help="Tiền tiết kiệm còn lại sau khi giữ riêng quỹ dự phòng.")
    col6.metric("Đóng góp / tháng", _vnd(result["monthly_contribution"]))

    st.subheader("Kết quả và khả năng chi trả")
    st.table({"Chỉ tiêu": ["Giá trị cuối kỳ từ vốn ban đầu", "Giá trị cuối kỳ từ đóng góp",
                            "Khoản đóng góp tối thiểu cần thiết", "Phần đóng góp hiện tại vượt dòng tiền",
                            "Phần đóng góp cần thiết vượt dòng tiền"],
              "Giá trị": [_vnd(result["fv_initial"]), _vnd(result["fv_contribution"]),
                          _vnd(result["required_monthly_contribution"]),
                          _vnd(result["contribution_affordability_gap"]),
                          _vnd(result["required_contribution_gap"])]})
    if result["required_contribution_gap"] > 0:
        st.warning("Để đạt mục tiêu đúng hạn, khoản đóng góp cần thiết vượt dòng tiền dư "
                   f"{_vnd(result['required_contribution_gap'])} mỗi tháng. Hãy xem lại mục tiêu, thời hạn hoặc dòng tiền.")
    if result["contribution_affordability_gap"] > 0:
        st.warning("Đóng góp đang mô phỏng vượt dòng tiền dư "
                   f"{_vnd(result['contribution_affordability_gap'])} mỗi tháng; kết quả toán học chưa chứng minh có thể chi trả.")

    if result["calculation_warnings"]:
        st.warning("Kế hoạch có điểm cần lưu ý: " + ", ".join(result["calculation_warnings"]))

    with st.expander("Cách tính và giả định đã áp dụng"):
        assumptions_used = result["assumptions_used"]
        st.markdown(
            "- Khoản đóng góp được ghi nhận **cuối mỗi tháng**.\n"
            "- Lợi suất năm được quy đổi sang **lợi suất hiệu dụng theo tháng**.\n"
            f"- Điều chỉnh theo lạm phát: **{'Có' if assumptions_used['inflation_enabled'] else 'Không'}**.\n"
            "- Thuế và phí: **chưa được tính trong mô phỏng**."
        )

    return result


__all__ = ["render_cashflow_page"]
