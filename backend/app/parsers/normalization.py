import re
import unicodedata
from collections import defaultdict
from typing import Any

from app.schemas.financial import FinancialStatement


FIELD_PATHS: dict[str, tuple[str, str]] = {
    "CURRENT_ASSETS": ("balance_sheet", "current_assets"),
    "INVENTORY": ("balance_sheet", "inventory"),
    "ACCOUNTS_RECEIVABLE": ("balance_sheet", "accounts_receivable"),
    "TOTAL_ASSETS": ("balance_sheet", "total_assets"),
    "CURRENT_LIABILITIES": ("balance_sheet", "current_liabilities"),
    "ACCOUNTS_PAYABLE": ("balance_sheet", "accounts_payable"),
    "TOTAL_LIABILITIES": ("balance_sheet", "total_liabilities"),
    "TOTAL_EQUITY": ("balance_sheet", "total_equity"),
    "NET_REVENUE": ("income_statement", "net_revenue"),
    "GROSS_PROFIT": ("income_statement", "gross_profit"),
    "COST_OF_GOODS_SOLD": ("income_statement", "cost_of_goods_sold"),
    "EBIT": ("income_statement", "ebit"),
    "INTEREST_EXPENSE": ("income_statement", "interest_expense"),
    "NET_INCOME": ("income_statement", "net_income"),
    "OPERATING_CASH_FLOW": ("cash_flow", "operating_cash_flow"),
}

METRIC_ALIASES: dict[str, str] = {
    "current assets": "CURRENT_ASSETS",
    "tai san ngan han": "CURRENT_ASSETS",
    "inventory": "INVENTORY",
    "hang ton kho": "INVENTORY",
    "accounts receivable": "ACCOUNTS_RECEIVABLE",
    "phai thu khach hang": "ACCOUNTS_RECEIVABLE",
    "cac khoan phai thu ngan han": "ACCOUNTS_RECEIVABLE",
    "total assets": "TOTAL_ASSETS",
    "tong tai san": "TOTAL_ASSETS",
    "tong cong tai san": "TOTAL_ASSETS",
    "current liabilities": "CURRENT_LIABILITIES",
    "no ngan han": "CURRENT_LIABILITIES",
    "no phai tra ngan han": "CURRENT_LIABILITIES",
    "accounts payable": "ACCOUNTS_PAYABLE",
    "phai tra nguoi ban": "ACCOUNTS_PAYABLE",
    "phai tra nguoi ban ngan han": "ACCOUNTS_PAYABLE",
    "total liabilities": "TOTAL_LIABILITIES",
    "tong no phai tra": "TOTAL_LIABILITIES",
    "tong cong no phai tra": "TOTAL_LIABILITIES",
    "no phai tra": "TOTAL_LIABILITIES",
    "total equity": "TOTAL_EQUITY",
    "von chu so huu": "TOTAL_EQUITY",
    "net revenue": "NET_REVENUE",
    "doanh thu thuan": "NET_REVENUE",
    "doanh thu thuan ve ban hang": "NET_REVENUE",
    "doanh thu ban hang va cung cap": "NET_REVENUE",
    "doanh thu thuan ve ban hang va cung cap dich vu": "NET_REVENUE",
    "gross profit": "GROSS_PROFIT",
    "loi nhuan gop": "GROSS_PROFIT",
    "loi nhuan gop ve ban hang": "GROSS_PROFIT",
    "lo gop": "GROSS_PROFIT",
    "lo gop ve ban hang": "GROSS_PROFIT",
    "cost of goods sold": "COST_OF_GOODS_SOLD",
    "gia von hang ban": "COST_OF_GOODS_SOLD",
    "ebit": "EBIT",
    "loi nhuan truoc lai vay va thue": "EBIT",
    "loi nhuan thuan tu hoat dong kinh doanh": "EBIT",
    "lo thuan tu hoat dong kinh doanh": "EBIT",
    "interest expense": "INTEREST_EXPENSE",
    "chi phi lai vay": "INTEREST_EXPENSE",
    "chi phi di vay": "INTEREST_EXPENSE",
    "net income": "NET_INCOME",
    "profit after tax": "NET_INCOME",
    "loi nhuan sau thue": "NET_INCOME",
    "lo sau thue": "NET_INCOME",
    "lo sau thue tndn": "NET_INCOME",
    "loi nhuan sau thue thu nhap doanh nghiep": "NET_INCOME",
    "operating cash flow": "OPERATING_CASH_FLOW",
    "cash flow from operating activities": "OPERATING_CASH_FLOW",
    "luu chuyen tien thuan tu hoat dong kinh doanh": "OPERATING_CASH_FLOW",
    "luu chuyen tien thuan su dung vao hoat dong kinh doanh": "OPERATING_CASH_FLOW",
    "luu chuyen tien thuan su dung vao": "OPERATING_CASH_FLOW",
    "dong tien tu hoat dong kinh doanh": "OPERATING_CASH_FLOW",
}


