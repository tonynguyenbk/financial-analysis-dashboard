import json
from pathlib import Path

from app.parsers.sample_data import build_mock_statement
from app.services.metrics_engine import calculate_all_metrics


def test_calculate_all_metrics_returns_expected_sections():
    metrics = calculate_all_metrics(build_mock_statement())

    assert metrics["pillars"]["profitability"]
    assert metrics["pillars"]["liquidity"]
    assert metrics["pillars"]["efficiency"]
    assert metrics["pillars"]["solvency"]
    assert metrics["dupont"]
    assert metrics["quality_of_earnings"]["alert_level"] == "green"


def test_vinfast_negative_equity_and_cash_losses_are_flagged():
    fixture_path = Path(__file__).parents[1] / "test_data" / "vinfast_statement.json"
    statement = json.loads(fixture_path.read_text(encoding="utf-8"))

    metrics = calculate_all_metrics(statement)

    assert metrics["quality_of_earnings"]["alert_level"] == "red"
    assert metrics["quality_of_earnings"]["cash_loss_streak"] == 3
    assert metrics["pillars"]["profitability"][-1]["roe"] is None
    assert metrics["pillars"]["solvency"][-1]["debt_to_equity"] is None
    assert metrics["dupont"][-1]["equity_multiplier"] is None
    assert any(warning["code"] == "NEGATIVE_EQUITY" for warning in metrics["warnings"])


def test_metric_engine_does_not_round_output_values():
    statement = build_mock_statement()
    statement.periods[-1].income_statement.net_revenue = 123456.789123456

    metrics = calculate_all_metrics(statement)

    assert metrics["summary"]["net_revenue"] == 123456.789123456
