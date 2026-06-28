import math
from typing import Any

import numpy as np
import pandas as pd

from app.schemas.financial import FinancialStatement


REQUIRED_NUMERIC_COLUMNS = [
    "current_assets",
    "inventory",
    "accounts_receivable",
    "total_assets",
    "current_liabilities",
    "accounts_payable",
    "total_liabilities",
    "total_equity",
    "net_revenue",
    "gross_profit",
    "cost_of_goods_sold",
    "ebit",
    "interest_expense",
    "net_income",
    "operating_cash_flow",
]


def calculate_all_metrics(statement: FinancialStatement | dict[str, Any]) -> dict[str, Any]:
    payload = _model_to_dict(statement)
    frame = financial_json_to_dataframe(payload)
    if frame.empty:
        raise ValueError("Financial statement contains no periods.")

    profitability = calculate_profitability(frame)
    liquidity = calculate_liquidity(frame)
    efficiency = calculate_efficiency(frame)
    solvency = calculate_solvency(frame)
    dupont = calculate_dupont(frame)
    quality_of_earnings = calculate_quality_of_earnings(frame)

    return {
        "company": payload.get("company", {}),
        "currency": payload.get("currency", "VND"),
        "unit": payload.get("unit", "million"),
        "source_type": payload.get("source_type", "manual"),
        "summary": build_summary(frame),
        "warnings": calculate_warnings(frame),
        "financials": _records(
            frame,
            ["net_revenue", "net_income", "operating_cash_flow", "total_assets", "total_equity"],
        ),
        "pillars": {
            "profitability": _records(
                profitability,
                ["gross_profit_margin", "net_profit_margin", "roa", "roe"],
            ),
            "liquidity": _records(liquidity, ["current_ratio", "quick_ratio"]),
            "efficiency": _records(efficiency, ["dio", "dso", "dpo", "cash_conversion_cycle"]),
            "solvency": _records(solvency, ["debt_to_equity", "interest_coverage_ratio"]),
        },
        "dupont": _records(
            dupont,
            ["net_profit_margin", "asset_turnover", "equity_multiplier", "roe_dupont"],
        ),
        "quality_of_earnings": quality_of_earnings,
    }


def financial_json_to_dataframe(statement: FinancialStatement | dict[str, Any]) -> pd.DataFrame:
    payload = _model_to_dict(statement)
    rows: list[dict[str, Any]] = []
    for period in payload.get("periods", []):
        row = {
            "period": period.get("period"),
            "fiscal_year": period.get("fiscal_year"),
        }
        for section in ("balance_sheet", "income_statement", "cash_flow"):
            row.update(period.get(section) or {})
        rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    for column in REQUIRED_NUMERIC_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["fiscal_year"] = pd.to_numeric(frame["fiscal_year"], errors="coerce")
    frame = frame.sort_values(["fiscal_year", "period"], na_position="last").reset_index(drop=True)
    return _add_average_columns(frame)


def calculate_profitability(frame: pd.DataFrame) -> pd.DataFrame:
    result = _base_metric_frame(frame)
    result["gross_profit_margin"] = _safe_divide(frame["gross_profit"], frame["net_revenue"])
    result["net_profit_margin"] = _safe_divide(frame["net_income"], frame["net_revenue"])
    result["roa"] = _safe_divide(frame["net_income"], frame["average_total_assets"])
    result["roe"] = _safe_divide_positive_denominator(frame["net_income"], frame["average_total_equity"])
    return result


def calculate_liquidity(frame: pd.DataFrame) -> pd.DataFrame:
    result = _base_metric_frame(frame)
    result["current_ratio"] = _safe_divide(frame["current_assets"], frame["current_liabilities"])
    result["quick_ratio"] = _safe_divide(frame["current_assets"] - frame["inventory"], frame["current_liabilities"])
    return result


def calculate_efficiency(frame: pd.DataFrame) -> pd.DataFrame:
    result = _base_metric_frame(frame)
    result["dio"] = _safe_divide(frame["average_inventory"], frame["cost_of_goods_sold"]) * 365
    result["dso"] = _safe_divide(frame["average_accounts_receivable"], frame["net_revenue"]) * 365
    result["dpo"] = _safe_divide(frame["average_accounts_payable"], frame["cost_of_goods_sold"]) * 365
    result["cash_conversion_cycle"] = result["dio"] + result["dso"] - result["dpo"]
    return result


def calculate_solvency(frame: pd.DataFrame) -> pd.DataFrame:
    result = _base_metric_frame(frame)
    result["debt_to_equity"] = _safe_divide_positive_denominator(
        frame["total_liabilities"], frame["total_equity"]
    )
    result["interest_coverage_ratio"] = _safe_divide(frame["ebit"], frame["interest_expense"])
    return result


def calculate_dupont(frame: pd.DataFrame) -> pd.DataFrame:
    result = _base_metric_frame(frame)
    result["net_profit_margin"] = _safe_divide(frame["net_income"], frame["net_revenue"])
    result["asset_turnover"] = _safe_divide(frame["net_revenue"], frame["average_total_assets"])
    result["equity_multiplier"] = _safe_divide_positive_denominator(
        frame["average_total_assets"], frame["average_total_equity"]
    )
    result["roe_dupont"] = (
        result["net_profit_margin"] * result["asset_turnover"] * result["equity_multiplier"]
    )
    return result


