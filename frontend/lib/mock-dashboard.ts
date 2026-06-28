import type { DashboardMetrics } from "@/types/financial";

export const fallbackDashboard: DashboardMetrics = {
  company: {
    name: "Demo Manufacturing JSC",
    ticker: "DEMO",
    industry: "Manufacturing"
  },
  currency: "VND",
  unit: "million",
  source_type: "mock",
  summary: {
    latest_period: "2024",
    net_revenue: 1120000,
    net_income: 116000,
    operating_cash_flow: 121000,
    total_assets: 1350000,
    total_equity: 630000
  },
  warnings: [],
  financials: [
    {
      period: "2022",
      fiscal_year: 2022,
      net_revenue: 820000,
      net_income: 78000,
      operating_cash_flow: 69000,
      total_assets: 1080000,
      total_equity: 490000
    },
    {
      period: "2023",
      fiscal_year: 2023,
      net_revenue: 950000,
      net_income: 92000,
      operating_cash_flow: 108000,
      total_assets: 1200000,
      total_equity: 550000
    },
    {
      period: "2024",
      fiscal_year: 2024,
      net_revenue: 1120000,
      net_income: 116000,
      operating_cash_flow: 121000,
      total_assets: 1350000,
      total_equity: 630000
    }
  ],
  pillars: {
    profitability: [
      {
        period: "2022",
        fiscal_year: 2022,
        gross_profit_margin: 0.290244,
        net_profit_margin: 0.095122,
        roa: 0.072222,
        roe: 0.159184
      },
      {
        period: "2023",
        fiscal_year: 2023,
        gross_profit_margin: 0.294737,
        net_profit_margin: 0.096842,
        roa: 0.080702,
        roe: 0.176923
      },
      {
        period: "2024",
        fiscal_year: 2024,
        gross_profit_margin: 0.305357,
        net_profit_margin: 0.103571,
        roa: 0.09098,
        roe: 0.19661
      }
    ],
    liquidity: [
      {
        period: "2022",
        fiscal_year: 2022,
        current_ratio: 2,
        quick_ratio: 1.46383
      },
      {
        period: "2023",
        fiscal_year: 2023,
        current_ratio: 2,
        quick_ratio: 1.461538
      },
      {
        period: "2024",
        fiscal_year: 2024,
        current_ratio: 1.966102,
        quick_ratio: 1.440678
      }
    ],
    efficiency: [
      {
        period: "2022",
        fiscal_year: 2022,
        dio: 78.969072,
        dso: 43.621951,
        dpo: 47.66323,
        cash_conversion_cycle: 74.927793
      },
      {
        period: "2023",
        fiscal_year: 2023,
        dio: 72.440299,
        dso: 39.957895,
        dpo: 43.850746,
        cash_conversion_cycle: 68.547448
      },
      {
        period: "2024",
        fiscal_year: 2024,
        dio: 69.192802,
        dso: 38.776786,
        dpo: 42.699229,
        cash_conversion_cycle: 65.270359
      }
    ],
    solvency: [
      {
        period: "2022",
        fiscal_year: 2022,
        debt_to_equity: 1.204082,
        interest_coverage_ratio: 4.241379
      },
      {
        period: "2023",
        fiscal_year: 2023,
        debt_to_equity: 1.181818,
        interest_coverage_ratio: 4.53125
      },
      {
        period: "2024",
        fiscal_year: 2024,
        debt_to_equity: 1.142857,
        interest_coverage_ratio: 5.171429
      }
    ]
  },
  dupont: [
    {
      period: "2022",
      fiscal_year: 2022,
      net_profit_margin: 0.095122,
      asset_turnover: 0.759259,
      equity_multiplier: 2.204082,
      roe_dupont: 0.159184
    },
    {
      period: "2023",
      fiscal_year: 2023,
      net_profit_margin: 0.096842,
      asset_turnover: 0.833333,
      equity_multiplier: 2.192308,
      roe_dupont: 0.176923
    },
    {
      period: "2024",
      fiscal_year: 2024,
      net_profit_margin: 0.103571,
      asset_turnover: 0.878431,
      equity_multiplier: 2.161017,
      roe_dupont: 0.19661
    }
  ],
  quality_of_earnings: {
    series: [
      {
        period: "2022",
        fiscal_year: 2022,
        quality_of_earnings_ratio: 0.884615,
        is_negative: false
      },
      {
        period: "2023",
        fiscal_year: 2023,
        quality_of_earnings_ratio: 1.173913,
        is_negative: false
      },
      {
        period: "2024",
        fiscal_year: 2024,
        quality_of_earnings_ratio: 1.043103,
        is_negative: false
      }
    ],
    latest: {
      period: "2024",
      fiscal_year: 2024,
      quality_of_earnings_ratio: 1.043103,
      is_negative: false
    },
    negative_streak: 0,
    alert_level: "green",
    message: "Operating cash flow supports reported net income."
  }
};
