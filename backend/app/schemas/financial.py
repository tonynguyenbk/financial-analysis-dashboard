from typing import Any, Literal

from pydantic import BaseModel, Field


SourceType = Literal["pdf", "excel", "mock", "manual", "sec"]


class CompanyInfo(BaseModel):
    name: str = "Unknown Company"
    ticker: str | None = None
    industry: str | None = None


class BalanceSheet(BaseModel):
    current_assets: float | None = None
    inventory: float | None = None
    accounts_receivable: float | None = None
    total_assets: float | None = None
    current_liabilities: float | None = None
    accounts_payable: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None


class IncomeStatement(BaseModel):
    net_revenue: float | None = None
    gross_profit: float | None = None
    cost_of_goods_sold: float | None = None
    ebit: float | None = None
    interest_expense: float | None = None
    net_income: float | None = None


class CashFlowStatement(BaseModel):
    operating_cash_flow: float | None = None


class FinancialPeriod(BaseModel):
    period: str
    fiscal_year: int | None = None
    balance_sheet: BalanceSheet = Field(default_factory=BalanceSheet)
    income_statement: IncomeStatement = Field(default_factory=IncomeStatement)
    cash_flow: CashFlowStatement = Field(default_factory=CashFlowStatement)


class FinancialStatement(BaseModel):
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    currency: str = "VND"
    unit: str = "million"
    source_type: SourceType = "manual"
    periods: list[FinancialPeriod]
    metadata: dict[str, Any] = Field(default_factory=dict)
