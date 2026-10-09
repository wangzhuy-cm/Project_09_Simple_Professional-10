"""Reproducible offline baseline and opt-in live LLM evaluation.

The module never invents a live score. The form baseline is measured locally on
the structured synthetic profiles. Live LLM metrics are produced only after an
API key is configured and the user explicitly starts the run.
"""
from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import Path
import statistics
import time

from src.evaluation import CSV_FIELDS, EXTRACTION_FIELDS, evaluate_extraction
from src.llm_explanation import generate_explanation_result
from src.llm_extraction import ExtractionError, extract_profile, get_openai_status
from src.market_reference import reference_assumptions
from src.scenarios import build_scenarios
from src.schemas import parse_financial_profile
from src.validation import validate_profile


ROOT = Path(__file__).resolve().parents[1]
TEST_CASES_PATH = ROOT / "data" / "test_cases.json"


class EvaluationRunError(RuntimeError):
    """Controlled error displayed by the evaluation UI."""


def _cases() -> list[dict]:
    try:
        value = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))["cases"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise EvaluationRunError("Không đọc được bộ 20 hồ sơ đánh giá.") from exc
    if not isinstance(value, list) or not value:
        raise EvaluationRunError("Bộ hồ sơ đánh giá đang trống.")
    return value


def evaluate_form_baseline() -> dict:
    """Measure the structured-form parsing baseline on all bundled cases.

    This is an identity/validation baseline: it measures whether data entered in
    the agreed 15-field form survives schema parsing correctly. It does not
    include human typing errors or completion time and is not presented as LLM
    performance.
    """
    cases = _cases()
    gold = {case["case_id"]: case["expected_profile"] for case in cases}
    predictions = {}
    started = time.perf_counter()
    for case_id, profile in gold.items():
        predictions[case_id] = parse_financial_profile(profile).to_profile_dict()
    elapsed_ms = (time.perf_counter() - started) * 1000
    extraction = evaluate_extraction(gold, predictions)
    return {
        "name": "Biểu mẫu có cấu trúc",
        "field_accuracy": extraction["field_accuracy"],
        "completeness": extraction["completeness"],
        "case_count": extraction["case_count"],
        "processing_time_ms": elapsed_ms,
        "scope": "20 hồ sơ giả lập; schema/form baseline, không phải user study",
    }


def _empty_prediction() -> dict:
    return {field: None for field in EXTRACTION_FIELDS}


def run_live_llm_evaluation(case_limit: int = 5) -> dict:
    """Run real OpenAI extraction and explanation checks on selected cases.

    One extraction request is made per selected planning case. For cases whose
    gold profile is simulation-ready, one additional explanation request is
    made. API/network failures are recorded; they are never replaced by fixture
    outputs. Qualitative groundedness is the share of completed commentaries
    accepted by deterministic guardrails. Hallucination rate is the share of
    completed commentaries rejected specifically for unsupported numeric/outcome
    claims. Human semantic review remains required.
    """
    if get_openai_status()["configured"] is not True:
        raise EvaluationRunError("Chưa có OPENAI_API_KEY nên không thể đo LLM thật.")
    if isinstance(case_limit, bool) or not isinstance(case_limit, int) or not 1 <= case_limit <= 20:
        raise EvaluationRunError("Số hồ sơ đánh giá phải từ 1 đến 20.")

    eligible = [case for case in _cases() if case.get("category") != "out_of_scope"][:case_limit]
    if not eligible:
        raise EvaluationRunError("Không có hồ sơ phù hợp để chạy đánh giá.")
    gold = {case["case_id"]: case["expected_profile"] for case in eligible}
    predictions: dict[str, dict] = {}
    extraction_failures = []
    extraction_times = []

    for case in eligible:
        started = time.perf_counter()
        try:
            predictions[case["case_id"]] = extract_profile(case["input_text"])
        except ExtractionError as exc:
            predictions[case["case_id"]] = _empty_prediction()
            extraction_failures.append({"case_id": case["case_id"], "code": exc.code})
        extraction_times.append((time.perf_counter() - started) * 1000)

    extraction = evaluate_extraction(gold, predictions)

    explanation_records = []
    assumptions = reference_assumptions()
    for case in eligible:
        profile = case["expected_profile"]
        validation = validate_profile(profile, assumptions)
        if validation.get("can_simulate") is not True:
            continue
        scenarios = build_scenarios(profile, assumptions)
        base = scenarios["base"]["calculation_result"]
        wrapped = {"scenarios": scenarios, "what_if": None,
                   "stress_test": None, "is_final_plan": False}
        result = generate_explanation_result(profile, base, wrapped, validation)
        explanation_records.append({
            "case_id": case["case_id"],
            "completed": result["llm_completed"],
            "accepted": result["llm_accepted"],
            "failure_code": result["failure_code"],
        })

    completed = [row for row in explanation_records if row["completed"]]
    if not completed:
        raise EvaluationRunError(
            "OpenAI chưa trả được lời giải thích hoàn chỉnh; kiểm tra key, hạn mức hoặc kết nối rồi chạy lại."
        )
    accepted = sum(row["accepted"] is True for row in completed)
    unsafe = sum(row["failure_code"] == "ungrounded_output" for row in completed)
    return {
        "name": "OpenAI live",
        "model": get_openai_status()["model"],
        "field_accuracy": extraction["field_accuracy"],
        "completeness": extraction["completeness"],
        "case_count": extraction["case_count"],
        "mean_extraction_time_ms": statistics.fmean(extraction_times),
        "llm_groundedness": accepted / len(completed),
        "llm_hallucination_rate": unsafe / len(completed),
        "explanation_case_count": len(completed),
        "extraction_failures": extraction_failures,
        "explanation_records": explanation_records,
        "scope": "Live API; automated guardrail screen, qualitative claims still require human review",
    }


def comparison_rows(baseline: dict, live: dict | None = None) -> list[dict]:
    """Return display rows for an honest form-versus-LLM comparison."""
    rows = [{
        "Phương pháp": baseline["name"],
        "Số hồ sơ": baseline["case_count"],
        "Field accuracy": baseline["field_accuracy"],
        "Completeness": baseline["completeness"],
        "Ghi chú": baseline["scope"],
    }]
    if live is not None:
        rows.append({
            "Phương pháp": live["name"] + " · " + live["model"],
            "Số hồ sơ": live["case_count"],
            "Field accuracy": live["field_accuracy"],
            "Completeness": live["completeness"],
            "Ghi chú": live["scope"],
        })
    return rows


def evaluation_csv_bytes(baseline: dict, live: dict | None = None) -> bytes:
    """Export measured rows only; pending live metrics are not written as scores."""
    rows = [
        {"metric": "field_accuracy", "value": f'{baseline["field_accuracy"]:.6f}',
         "unit": "fraction", "scope": "structured form baseline",
         "sample_size": baseline["case_count"], "status": "measured",
         "method": baseline["scope"]},
        {"metric": "completeness", "value": f'{baseline["completeness"]:.6f}',
         "unit": "fraction", "scope": "structured form baseline",
         "sample_size": baseline["case_count"], "status": "measured",
         "method": baseline["scope"]},
    ]
    if live is not None:
        rows.extend([
            {"metric": "field_accuracy", "value": f'{live["field_accuracy"]:.6f}',
             "unit": "fraction", "scope": "live LLM extraction",
             "sample_size": live["case_count"], "status": "measured",
             "method": live["scope"]},
            {"metric": "completeness", "value": f'{live["completeness"]:.6f}',
             "unit": "fraction", "scope": "live LLM extraction",
             "sample_size": live["case_count"], "status": "measured",
             "method": live["scope"]},
            {"metric": "llm_groundedness", "value": f'{live["llm_groundedness"]:.6f}',
             "unit": "fraction", "scope": "live LLM explanation",
             "sample_size": live["explanation_case_count"], "status": "measured",
             "method": live["scope"]},
            {"metric": "llm_hallucination_rate", "value": f'{live["llm_hallucination_rate"]:.6f}',
             "unit": "fraction", "scope": "live LLM explanation",
             "sample_size": live["explanation_case_count"], "status": "measured",
             "method": live["scope"]},
        ])
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


__all__ = ["EvaluationRunError", "evaluate_form_baseline", "run_live_llm_evaluation",
           "comparison_rows", "evaluation_csv_bytes"]
