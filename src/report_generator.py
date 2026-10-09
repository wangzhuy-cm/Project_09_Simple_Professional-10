"""Create a polished, review-gated Vietnamese financial planning PDF."""
from __future__ import annotations

from datetime import datetime
from html import escape
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (HRFlowable, PageBreak, Paragraph,
                               SimpleDocTemplate, Spacer, Table, TableStyle)
from pypdf import PdfReader

from src.evaluation import EvaluationError, audit_numeric_grounding
from src.llm_explanation import (ExplanationError, WARNING_LABELS,
                                 prepare_explanation_facts)
from src.presentation import what_if_change_lines, explanation_mode_label


NAVY = colors.HexColor("#111D3F")
INK = colors.HexColor("#111827")
SLATE = colors.HexColor("#5F6F85")
TEAL = colors.HexColor("#0891B2")
TEAL_LIGHT = colors.HexColor("#ECFEFF")
GOLD = colors.HexColor("#B77915")
GOLD_LIGHT = colors.HexColor("#FFFAEB")
IVORY = colors.HexColor("#F4F7FF")
LINE_COLOR = colors.HexColor("#D7E2F1")
SOFT_BLUE = colors.HexColor("#EEF4FF")
WHITE = colors.white
CONTENT_WIDTH = A4[0] - 36 * mm