def normalize_label(label: Any) -> str:
    text = str(label or "").strip().lower()
    text = text.replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_metric(label: Any) -> str | None:
    normalized = normalize_label(label)
    if not normalized:
        return None
    return METRIC_ALIASES.get(normalized)


def coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    is_negative = text.startswith("(") and text.endswith(")")
    cleaned = text.strip("()")
    cleaned = cleaned.replace(" ", "")
    cleaned = re.sub(r"[^0-9,\.\-]", "", cleaned)
    if cleaned in {"", "-", "."}:
        return None

    cleaned = normalize_number_separators(cleaned)

    try:
        number = float(cleaned)
    except ValueError:
        return None
    return -number if is_negative else number


def normalize_number_separators(value: str) -> str:
    negative = value.startswith("-")
    unsigned = value[1:] if negative else value

    if "," in unsigned and "." in unsigned:
        if unsigned.rfind(",") > unsigned.rfind("."):
            unsigned = unsigned.replace(".", "").replace(",", ".")
        else:
            unsigned = unsigned.replace(",", "")
    elif "." in unsigned:
        parts = unsigned.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3):
            unsigned = "".join(parts)
    elif "," in unsigned:
        parts = unsigned.split(",")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3):
            unsigned = "".join(parts)
        else:
            unsigned = unsigned.replace(",", ".")

    return f"-{unsigned}" if negative else unsigned


def infer_fiscal_year(period: Any) -> int | None:
    match = re.search(r"(20\d{2}|19\d{2})", str(period))
    return int(match.group(1)) if match else None


def build_statement_from_metric_records(
    *,
    company: dict[str, Any] | None,
    records: list[dict[str, Any]],
    source_type: str,
    currency: str = "VND",
    unit: str = "million",
    metadata: dict[str, Any] | None = None,
) -> FinancialStatement:
    grouped_periods: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "balance_sheet": {},
            "income_statement": {},
            "cash_flow": {},
        }
    )
    unknown_metrics: set[str] = set()

    for record in records:
        metric = canonical_metric(record.get("metric") or record.get("label") or record.get("code"))
        if metric is None:
            raw_metric = record.get("metric") or record.get("label") or record.get("code")
            if raw_metric:
                unknown_metrics.add(str(raw_metric))
            continue

        period = str(record.get("period") or record.get("fiscal_year") or "").strip()
        value = coerce_number(record.get("value"))
        if not period or value is None:
            continue

        section, field_name = FIELD_PATHS[metric]
        grouped_periods[period][section][field_name] = value
        grouped_periods[period]["period"] = period
        grouped_periods[period]["fiscal_year"] = infer_fiscal_year(period)

    periods = sorted(
        grouped_periods.values(),
        key=lambda item: (item.get("fiscal_year") is None, item.get("fiscal_year") or 0, item["period"]),
    )

    if not periods:
        raise ValueError("No recognizable financial metrics were found in the input.")

    for period in periods:
        reconcile_balance_sheet(period["balance_sheet"])

    final_metadata = metadata.copy() if metadata else {}
    if unknown_metrics:
        final_metadata["unknown_metrics"] = sorted(unknown_metrics)

    return FinancialStatement(
        company=company or {"name": "Unknown Company"},
        currency=currency,
        unit=unit,
        source_type=source_type,
        periods=periods,
        metadata=final_metadata,
    )


def reconcile_balance_sheet(balance_sheet: dict[str, Any]) -> None:
    total_assets = coerce_number(balance_sheet.get("total_assets"))
    total_liabilities = coerce_number(balance_sheet.get("total_liabilities"))
    total_equity = coerce_number(balance_sheet.get("total_equity"))

    if (
        (total_assets is None or abs(total_assets) < 1000)
        and total_liabilities is not None
        and total_equity is not None
        and abs(total_liabilities) >= 1000
    ):
        balance_sheet["total_assets"] = total_liabilities + total_equity