def calculate_quality_of_earnings(frame: pd.DataFrame) -> dict[str, Any]:
    result = _base_metric_frame(frame)
    result["quality_of_earnings_ratio"] = _safe_divide(frame["operating_cash_flow"], frame["net_income"])
    result["is_negative"] = result["quality_of_earnings_ratio"] < 0
    result["cfo_negative"] = frame["operating_cash_flow"] < 0
    result["net_income_negative"] = frame["net_income"] < 0
    result["both_cfo_and_net_income_negative"] = result["cfo_negative"] & result["net_income_negative"]
    series = _records(
        result,
        [
            "quality_of_earnings_ratio",
            "is_negative",
            "cfo_negative",
            "net_income_negative",
            "both_cfo_and_net_income_negative",
        ],
    )

    negative_streak = 0
    for point in reversed(series):
        if point.get("is_negative") is True:
            negative_streak += 1
        else:
            break

    cash_loss_streak = 0
    for point in reversed(series):
        if point.get("both_cfo_and_net_income_negative") is True:
            cash_loss_streak += 1
        else:
            break

    latest = series[-1] if series else None
    if latest and latest.get("both_cfo_and_net_income_negative") is True:
        alert_level = "red"
        message = (
            "Operating cash flow and net income are both negative; "
            "a positive CFO/net income ratio is not a healthy earnings signal."
        )
    elif negative_streak >= 2:
        alert_level = "red"
        message = "Quality of earnings ratio is negative for multiple consecutive periods."
    elif latest and latest.get("is_negative") is True:
        alert_level = "yellow"
        message = "Latest quality of earnings ratio is negative."
    else:
        alert_level = "green"
        message = "Operating cash flow supports reported net income."

    return {
        "series": series,
        "latest": latest,
        "negative_streak": negative_streak,
        "cash_loss_streak": cash_loss_streak,
        "alert_level": alert_level,
        "message": message,
    }


def calculate_warnings(frame: pd.DataFrame) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []

    for _, row in frame.iterrows():
        period = _clean_value(row.get("period"))
        if _is_negative(row.get("total_equity")):
            warnings.append(
                {
                    "period": period,
                    "code": "NEGATIVE_EQUITY",
                    "severity": "red",
                    "message": "Equity is negative; ROE, equity multiplier and Debt/Equity are not meaningful.",
                }
            )
        if _is_negative(row.get("gross_profit")):
            warnings.append(
                {
                    "period": period,
                    "code": "NEGATIVE_GROSS_PROFIT",
                    "severity": "red",
                    "message": "Gross profit is negative.",
                }
            )
        if _is_negative(row.get("net_income")):
            warnings.append(
                {
                    "period": period,
                    "code": "NEGATIVE_NET_INCOME",
                    "severity": "red",
                    "message": "Net income is negative.",
                }
            )
        if _is_negative(row.get("operating_cash_flow")):
            warnings.append(
                {
                    "period": period,
                    "code": "NEGATIVE_OPERATING_CASH_FLOW",
                    "severity": "red",
                    "message": "Operating cash flow is negative.",
                }
            )

    return warnings


def build_summary(frame: pd.DataFrame) -> dict[str, Any]:
    latest = frame.iloc[-1]
    return _clean_mapping(
        {
            "latest_period": latest.get("period"),
            "net_revenue": latest.get("net_revenue"),
            "net_income": latest.get("net_income"),
            "operating_cash_flow": latest.get("operating_cash_flow"),
            "total_assets": latest.get("total_assets"),
            "total_equity": latest.get("total_equity"),
        }
    )


def _add_average_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for column in ["total_assets", "total_equity", "inventory", "accounts_receivable", "accounts_payable"]:
        average_column = f"average_{column}"
        frame[average_column] = (frame[column] + frame[column].shift(1)) / 2
        frame[average_column] = frame[average_column].fillna(frame[column])
    return frame


def _base_metric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[["period", "fiscal_year"]].copy()


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace({0: np.nan})
    return numerator.divide(denominator)


def _safe_divide_positive_denominator(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.where(denominator > 0, np.nan)
    return numerator.divide(denominator)


def _is_negative(value: Any) -> bool:
    if value is None:
        return False
    try:
        return bool(float(value) < 0)
    except (TypeError, ValueError):
        return False


def _records(frame: pd.DataFrame, metric_columns: list[str]) -> list[dict[str, Any]]:
    columns = ["period", "fiscal_year", *metric_columns]
    output = frame[columns].replace([np.inf, -np.inf], np.nan)
    return [_clean_mapping(record) for record in output.to_dict(orient="records")]


def _clean_mapping(record: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in record.items():
        cleaned[key] = _clean_year(value) if key == "fiscal_year" else _clean_value(value)
    return cleaned


def _clean_year(value: Any) -> int | None:
    cleaned_value = _clean_value(value)
    if cleaned_value is None:
        return None
    return int(cleaned_value)


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | np.integer):
        return int(value)
    if isinstance(value, float | np.floating):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    return value


def _model_to_dict(value: FinancialStatement | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()
