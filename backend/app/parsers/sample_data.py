from app.schemas.financial import FinancialStatement


def build_mock_statement(source_type: str = "mock") -> FinancialStatement:
    return FinancialStatement(
        company={
            "name": "Demo Manufacturing JSC",
            "ticker": "DEMO",
            "industry": "Manufacturing",
        },
        currency="VND",
        unit="million",
        source_type=source_type,
        periods=[
            {
                "period": "2022",
                "fiscal_year": 2022,
                "balance_sheet": {
                    "current_assets": 470000,
                    "inventory": 126000,
                    "accounts_receivable": 98000,
                    "total_assets": 1080000,
                    "current_liabilities": 235000,
                    "accounts_payable": 76000,
                    "total_liabilities": 590000,
                    "total_equity": 490000,
                },
                "income_statement": {
                    "net_revenue": 820000,
                    "gross_profit": 238000,
                    "cost_of_goods_sold": 582000,
                    "ebit": 123000,
                    "interest_expense": 29000,
                    "net_income": 78000,
                },
                "cash_flow": {"operating_cash_flow": 69000},
            },
            {
                "period": "2023",
                "fiscal_year": 2023,
                "balance_sheet": {
                    "current_assets": 520000,
                    "inventory": 140000,
                    "accounts_receivable": 110000,
                    "total_assets": 1200000,
                    "current_liabilities": 260000,
                    "accounts_payable": 85000,
                    "total_liabilities": 650000,
                    "total_equity": 550000,
                },
                "income_statement": {
                    "net_revenue": 950000,
                    "gross_profit": 280000,
                    "cost_of_goods_sold": 670000,
                    "ebit": 145000,
                    "interest_expense": 32000,
                    "net_income": 92000,
                },
                "cash_flow": {"operating_cash_flow": 108000},
            },
            {
                "period": "2024",
                "fiscal_year": 2024,
                "balance_sheet": {
                    "current_assets": 580000,
                    "inventory": 155000,
                    "accounts_receivable": 128000,
                    "total_assets": 1350000,
                    "current_liabilities": 295000,
                    "accounts_payable": 97000,
                    "total_liabilities": 720000,
                    "total_equity": 630000,
                },
                "income_statement": {
                    "net_revenue": 1120000,
                    "gross_profit": 342000,
                    "cost_of_goods_sold": 778000,
                    "ebit": 181000,
                    "interest_expense": 35000,
                    "net_income": 116000,
                },
                "cash_flow": {"operating_cash_flow": 121000},
            },
        ],
        metadata={
            "schema_version": "0.1.0",
            "notes": "Mock data uses normalized fields required by the metrics engine.",
        },
    )
