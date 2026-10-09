"""Person 5: reproducible evaluation, with explicit measured/not-measured scope.

No mock prediction is presented as an observed LLM result. Extraction scores
require actual predictions paired with Person 1's ground truth. Detection
scores require issue-level gold labels. Numeric grounding is an automated
screen; qualitative meaning still needs human review.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import re
import time
from typing import Any, Callable


EXTRACTION_FIELDS = (
    "monthly_primary_income", "monthly_other_income", "monthly_essential_expense",
    "monthly_discretionary_expense", "monthly_debt_payment", "current_savings",
    "emergency_fund_reserved", "goal_name", "goal_amount", "goal_horizon_months",
    "risk_tolerance", "liquidity_need", "expected_income_growth",
)
CSV_FIELDS = ("metric", "value", "unit", "scope", "sample_size", "status", "method")
_MENTION = re.compile(r"(?<![\w])(?P<value>[-+]?\d[\d.,]*)(?:\s*(?P<unit>%|VND|đồng|tháng|năm))?", re.IGNORECASE)


class EvaluationError(ValueError):
    """Invalid evaluation input; never substitute fabricated observations."""


def _equal(expected: Any, predicted: Any) -> bool:
    if expected is None or predicted is None:
        return expected is predicted
    if isinstance(expected, bool) or isinstance(predicted, bool):
        return type(expected) is type(predicted) and expected == predicted
    if isinstance(expected, (int, float)) and isinstance(predicted, (int, float)):
        return math.isfinite(expected) and math.isfinite(predicted) and math.isclose(
            expected, predicted, rel_tol=1e-9, abs_tol=0.01
        )
    return expected == predicted


def evaluate_extraction(gold_cases: dict[str, dict], predictions: dict[str, dict]) -> dict:
    """Score the 13 extractable fields in paired, actually executed cases.

    user_id is a fixture identifier, not part of natural-language evidence;
    notes is an internal copy of raw text rather than an exact extraction label.
    Missing source information (gold None) counts as correct only if predicted
    None. Completeness concerns only fields with non-null ground truth.
    """
    if not isinstance(gold_cases, dict) or not isinstance(predictions, dict) or not gold_cases:
        raise EvaluationError("Cần ground truth và dự đoán đã chạy, ghép theo case_id.")
    if set(predictions) - set(gold_cases):
        raise EvaluationError("Có dự đoán không thuộc bộ ground truth.")
    if not predictions:
        raise EvaluationError("Không có dự đoán LLM thực tế để đánh giá.")
    correct = total = expected_non_null = predicted_non_null = 0
    per_case = []
    for case_id, predicted in predictions.items():
        gold = gold_cases[case_id]
        if not isinstance(gold, dict) or not isinstance(predicted, dict):
            raise EvaluationError(f"Dữ liệu {case_id} phải là dictionary.")
        if set(EXTRACTION_FIELDS) - set(gold) or set(EXTRACTION_FIELDS) - set(predicted):
            raise EvaluationError(f"Dữ liệu {case_id} thiếu trường trích xuất.")
        row_correct = 0
        for field in EXTRACTION_FIELDS:
            row_correct += int(_equal(gold[field], predicted[field]))
            if gold[field] is not None:
                expected_non_null += 1
                predicted_non_null += int(predicted[field] is not None)
        correct += row_correct
        total += len(EXTRACTION_FIELDS)
        per_case.append({"case_id": case_id, "correct_fields": row_correct,
                         "total_fields": len(EXTRACTION_FIELDS)})
    return {
        "field_accuracy": correct / total,
        "completeness": predicted_non_null / expected_non_null if expected_non_null else None,
        "correct_fields": correct, "total_fields": total,
        "expected_non_null_fields": expected_non_null,
        "returned_non_null_fields": predicted_non_null,
        "case_count": len(predictions), "per_case": per_case,
    }


def evaluate_issue_detection(gold_issues: dict[str, set[str]],
                             predicted_issues: dict[str, set[str]]) -> dict:
    """Micro precision/recall/F1 for manually labeled missing/contradictory issues.

    Each issue is a stable identifier such as 'missing:goal_horizon_months'.
    Case categories alone are insufficient gold labels for contradictory rules.
    Both mappings must have the same case IDs; a missing prediction is not a TN.
    """
    if not gold_issues or set(gold_issues) != set(predicted_issues):
        raise EvaluationError("Cần bộ nhãn lỗi và dự đoán cùng case_id.")
    tp = fp = fn = 0
    for case_id, expected in gold_issues.items():
        predicted = predicted_issues[case_id]
        if not isinstance(expected, set) or not isinstance(predicted, set):
            raise EvaluationError("Nhãn lỗi phải là set[str].")
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1,
            "true_positive": tp, "false_positive": fp, "false_negative": fn,
            "case_count": len(gold_issues)}


def _source_numbers(source: Any, field: str = "") -> dict[str, list[float]]:
    found: dict[str, list[float]] = {"all": [], "money": [], "rate": [], "month": []}
    if isinstance(source, dict):
        for key, value in source.items():
            group = _source_numbers(value, str(key))
            for name in found:
                found[name].extend(group[name])
    elif isinstance(source, (list, tuple)):
        for value in source:
            group = _source_numbers(value, field)
            for name in found:
                found[name].extend(group[name])
    elif isinstance(source, (int, float)) and not isinstance(source, bool) and math.isfinite(source):
        number = float(source)
        found["all"].append(number)
        key = field.lower()
        if any(x in key for x in ("rate", "growth", "multiplier")):
            found["rate"].append(number)
        elif key == "month" or key.endswith(("_month", "_months")) or "month_to_goal" in key:
            found["month"].append(number)
        elif any(x in key for x in (
            "income", "expense", "payment", "saving", "fund", "amount", "contribution",
            "balance", "fv_", "goal_gap", "outflow", "surplus", "deficit", "gain", "reduction", "gap",
        )):
            found["money"].append(number)
    return found


def _parse_numeric(raw: str) -> float:
    raw = raw.strip()
    # Display uses dot thousands and comma decimals in Vietnamese. A sole dot
    # before 1-2 trailing digits is a decimal; 3 trailing digits is thousands.
    if "." in raw and "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".") if len(raw.split(",")[-1]) < 3 else raw.replace(",", "")
    elif raw.count(".") > 1 or ("." in raw and len(raw.split(".")[-1]) == 3):
        raw = raw.replace(".", "")
    return float(raw)


def audit_numeric_grounding(explanation: str, source: dict) -> dict:
    """Screen numeric mentions against source JSON; do not claim semantic proof.

    Tolerates display rounding to the nearest VND or hundredth of a percent.
    Source may include profile, calculations and Person 3 results. Returns
    unsupported mentions for human review, not a universal NLP verdict.
    """
    if not isinstance(explanation, str) or not isinstance(source, dict):
        raise EvaluationError("Lời giải thích và JSON nguồn không hợp lệ.")
    values = _source_numbers(source)
    if not values["all"]:
        raise EvaluationError("JSON nguồn không chứa số để đối chiếu.")
    unsupported = []
    mentions = []
    for match in _MENTION.finditer(explanation):
        token = match.group(0).strip()
        try:
            number = _parse_numeric(match.group("value"))
        except ValueError:
            unsupported.append(token)
            continue
        unit = (match.group("unit") or "").lower()
        tolerance = 0.505 if unit != "%" else 0.0051
        if unit == "%":
            candidates = values["rate"]
            supported = any(math.isclose(number, v * 100, abs_tol=tolerance, rel_tol=0)
                            for v in candidates)
        else:
            candidates = (values["money"] if unit in {"vnd", "đồng"}
                          else values["month"] if unit in {"tháng", "năm"}
                          else values["all"])
            supported = any(math.isclose(number, v, abs_tol=tolerance, rel_tol=0)
                            for v in candidates)
        mentions.append(token)
        if not supported:
            unsupported.append(token)
    count = len(mentions)
    return {"numeric_claim_count": count, "unsupported_numeric_claims": unsupported,
            "numeric_groundedness": (count - len(unsupported)) / count if count else 1.0,
            "numeric_hallucination_rate": len(unsupported) / count if count else 0.0,
            "method": "Automated numeric screen only; units, scenario meaning and qualitative claims require review."}


def measure_processing_time(action: Callable, *args, **kwargs) -> tuple[Any, float]:
    """Run a real step once and return (output, elapsed milliseconds)."""
    start = time.perf_counter()
    result = action(*args, **kwargs)
    return result, (time.perf_counter() - start) * 1000


def write_evaluation_results(rows: list[dict], output_path: str) -> str:
    """Write transparent measured/pending metric rows to a new CSV file."""
    if not isinstance(rows, list) or not rows:
        raise EvaluationError("Bảng đánh giá cần ít nhất một dòng.")
    if any(set(row) != set(CSV_FIELDS) or row["status"] not in {"measured", "not_measured"}
           for row in rows):
        raise EvaluationError("Mỗi dòng cần đủ cột và trạng thái measured/not_measured.")
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def load_gold_cases(path: str) -> dict[str, dict]:
    """Read Person 1's test_cases.json without altering source data."""
    try:
        cases = json.loads(Path(path).read_text(encoding="utf-8"))["cases"]
        result = {case["case_id"]: case["expected_profile"] for case in cases}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise EvaluationError("Không đọc được ground truth Người 1.") from exc
    if not result or len(result) != len(cases):
        raise EvaluationError("Ground truth rỗng hoặc trùng case_id.")
    return result


__all__ = ["EvaluationError", "evaluate_extraction", "evaluate_issue_detection",
           "audit_numeric_grounding", "measure_processing_time",
           "write_evaluation_results", "load_gold_cases"]
