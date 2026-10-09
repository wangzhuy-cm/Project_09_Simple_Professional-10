from src.market_reference import load_market_reference, reference_assumptions


def test_dated_market_reference_is_engine_ready_and_auditable():
    reference = load_market_reference()
    assumptions = reference_assumptions()
    assert reference["retrieved_on"] == "2026-09-24"
    assert assumptions == {"annual_return_rate": 0.059, "annual_inflation_rate": 0.0489}
    for indicator in reference["indicators"].values():
        assert indicator["source"].strip()
        assert indicator["source_url"].startswith("https://")