class ReportError(ValueError):
    """Safe error for rejected report input or a failed PDF write."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _fonts() -> tuple[str, str]:
    # Liberation Sans (metric-compatible with Arial) instead of DejaVu Sans:
    # DejaVu's hook-above accent (dấu hỏi, used in ể/ẩ/ẳ/ỏ/ủ/ả...) renders as a
    # stray disconnected squiggle at report title sizes; Liberation draws a
    # clean small hook and reads as a standard business-document typeface.
    root = Path(__file__).resolve().parents[1]
    regular = root / "assets" / "LiberationSans-Regular.ttf"
    bold = root / "assets" / "LiberationSans-Bold.ttf"
    if not regular.is_file() or not bold.is_file():
        raise ReportError("font_missing", "Không tìm thấy bộ chữ cần thiết để tạo báo cáo.")
    if "Person5Sans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Person5Sans", str(regular)))
        pdfmetrics.registerFont(TTFont("Person5Sans-Bold", str(bold)))
        pdfmetrics.registerFontFamily(
            "Person5Sans", normal="Person5Sans", bold="Person5Sans-Bold"
        )
    return "Person5Sans", "Person5Sans-Bold"


def _safe_text(value) -> str:
    return (str(value).replace("\u2011", "-").replace("\u2013", "-")
            .replace("\u2014", "-").replace("\u2212", "-"))


def _money(value) -> str:
    return f"{value:,.0f}".replace(",", ".") + " VND"


def _compact_money(value) -> str:
    number = float(value)
    absolute = abs(number)
    if absolute >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}".replace(".", ",") + " tỷ"
    if absolute >= 1_000_000:
        return f"{number / 1_000_000:.1f}".replace(".", ",") + " triệu"
    return f"{number:,.0f}".replace(",", ".")


def _percent(value) -> str:
    return f"{value * 100:.2f}".replace(".", ",") + "%/năm"


def _p(value, style):
    return Paragraph(escape(_safe_text(value)), style)


def _table(rows, widths, body, header, *, padding=8):
    formatted = [[_p(cell, header if row_index == 0 else body)
                  for cell in row] for row_index, row in enumerate(rows)]
    table = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, IVORY]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]))
    return table


def _metric_cards(items: list[tuple[str, str, str]], label_style, value_style, note_style):
    cells = []
    for label, value, note in items:
        card = Table([
            [Paragraph(escape(_safe_text(label)).upper(), label_style)],
            [Paragraph(escape(_safe_text(value)), value_style)],
            [Paragraph(escape(_safe_text(note)), note_style)],
        ], colWidths=[41.1 * mm], rowHeights=[7 * mm, 10 * mm, 7 * mm])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), IVORY),
            ("BOX", (0, 0), (-1, -1), 0.5, LINE_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        cells.append(card)
    grid = Table([cells], colWidths=[43.5 * mm] * len(cells), hAlign="LEFT")
    grid.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return grid


def _goal_progress_chart(facts: dict, regular: str, bold: str) -> Drawing:
    width = CONTENT_WIDTH
    drawing = Drawing(width, 68)
    base = facts["scenarios"]["base"]
    goal = max(float(facts["adjusted_goal"]), 1.0)
    value = max(float(base["fv_total"]), 0.0)
    ratio = value / goal
    bar_x, bar_y, bar_w, bar_h = 8, 25, width - 16, 14
    drawing.add(Rect(0, 0, width, 68, rx=8, ry=8, fillColor=IVORY, strokeColor=LINE_COLOR))
    drawing.add(String(8, 52, "TIẾN ĐỘ MỤC TIÊU", fontName=bold, fontSize=7.4, fillColor=SLATE))
    drawing.add(String(width - 8, 50, f"{ratio * 100:.0f}%", textAnchor="end",
                       fontName=bold, fontSize=13, fillColor=TEAL if ratio >= 1 else GOLD))
    drawing.add(Rect(bar_x, bar_y, bar_w, bar_h, rx=7, ry=7,
                     fillColor=SOFT_BLUE, strokeColor=None))
    drawing.add(Rect(bar_x, bar_y, bar_w * min(ratio, 1), bar_h, rx=7, ry=7,
                     fillColor=TEAL if ratio >= 1 else GOLD, strokeColor=None))
    drawing.add(String(8, 9, "Dự kiến " + _compact_money(value), fontName=regular,
                       fontSize=7.5, fillColor=INK))
    drawing.add(String(width - 8, 9, "Mục tiêu " + _compact_money(goal), textAnchor="end",
                       fontName=regular, fontSize=7.5, fillColor=INK))
    return drawing


def _cashflow_chart(profile: dict, facts: dict, regular: str, bold: str) -> Drawing:
    width = CONTENT_WIDTH
    drawing = Drawing(width, 96)
    income = max(float(facts["income"]), 0.0)
    components = [
        ("Thiết yếu", max(float(profile.get("monthly_essential_expense") or 0), 0), NAVY),
        ("Linh hoạt", max(float(profile.get("monthly_discretionary_expense") or 0), 0), GOLD),
        ("Trả nợ", max(float(profile.get("monthly_debt_payment") or 0), 0), colors.HexColor("#B96A5A")),
        ("Còn lại", max(float(facts["surplus"]), 0), TEAL),
    ]
    drawing.add(Rect(0, 0, width, 96, rx=8, ry=8, fillColor=IVORY, strokeColor=LINE_COLOR))
    drawing.add(String(8, 79, "PHÂN BỔ DÒNG TIỀN HẰNG THÁNG", fontName=bold,
                       fontSize=7.4, fillColor=SLATE))
    drawing.add(String(width - 8, 77, _compact_money(income) + " thu nhập", textAnchor="end",
                       fontName=bold, fontSize=9, fillColor=NAVY))
    bar_x, bar_y, bar_w, bar_h = 8, 51, width - 16, 15
    drawing.add(Rect(bar_x, bar_y, bar_w, bar_h, rx=7, ry=7,
                     fillColor=SOFT_BLUE, strokeColor=None))
    cursor = bar_x
    denominator = max(sum(value for _, value, _ in components), 1)
    for _, value, color in components:
        segment = bar_w * value / denominator
        if segment > 0:
            drawing.add(Rect(cursor, bar_y, segment, bar_h, fillColor=color, strokeColor=None))
            cursor += segment
    legend_x = 8
    for label, value, color in components:
        drawing.add(Rect(legend_x, 22, 7, 7, rx=1.5, ry=1.5, fillColor=color, strokeColor=None))
        drawing.add(String(legend_x + 11, 22, label, fontName=regular, fontSize=7, fillColor=SLATE))
        drawing.add(String(legend_x + 11, 9, _compact_money(value), fontName=bold, fontSize=7.3, fillColor=INK))
        legend_x += width / 4
    return drawing


def _scenario_chart(facts: dict, regular: str, bold: str) -> Drawing:
    width = CONTENT_WIDTH
    height = 174
    drawing = Drawing(width, height)
    keys = ("conservative", "base", "optimistic")
    values = [max(float(facts["scenarios"][key]["fv_total"]), 0) for key in keys]
    goal = max(float(facts["adjusted_goal"]), 0)
    maximum = max(values + [goal, 1]) * 1.15
    plot_x, plot_y, plot_w, plot_h = 58, 36, width - 76, 105
    drawing.add(Rect(0, 0, width, height, rx=8, ry=8, fillColor=WHITE, strokeColor=LINE_COLOR))
    drawing.add(String(12, 156, "GIÁ TRỊ DỰ KIẾN CUỐI KỲ", fontName=bold,
                       fontSize=8, fillColor=NAVY))
    drawing.add(String(width - 12, 155, "Đơn vị: triệu VND", textAnchor="end",
                       fontName=regular, fontSize=6.8, fillColor=SLATE))
    for fraction in (0, .25, .5, .75, 1):
        y = plot_y + plot_h * fraction
        drawing.add(Line(plot_x, y, plot_x + plot_w, y, strokeColor=LINE_COLOR, strokeWidth=.4))
        drawing.add(String(plot_x - 7, y - 2.5, f"{maximum * fraction / 1_000_000:.0f}",
                           textAnchor="end", fontName=regular, fontSize=6.5, fillColor=SLATE))
    goal_y = plot_y + plot_h * goal / maximum
    drawing.add(Line(plot_x, goal_y, plot_x + plot_w, goal_y, strokeColor=GOLD,
                     strokeWidth=1.2, strokeDashArray=[4, 3]))
    drawing.add(String(plot_x + plot_w, goal_y + 4, "Mục tiêu", textAnchor="end",
                       fontName=bold, fontSize=6.5, fillColor=GOLD))
    bar_colors = (colors.HexColor("#94A3B8"), colors.HexColor("#06B6D4"), colors.HexColor("#8B5CF6"))
    labels = ("Thận trọng", "Cơ sở", "Tích cực")
    slot = plot_w / 3
    for index, (value, color, label) in enumerate(zip(values, bar_colors, labels)):
        bar_w = 42
        x = plot_x + slot * index + (slot - bar_w) / 2
        bar_h = plot_h * value / maximum
        drawing.add(Rect(x, plot_y, bar_w, bar_h, rx=4, ry=4, fillColor=color, strokeColor=None))
        drawing.add(String(x + bar_w / 2, min(plot_y + bar_h + 8, 146), _compact_money(value),
                           textAnchor="middle", fontName=bold, fontSize=7, fillColor=INK))
        drawing.add(String(x + bar_w / 2, 18, label, textAnchor="middle",
                           fontName=regular, fontSize=7.2, fillColor=SLATE))
    return drawing


def _projection_chart(scenario_bundle: dict, facts: dict, regular: str, bold: str) -> Drawing:
    """Balance-over-time line chart for the three scenarios against the goal.

    Uses each scenario's own monthly_projection (already computed by the
    engine); draws no new numbers, only plots the ones given.
    """
    width = CONTENT_WIDTH
    height = 172
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, rx=8, ry=8, fillColor=WHITE, strokeColor=LINE_COLOR))
    drawing.add(String(12, height - 18, "SỐ DƯ DỰ KIẾN THEO THỜI GIAN", fontName=bold,
                       fontSize=8, fillColor=NAVY))
    drawing.add(String(width - 12, height - 19, "Đơn vị: triệu VND", textAnchor="end",
                       fontName=regular, fontSize=6.8, fillColor=SLATE))

    scenario_defs = (("conservative", "Thận trọng", colors.HexColor("#94A3B8")),
                     ("base", "Cơ sở", colors.HexColor("#06B6D4")),
                     ("optimistic", "Tích cực", colors.HexColor("#8B5CF6")))
    series, balances, max_month, target_rows = [], [], 0, None
    for key, label, color in scenario_defs:
        rows = (scenario_bundle.get(key) or {}).get("monthly_projection") or []
        if not rows:
            continue
        series.append((label, color, rows))
        balances.extend(row["balance"] for row in rows)
        max_month = max(max_month, rows[-1]["month"])
        target_rows = target_rows or rows
    plot_x, plot_y, plot_w, plot_h = 30, 30, width - 44, height - 66
    if not series or max_month <= 0:
        drawing.add(String(width / 2, height / 2, "Chưa có dữ liệu dự phóng theo tháng.",
                           textAnchor="middle", fontName=regular, fontSize=8, fillColor=SLATE))
        return drawing
    goal_value = max((row["target_amount"] for row in target_rows), default=float(facts["adjusted_goal"]))
    maximum = max(balances + [goal_value, 1]) * 1.08

    for fraction in (0, .25, .5, .75, 1):
        y = plot_y + plot_h * fraction
        drawing.add(Line(plot_x, y, plot_x + plot_w, y, strokeColor=LINE_COLOR, strokeWidth=.4))
        drawing.add(String(plot_x - 6, y - 2.5, f"{maximum * fraction / 1_000_000:.0f}",
                           textAnchor="end", fontName=regular, fontSize=6.3, fillColor=SLATE))
    for month_mark in sorted({0, max_month // 2, max_month}):
        x = plot_x + plot_w * (month_mark / max_month)
        drawing.add(String(x, plot_y - 10, f"T{month_mark}", textAnchor="middle",
                           fontName=regular, fontSize=6.3, fillColor=SLATE))
    goal_points = []
    for row in target_rows:
        goal_points += [plot_x + plot_w * row["month"] / max_month,
                        plot_y + plot_h * row["target_amount"] / maximum]
    drawing.add(PolyLine(goal_points, strokeColor=GOLD, strokeWidth=1.1, strokeDashArray=[3, 2]))
    goal_y = plot_y + plot_h * target_rows[-1]["target_amount"] / maximum
    drawing.add(String(plot_x + plot_w - 5, goal_y + 3, "Mục tiêu", textAnchor="end",
                       fontName=bold, fontSize=6.3, fillColor=GOLD))
    legend_x = plot_x
    for label, color, rows in series:
        points = []
        for row in rows:
            points.append(plot_x + plot_w * (row["month"] / max_month))
            points.append(plot_y + plot_h * min(max(row["balance"], 0) / maximum, 1))
        drawing.add(PolyLine(points, strokeColor=color, strokeWidth=1.8,
                             strokeLineJoin=1, strokeLineCap=1))
        drawing.add(Line(legend_x, height - 30, legend_x + 14, height - 30,
                         strokeColor=color, strokeWidth=2.6))
        drawing.add(String(legend_x + 18, height - 33, label, fontName=regular,
                           fontSize=6.6, fillColor=SLATE))
        legend_x += 58
    return drawing


def _stress_chart(stress: dict, regular: str, bold: str) -> Drawing:
    """Compact before/after bars for the income-shock stress test."""
    width = CONTENT_WIDTH
    height = 86
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, rx=8, ry=8, fillColor=WHITE, strokeColor=LINE_COLOR))
    drawing.add(String(12, height - 16, "SỐ DƯ CUỐI KỲ: TRƯỚC VÀ SAU CÚ SỐC THU NHẬP",
                       fontName=bold, fontSize=7.6, fillColor=NAVY))
    baseline = max(float(stress["baseline"]["calculation_result"]["fv_total"]), 0)
    stressed = max(float(stress["stressed"]["calculation_result"]["fv_total"]), 0)
    maximum = max(baseline, stressed, 1) * 1.15
    plot_x, plot_y, plot_w, plot_h = 20, 18, width - 40, height - 43
    bars = ((baseline, "Kế hoạch cơ sở", TEAL), (stressed, "Sau khi giảm thu nhập", colors.HexColor("#F06464")))
    slot = plot_w / 2
    for index, (value, label, color) in enumerate(bars):
        bar_w = 54
        x = plot_x + slot * index + (slot - bar_w) / 2
        bar_h = plot_h * value / maximum
        drawing.add(Rect(x, plot_y, bar_w, bar_h, rx=4, ry=4, fillColor=color, strokeColor=None))
        drawing.add(String(x + bar_w / 2, plot_y + bar_h + 6, _compact_money(value),
                           textAnchor="middle", fontName=bold, fontSize=7.4, fillColor=INK))
        drawing.add(String(x + bar_w / 2, 6, label, textAnchor="middle",
                           fontName=regular, fontSize=7, fillColor=SLATE))
    return drawing


def _warnings(facts):
    raw = [("Cơ sở", w) for w in facts["calculation_warnings"]]
    raw += [("Hồ sơ", w.get("message", w.get("code", "")) if isinstance(w, dict) else str(w))
            for w in facts["validation_warnings"]]
    for key, item in facts["scenarios"].items():
        label = {"conservative": "Thận trọng", "base": "Cơ sở", "optimistic": "Tích cực"}.get(key, key)
        raw.extend((label, w) for w in item["warnings"])
    if facts["stress_test"]:
        raw.extend(("Giảm thu nhập", w) for w in facts["stress_test"]["stressed"].get("warnings", []))
    grouped = {}
    for label, warning in raw:
        if warning == "income_growth_not_applied_in_mvp":
            continue  # Always disclosed explicitly in assumptions below.
        message = WARNING_LABELS.get(str(warning), str(warning))
        if message:
            grouped.setdefault(message, set()).add(label)
    return [" / ".join(sorted(labels)) + ": " + message for message, labels in grouped.items()]


def _clean_explanation_lines(explanation: str, omitted_sections: set[str] | None = None) -> list[str]:
    """Return display prose while removing internal and duplicated sections."""
    omitted_sections = omitted_sections or set()
    headings = {
        "TÓM TẮT HỒ SƠ VÀ DÒNG TIỀN", "BA KỊCH BẢN (THEO GIẢ ĐỊNH)",
        "WHAT-IF", "STRESS TEST", "BÌNH LUẬN AI (ĐỊNH TÍNH)",
    }
    lines = []
    skip = False
    for raw_line in explanation.splitlines():
        line = raw_line.strip()
        if line == "GIẢ ĐỊNH VÀ CẢNH BÁO":
            skip = True
            continue
        if line in headings:
            skip = line in omitted_sections
            if not skip:
                lines.append(_safe_text(line))
            continue
        if line and not skip and not line.startswith("Chế độ:"):
            lines.append(_safe_text(line))
    return lines


def _draw_page(canvas, doc):
    canvas.saveState()
    page = canvas.getPageNumber()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#06B6D4"))
    canvas.rect(0, A4[1] - 8 * mm, A4[0] / 3, 1.2 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#2563EB"))
    canvas.setLineWidth(1.1)
    canvas.line(18 * mm, 17 * mm, A4[0] - 18 * mm, 17 * mm)
    canvas.setFont("Person5Sans", 7.1)
    canvas.setFillColor(SLATE)
    canvas.drawString(18 * mm, 11.5 * mm, "PROJECT 09 | KẾ HOẠCH TÀI CHÍNH CÁ NHÂN")
    canvas.drawRightString(A4[0] - 18 * mm, 11.5 * mm, f"Trang {page}")
    canvas.restoreState()


def generate_report(profile: dict, results: dict, explanation: str, output_path: str) -> str:
    """Create a confirmed report without changing or recalculating supplied data."""
    if not isinstance(results, dict) or not isinstance(explanation, str) or not explanation.strip():
        raise ReportError("invalid_input", "Thiếu kết quả hoặc lời giải thích để tạo báo cáo.")
    if any(results.get(key) is not True for key in
           ("profile_confirmed", "assumptions_confirmed", "report_confirmed")):
        raise ReportError("confirmation_required", "Cần xác nhận hồ sơ, giả định và báo cáo trước khi xuất PDF.")
    try:
        calculation = results["calculation_result"]
        scenarios = results["scenario_result"]
        validation = results["validation_result"]
        facts = prepare_explanation_facts(profile, calculation, scenarios, validation)
        scenario_bundle = scenarios.get("scenarios", scenarios) if isinstance(scenarios, dict) else {}
        audit = audit_numeric_grounding(
            explanation,
            {"profile": profile, "calculation_result": calculation,
             "scenario_result": scenarios, "validation_result": validation},
        )
    except (KeyError, TypeError, ExplanationError, EvaluationError) as exc:
        raise ReportError("invalid_input", "Dữ liệu báo cáo chưa hợp lệ hoặc đã thay đổi.") from exc
    if audit["unsupported_numeric_claims"]:
        raise ReportError("ungrounded_explanation", "Lời giải thích chứa số chưa đối chiếu được với kết quả.")
    for item in facts["scenarios"].values():
        line = next((line for line in explanation.splitlines()
                     if line.startswith(str(item["label"]) + ":")), None)
        expected = "còn thiếu" if item["goal_gap"] > 0 else "đạt hoặc vượt mục tiêu"
        if line is None or expected not in line:
            raise ReportError("inconsistent_verdict", "Lời giải thích không khớp với kết quả phương án.")
    if not isinstance(output_path, str) or not output_path.lower().endswith(".pdf"):
        raise ReportError("invalid_path", "Đường dẫn báo cáo phải kết thúc bằng .pdf.")

    regular, bold = _fonts()
    base = facts["scenarios"]["base"]
    reached = base["goal_reached_by_horizon"]
    styles = getSampleStyleSheet()
    eyebrow = ParagraphStyle("eyebrow", parent=styles["Normal"], fontName=bold,
                             fontSize=7.2, leading=10, textColor=GOLD, spaceAfter=4)
    title = ParagraphStyle("title", parent=styles["Title"], fontName=bold,
                           fontSize=23, leading=29, textColor=NAVY,
                           alignment=TA_LEFT, spaceAfter=6)
    subtitle = ParagraphStyle("subtitle", parent=styles["Normal"], fontName=regular,
                              fontSize=9, leading=14, textColor=SLATE, spaceAfter=8)
    heading = ParagraphStyle("heading", parent=styles["Heading2"], fontName=bold,
                             fontSize=12, leading=16, textColor=NAVY,
                             spaceBefore=12, spaceAfter=7, keepWithNext=True)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=regular,
                          fontSize=8.5, leading=13.5, textColor=INK, spaceAfter=6)
    small = ParagraphStyle("small", parent=body, fontSize=7.4, leading=10.5, spaceAfter=0)
    table_head = ParagraphStyle("table_head", parent=small, fontName=bold,
                                textColor=WHITE, alignment=TA_LEFT)
    card_label = ParagraphStyle("card_label", parent=small, fontName=bold,
                                fontSize=6.2, leading=7.5, textColor=SLATE)
    card_value = ParagraphStyle("card_value", parent=body, fontName=bold,
                                fontSize=10, leading=12, textColor=NAVY, spaceAfter=0)
    card_note = ParagraphStyle("card_note", parent=small, fontSize=6.2,
                               leading=7.5, textColor=SLATE)
    outcome_title = ParagraphStyle("outcome_title", parent=body, fontName=bold,
                                   fontSize=13, leading=17,
                                   textColor=TEAL if reached else colors.HexColor("#8A5B10"),
                                   spaceAfter=2)
    warning_style = ParagraphStyle("warning", parent=body,
                                   textColor=colors.HexColor("#6F4C13"), leftIndent=8)
    center_small = ParagraphStyle("center_small", parent=small, alignment=TA_CENTER)

    generated = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y - %H:%M")
    outcome = "Kế hoạch cơ sở có khả năng đạt mục tiêu đúng hạn" if reached else "Kế hoạch cơ sở chưa đạt mục tiêu đúng hạn"
    timing = ("Dự kiến đạt vào tháng " + str(base["estimated_month_to_goal"])
              if base["estimated_month_to_goal"] is not None else "Chưa xác định được tháng đạt mục tiêu")
    story = [
        Paragraph("PROJECT 09 / PERSONAL FINANCE REPORT", eyebrow),
        Paragraph(escape(_safe_text(facts["goal_name"])), title),
        Paragraph("Báo cáo kế hoạch tài chính cá nhân - " + generated, subtitle),
        Paragraph(escape(explanation_mode_label(explanation)), small), Spacer(1, 6),
        HRFlowable(width="100%", thickness=1.4, color=GOLD, spaceAfter=10),
    ]

    outcome_box = Table([
        [Paragraph("KẾT LUẬN CHÍNH", card_label)],
        [Paragraph(escape(outcome), outcome_title)],
        [Paragraph(escape(timing + ". Hãy theo dõi kế hoạch định kỳ và điều chỉnh khi dòng tiền thay đổi."), body)],
    ], colWidths=[CONTENT_WIDTH])
    outcome_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT if reached else GOLD_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.7, TEAL if reached else GOLD),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [outcome_box, Paragraph("01 / TỔNG QUAN KẾ HOẠCH", heading)]
    story.append(_metric_cards([
        ("Mục tiêu", _compact_money(facts["adjusted_goal"]), f"Trong {facts['horizon']} tháng"),
        ("Dự kiến có", _compact_money(base["fv_total"]), "Phương án cơ sở"),
        ("Dành mỗi tháng", _compact_money(base["monthly_contribution"]), "Theo kế hoạch hiện tại"),
        ("Quỹ dự phòng", _compact_money(facts["emergency_fund_reserved"]), "Được giữ riêng"),
    ], card_label, card_value, card_note))
    story += [Spacer(1, 8), _goal_progress_chart(facts, regular, bold), Spacer(1, 8),
              _cashflow_chart(profile, facts, regular, bold)]

    story.append(Paragraph("Thông tin nền", heading))
    details = [
        ("Mục tiêu theo giá hôm nay", _money(facts["goal_amount"])),
        ("Mục tiêu sau điều chỉnh", _money(facts["adjusted_goal"])),
        ("Tổng thu nhập mỗi tháng", _money(facts["income"])),
        ("Tổng chi tiêu và trả nợ", _money(facts["outflow"])),
        ("Dòng tiền còn lại", _money(facts["surplus"])),
        ("Vốn ban đầu cho mục tiêu", _money(facts["initial_available"])),
    ]
    story.append(_table([["Chỉ tiêu", "Giá trị"]] + [list(item) for item in details],
                        [92 * mm, 82 * mm], small, table_head))

    story += [PageBreak(), Paragraph("02 / BA PHƯƠNG ÁN", eyebrow),
              Paragraph("So sánh để chọn mức độ phù hợp", title),
              Paragraph("Ba phương án giúp bạn nhìn thấy khoảng an toàn và dư địa của kế hoạch. "
                        "Đây là các tình huống mô phỏng, không phải xác suất thành công.", subtitle),
              _projection_chart(scenario_bundle, facts, regular, bold), Spacer(1, 8),
              _scenario_chart(facts, regular, bold), Spacer(1, 8)]
    scenario_rows = [["Phương án", "Dành mỗi tháng", "Giá trị cuối kỳ", "Kết quả"]]
    for key in ("conservative", "base", "optimistic"):
        item = facts["scenarios"][key]
        verdict = ("Còn thiếu " + _money(item["goal_gap"])
                   if item["goal_gap"] > 0 else "Đạt / vượt mục tiêu")
        scenario_rows.append([item["label"], _money(item["monthly_contribution"]),
                              _money(item["fv_total"]), verdict])
    story.append(_table(scenario_rows, [31 * mm, 47 * mm, 47 * mm, 49 * mm], small, table_head))

    if facts["what_if"]:
        what_if = facts["what_if"]
        story.append(Paragraph("Kết quả khi thử thay đổi kế hoạch", heading))
        for change in what_if_change_lines(what_if):
            story.append(Paragraph(escape(_safe_text(change)), body))
        story.append(_table([
            ["Trước thay đổi", "Sau thay đổi"],
            [_money(what_if["baseline"]["calculation_result"]["fv_total"]) +
             f" sau {what_if['baseline']['calculation_result']['goal_horizon_months']} tháng",
             _money(what_if["modified"]["calculation_result"]["fv_total"]) +
             f" sau {what_if['modified']['calculation_result']['goal_horizon_months']} tháng"],
        ], [87 * mm, 87 * mm], small, table_head))
        if what_if["comparison"].get("horizons_differ"):
            story.append(Paragraph("Hai kết quả sử dụng thời hạn khác nhau; hãy đọc cùng thời hạn và mục tiêu tương ứng.", body))

    # Page 3 deliberately starts here. Keeping the stress block with the notes
    # avoids a nearly empty overflow page when what-if and stress are both on.
    story += [PageBreak(), Paragraph("03 / SỨC CHỊU ĐỰNG VÀ LƯU Ý", eyebrow),
              Paragraph("Những điều cần nhớ khi theo dõi kế hoạch", title)]
    if facts["stress_test"]:
        stress = facts["stress_test"]
        comparison = stress["comparison"]
        story.append(Paragraph("Khả năng chịu đựng khi thu nhập giảm", heading))
        story.append(_stress_chart(stress, regular, bold))
        story.append(Spacer(1, 5))
        story.append(_table([
            ["Kế hoạch cơ sở", "Khi thu nhập giảm", "Mức giảm cuối kỳ"],
            [_money(stress["baseline"]["calculation_result"]["fv_total"]),
             _money(stress["stressed"]["calculation_result"]["fv_total"]),
             _money(comparison["fv_total_reduction"])],
        ], [58 * mm, 58 * mm, 58 * mm], small, table_head, padding=5))
        delay = comparison.get("goal_delay_months")
        extension = comparison.get("extension_months_from_original_horizon")
        original_month = stress["baseline"]["calculation_result"].get("estimated_month_to_goal")
        stress_month = stress["stressed"]["calculation_result"].get("estimated_month_to_goal")
        story.append(Paragraph(
            f"Tháng đạt mục tiêu: cơ sở {original_month if original_month is not None else 'chưa xác định'}, "
            f"sau cú sốc {stress_month if stress_month is not None else 'chưa xác định'}. "
            "Chậm so với cơ sở: " + ("chưa xác định" if delay is None else f"{delay} tháng") +
            f"; trễ so với hạn gốc {facts['horizon']} tháng: " +
            ("chưa xác định" if extension is None else f"{extension} tháng") + ".", body))
        deficit = comparison.get("unfunded_cashflow_deficit", 0)
        if deficit > 0:
            story.append(Paragraph("KẾT QUẢ CÓ ĐIỀU KIỆN: thiếu " + _money(deficit) +
                " cho sinh hoạt. Khoản này chưa trừ khỏi tiền mục tiêu hoặc quỹ dự phòng; cần nguồn khác bù thiếu hụt.", warning_style))
        recovery = comparison.get("recovery_required_monthly_contribution")
        recovery_gap = comparison.get("recovery_required_contribution_gap")
        if recovery is not None:
            story.append(Paragraph(
                "Để giữ hạn gốc, mức cần dành là " + _money(recovery) +
                "/tháng; phần vượt dòng tiền hiện tại là " + _money(recovery_gap or 0) +
                "/tháng.", body))

    story.append(Paragraph("Giả định chính", heading))
    story.append(Paragraph(
        f"Lợi suất cơ sở giả định {_percent(facts['annual_return_rate'])}; lạm phát giả định "
        f"{_percent(facts['annual_inflation_rate'])}. Khoản dành cho mục tiêu được ghi nhận vào cuối tháng. "
        "Báo cáo chưa tính thuế, phí, tăng trưởng thu nhập lũy tiến hoặc biến động lợi suất. "
        "Phần quỹ dự phòng giữ riêng, không tự đưa vào vốn mục tiêu. Nhu cầu rút tiền chỉ được ghi nhận, chưa tác động phép tính. "
        "Lãi suất và lạm phát là giả định giáo dục, không phải dữ liệu thị trường được xác minh tại thời điểm xuất.", body))
    warnings = _warnings(facts)
    story.append(Paragraph("Điểm cần lưu ý", heading))
    if warnings:
        story.extend(Paragraph("- " + escape(_safe_text(message)), warning_style) for message in warnings)
    else:
        story.append(Paragraph("Không có lưu ý bổ sung từ dữ liệu hiện tại.", body))

    story.append(Paragraph("Nguồn nội dung báo cáo", heading))
    story.append(Paragraph(escape(explanation_mode_label(explanation)), body))
    heading_lines = {
        "TÓM TẮT HỒ SƠ VÀ DÒNG TIỀN", "BA KỊCH BẢN (THEO GIẢ ĐỊNH)",
        "WHAT-IF", "STRESS TEST", "BÌNH LUẬN AI (ĐỊNH TÍNH)",
    }
    omitted_sections = {"TÓM TẮT HỒ SƠ VÀ DÒNG TIỀN", "BA KỊCH BẢN (THEO GIẢ ĐỊNH)"}
    if facts["what_if"]:
        omitted_sections.add("WHAT-IF")
    if facts["stress_test"]:
        omitted_sections.add("STRESS TEST")
    for line in _clean_explanation_lines(explanation, omitted_sections):
        if line in heading_lines:
            display = {
                "TÓM TẮT HỒ SƠ VÀ DÒNG TIỀN": "Tóm tắt hồ sơ và dòng tiền",
                "BA KỊCH BẢN (THEO GIẢ ĐỊNH)": "Diễn giải ba phương án",
                "WHAT-IF": "Khi điều chỉnh kế hoạch",
                "STRESS TEST": "Khi thu nhập giảm",
                "BÌNH LUẬN AI (ĐỊNH TÍNH)": "Góc nhìn bổ sung",
            }[line]
            story.append(Paragraph(display, heading))
        else:
            story.append(Paragraph(escape(line), body))

    disclaimer = Table([[Paragraph(
        "Báo cáo này phục vụ mục đích học tập và lập kế hoạch cá nhân. Các phương án là kết quả mô phỏng theo giả định, "
        "không cam kết lợi nhuận và không thay thế tư vấn tài chính chuyên nghiệp.", center_small)]],
        colWidths=[CONTENT_WIDTH])
    disclaimer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GOLD_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, GOLD),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story += [Spacer(1, 8), disclaimer]

    target = Path(output_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", prefix="project09_", dir=target.parent,
                                         delete=False) as handle:
            temp_path = Path(handle.name)
        doc = SimpleDocTemplate(
            str(temp_path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
            topMargin=16 * mm, bottomMargin=23 * mm,
            title="Project 09 - Báo cáo kế hoạch tài chính cá nhân",
            author="Project 09",
            subject="Báo cáo kế hoạch tài chính theo mục tiêu",
        )
        doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
        if temp_path.stat().st_size < 500:
            raise OSError("PDF empty")
        if not PdfReader(str(temp_path)).pages:
            raise OSError("PDF contains no pages")
        os.replace(temp_path, target)
    except (OSError, ValueError) as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise ReportError("pdf_unavailable", "Không tạo được file PDF; dữ liệu của bạn vẫn được giữ nguyên.") from exc
    return str(target)


__all__ = ["ReportError", "generate_report"]
