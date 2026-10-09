"""Teacher-facing evidence panel for reproducible system evaluation."""
from __future__ import annotations

import streamlit as st

from src.evaluation_runner import (
    EvaluationRunError,
    comparison_rows,
    evaluate_form_baseline,
    evaluation_csv_bytes,
    run_live_llm_evaluation,
)
from src.llm_extraction import get_openai_status


PREFIX = "evaluation_"


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def render_evaluation_panel() -> None:
    """Show measured baseline and run live metrics only on explicit action."""
    st.markdown('<div class="p09-eval-heading"><span>ĐÁNH GIÁ HỆ THỐNG</span>'
                '<h2>Bằng chứng đo lường, không dùng số minh họa</h2>'
                '<p>Baseline được tính tại máy. Các chỉ số LLM chỉ xuất hiện sau khi '
                'OpenAI thực sự xử lý bộ hồ sơ kiểm thử.</p></div>', unsafe_allow_html=True)
    try:
        baseline = evaluate_form_baseline()
    except (EvaluationRunError, ValueError, TypeError) as exc:
        st.error(f"Không đọc được baseline: {exc}")
        return

    live = st.session_state.get(PREFIX + "live_result")
    cards = st.columns(3)
    cards[0].metric("Bảo toàn trường qua biểu mẫu", _percent(baseline["field_accuracy"]))
    cards[1].metric("Bảo toàn dữ liệu đã có", _percent(baseline["completeness"]))
    cards[2].metric("Bộ hồ sơ kiểm thử", str(baseline["case_count"]))
    st.caption("Đây là kiểm tra cấu trúc trên dữ liệu mẫu đã biết đáp án, không phải độ chính xác LLM, không đo người dùng nhập liệu thực tế.")

    status = get_openai_status()
    if status["configured"]:
        st.info("Đã tìm thấy cấu hình OpenAI; chưa xác nhận quyền truy cập hoặc hạn mức. Chỉ gọi API khi bạn bấm nút chạy bên dưới.")
    else:
        st.info("Chưa cấu hình OpenAI API. Baseline vẫn đo được, nhưng chưa thể tạo số đo LLM thật. "
                "Hệ thống không tự điền số giả vào báo cáo.")

    left, right = st.columns([1, 2], gap="large")
    with left:
        case_limit = st.select_slider(
            "Số hồ sơ gọi API",
            options=[3, 5, 10, 20],
            value=5,
            key=PREFIX + "case_limit",
            help="Mỗi hồ sơ có một lần trích xuất; hồ sơ hợp lệ có thêm một lần diễn giải.",
        )
        run = st.button(
            "Chạy đánh giá LLM thật",
            type="primary",
            key=PREFIX + "run_live",
            disabled=not status["configured"],
            use_container_width=True,
        )
        st.caption("Có thể phát sinh chi phí API. Không bấm nút thì không có dữ liệu nào được gửi.")
    with right:
        st.markdown(
            "**Web sẽ đo tự động:**\n\n"
            "1. `field_accuracy` và `completeness` của trích xuất hồ sơ.\n"
            "2. `llm_groundedness`: tỷ lệ lời giải thích qua guardrails.\n"
            "3. `llm_hallucination_rate`: tỷ lệ phản hồi bị chặn vì tự thêm số hoặc kết luận.\n"
            "4. So sánh kết quả OpenAI với baseline biểu mẫu có cấu trúc."
        )

    if run:
        try:
            with st.spinner("Đang gọi OpenAI và đối chiếu từng hồ sơ…"):
                live = run_live_llm_evaluation(int(case_limit))
            st.session_state[PREFIX + "live_result"] = live
            st.success("Đã đo xong bằng phản hồi API thật.")
        except EvaluationRunError as exc:
            st.session_state.pop(PREFIX + "live_result", None)
            live = None
            st.error(str(exc))

    rows = comparison_rows(baseline, live)
    display = []
    for row in rows:
        display.append({
            "Phương pháp": row["Phương pháp"],
            "Số hồ sơ": row["Số hồ sơ"],
            "Field accuracy": _percent(row["Field accuracy"]),
            "Completeness": _percent(row["Completeness"]),
            "Phạm vi đo": row["Ghi chú"],
        })
    st.dataframe(display, width="stretch", hide_index=True)

    if live is not None:
        live_cards = st.columns(3)
        live_cards[0].metric("LLM groundedness", _percent(live["llm_groundedness"]))
        live_cards[1].metric("LLM hallucination rate", _percent(live["llm_hallucination_rate"]))
        live_cards[2].metric("Thời gian trích xuất TB", f'{live["mean_extraction_time_ms"] / 1000:.2f} giây')
        if live["extraction_failures"]:
            with st.expander("Xem failure cases"):
                st.dataframe(live["extraction_failures"], width="stretch", hide_index=True)
    else:
        st.caption("Các ô LLM chưa hiển thị vì chưa có lần chạy API thật. Đây là trạng thái chưa chạy, không phải điểm 0.")

    st.download_button(
        "Tải bảng đánh giá CSV",
        data=evaluation_csv_bytes(baseline, live),
        file_name="Project_09_Evaluation_Results.csv",
        mime="text/csv",
        key=PREFIX + "download",
        use_container_width=True,
    )
    st.caption("Groundedness tự động là phép kiểm tra guardrail. Đánh giá ý nghĩa của nhận định định tính vẫn cần con người đọc mẫu.")


__all__ = ["render_evaluation_panel"]
