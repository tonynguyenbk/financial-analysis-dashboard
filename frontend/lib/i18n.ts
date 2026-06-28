export type Language = "en" | "vi";
export type ThemeMode = "light" | "dark" | "system";

export const languageOptions: Array<{ value: Language; label: string }> = [
  { value: "en", label: "EN" },
  { value: "vi", label: "VI" }
];

export const themeOptions: Array<{ value: ThemeMode; labelKey: keyof typeof copy.en.theme }> = [
  { value: "light", labelKey: "light" },
  { value: "dark", labelKey: "dark" },
  { value: "system", labelKey: "system" }
];

export const localeByLanguage: Record<Language, string> = {
  en: "en-US",
  vi: "vi-VN"
};

export const copy = {
  en: {
    appName: "Financial Analysis Platform",
    appSubtitle: "Upload a PDF or Excel statement, review the normalized report, then run analysis.",
    language: "Language",
    themeLabel: "Theme",
    theme: {
      light: "Light",
      dark: "Dark",
      system: "System"
    },
    actions: {
      upload: "Upload report",
      uploading: "Standardizing",
      analyze: "Analyze",
      analyzing: "Analyzing",
      replaceFile: "Replace file"
    },
    errors: {
      parse: "Could not standardize this report.",
      analyze: "Could not analyze this report."
    },
    workflow: {
      uploadTitle: "Start with the user's report",
      uploadBody: "Upload the financial statement downloaded by the user. The platform first converts it into a structured report format before any analysis runs.",
      reviewTitle: "Standardized report",
      reviewBody: "Review the extracted line items and periods. Analysis is intentionally separate so the user can confirm the data first.",
      analysisTitle: "Analysis results",
      analysisBody: "Metrics, charts and explanations are calculated from the standardized report."
    },
    report: {
      company: "Company",
      source: "Source",
      currency: "Currency",
      unit: "Unit",
      periods: "Periods",
      metadata: "Extraction details",
      noMetadata: "No extraction notes were returned.",
      balanceSheet: "Balance sheet",
      incomeStatement: "Income statement",
      cashFlow: "Cash flow",
      lineItem: "Line item",
      notes: "Notes and disclosures",
      notesFallback: "No statement note text is available yet. When the PDF/Excel note parser is connected, this area can summarize accounting policies, debt notes, related-party notes and unusual items."
    },
    tabs: {
      summary: "Executive Summary",
      deepDive: "Deep Dive",
      benchmarking: "Benchmarking"
    },
    metrics: {
      current_assets: "Current assets",
      inventory: "Inventory",
      accounts_receivable: "Accounts receivable",
      total_assets: "Total assets",
      current_liabilities: "Current liabilities",
      accounts_payable: "Accounts payable",
      total_liabilities: "Total liabilities",
      total_equity: "Total equity",
      net_revenue: "Net revenue",
      gross_profit: "Gross profit",
      cost_of_goods_sold: "Cost of goods sold",
      ebit: "EBIT",
      interest_expense: "Interest expense",
      net_income: "Net income",
      operating_cash_flow: "Operating cash flow",
      gross_profit_margin: "Gross profit margin",
      net_profit_margin: "Net profit margin",
      roa: "ROA",
      roe: "ROE",
      current_ratio: "Current ratio",
      quick_ratio: "Quick ratio",
      cash_conversion_cycle: "Cash conversion cycle",
      debt_to_equity: "Debt / Equity",
      interest_coverage_ratio: "Interest coverage",
      quality_of_earnings_ratio: "Quality of earnings"
    },
    summary: {
      revenueAndMargin: "Revenue & Margin",
      qualityOfEarnings: "Quality of Earnings",
      streak: "Streak"
    },
    health: {
      profitability: "Profitability",
      liquidity: "Liquidity",
      efficiency: "Efficiency",
      leverage: "Leverage"
    },
    deepDive: {
      profitability: "Profitability",
      liquidityCcc: "Liquidity & CCC",
      dupont: "DuPont 3-Step",
      returnOnEquity: "Return on Equity",
      assetTurnover: "Asset Turnover",
      equityMultiplier: "Equity Multiplier"
    },
    benchmark: {
      title: "Industry Benchmark",
      metric: "Metric",
      company: "Company",
      industry: "Industry",
      gap: "Gap",
      signal: "Signal",
      ahead: "Ahead",
      watch: "Watch"
    },
    narrative: {
      title: "What the indicators mean",
      currentReading: "Current reading",
      disclosureTitle: "How notes should be used",
      profitability: "Profitability ratios show how much profit the company turns revenue and assets into. Weak margins usually point to pricing pressure, high production costs or scale that has not yet absorbed fixed costs.",
      liquidity: "Liquidity ratios show whether near-term assets can cover near-term obligations. A current ratio below 1.0 means short-term funding pressure deserves attention.",
      efficiency: "Efficiency metrics describe how quickly inventory, receivables and payables move through the business. A shorter cash conversion cycle usually means less cash is tied up in operations.",
      solvency: "Solvency ratios show how dependent the company is on debt and whether operating profit can cover interest. Negative equity makes ROE and Debt/Equity mathematically misleading, so the platform suppresses them.",
      qoe: "Quality of earnings compares operating cash flow with net income. If both cash flow and net income are negative, a positive ratio is not a healthy signal.",
      disclosure: "The financial statement notes should explain accounting policies, debt maturity, collateral, related-party balances and unusual one-off items. Those notes are the context for deciding whether a ratio is structural or temporary."
    }
  },
  vi: {
    appName: "Nền tảng phân tích báo cáo tài chính",
    appSubtitle: "Tải lên báo cáo PDF hoặc Excel, kiểm tra báo cáo đã chuẩn hóa, rồi mới chạy phân tích.",
    language: "Ngôn ngữ",
    themeLabel: "Giao diện",
    theme: {
      light: "Sáng",
      dark: "Tối",
      system: "Hệ thống"
    },
    actions: {
      upload: "Tải báo cáo",
      uploading: "Đang chuẩn hóa",
      analyze: "Phân tích",
      analyzing: "Đang phân tích",
      replaceFile: "Đổi file"
    },
    errors: {
      parse: "Không thể chuẩn hóa báo cáo này.",
      analyze: "Không thể phân tích báo cáo này."
    },
    workflow: {
      uploadTitle: "Bắt đầu từ báo cáo của người dùng",
      uploadBody: "Người dùng tải lên báo cáo tài chính đã tải từ Internet. Nền tảng chuẩn hóa dữ liệu trước, chưa chạy phân tích ngay.",
      reviewTitle: "Báo cáo đã chuẩn hóa",
      reviewBody: "Kiểm tra các kỳ và chỉ tiêu đã trích xuất. Phân tích được tách riêng để người dùng xác nhận dữ liệu trước.",
      analysisTitle: "Kết quả phân tích",
      analysisBody: "Các chỉ số, biểu đồ và phần diễn giải được tính từ báo cáo đã chuẩn hóa."
    },
    report: {
      company: "Doanh nghiệp",
      source: "Nguồn",
      currency: "Tiền tệ",
      unit: "Đơn vị",
      periods: "Kỳ báo cáo",
      metadata: "Thông tin trích xuất",
      noMetadata: "Chưa có ghi chú trích xuất.",
      balanceSheet: "Bảng cân đối kế toán",
      incomeStatement: "Báo cáo kết quả kinh doanh",
      cashFlow: "Báo cáo lưu chuyển tiền tệ",
      lineItem: "Chỉ tiêu",
      notes: "Thuyết minh báo cáo",
      notesFallback: "Chưa có nội dung thuyết minh được trích xuất. Khi parser thuyết minh PDF/Excel được kết nối, khu vực này có thể tóm tắt chính sách kế toán, nợ vay, bên liên quan và các khoản mục bất thường."
    },
    tabs: {
      summary: "Tóm tắt điều hành",
      deepDive: "Phân tích sâu",
      benchmarking: "So sánh ngành"
    },
    metrics: {
      current_assets: "Tài sản ngắn hạn",
      inventory: "Hàng tồn kho",
      accounts_receivable: "Phải thu khách hàng",
      total_assets: "Tổng tài sản",
      current_liabilities: "Nợ ngắn hạn",
      accounts_payable: "Phải trả người bán",
      total_liabilities: "Tổng nợ phải trả",
      total_equity: "Vốn chủ sở hữu",
      net_revenue: "Doanh thu thuần",
      gross_profit: "Lợi nhuận gộp",
      cost_of_goods_sold: "Giá vốn hàng bán",
      ebit: "EBIT",
      interest_expense: "Chi phí lãi vay",
      net_income: "Lợi nhuận sau thuế",
      operating_cash_flow: "Dòng tiền HĐKD",
      gross_profit_margin: "Biên lợi nhuận gộp",
      net_profit_margin: "Biên lợi nhuận ròng",
      roa: "ROA",
      roe: "ROE",
      current_ratio: "Hệ số thanh toán hiện hành",
      quick_ratio: "Hệ số thanh toán nhanh",
      cash_conversion_cycle: "Chu kỳ chuyển đổi tiền mặt",
      debt_to_equity: "Nợ / Vốn chủ sở hữu",
      interest_coverage_ratio: "Khả năng trả lãi",
      quality_of_earnings_ratio: "Chất lượng lợi nhuận"
    },
    summary: {
      revenueAndMargin: "Doanh thu & biên lợi nhuận",
      qualityOfEarnings: "Chất lượng lợi nhuận",
      streak: "Số kỳ liên tiếp"
    },
    health: {
      profitability: "Sinh lời",
      liquidity: "Thanh khoản",
      efficiency: "Hiệu quả",
      leverage: "Đòn bẩy"
    },
    deepDive: {
      profitability: "Khả năng sinh lời",
      liquidityCcc: "Thanh khoản & CCC",
      dupont: "DuPont 3 bước",
      returnOnEquity: "Tỷ suất sinh lời VCSH",
      assetTurnover: "Vòng quay tài sản",
      equityMultiplier: "Đòn bẩy tài sản"
    },
    benchmark: {
      title: "So sánh với ngành",
      metric: "Chỉ tiêu",
      company: "Doanh nghiệp",
      industry: "Ngành",
      gap: "Chênh lệch",
      signal: "Tín hiệu",
      ahead: "Tốt hơn",
      watch: "Theo dõi"
    },
    narrative: {
      title: "Ý nghĩa các chỉ tiêu",
      currentReading: "Diễn giải hiện tại",
      disclosureTitle: "Cách sử dụng thuyết minh",
      profitability: "Nhóm sinh lời cho biết doanh nghiệp chuyển doanh thu và tài sản thành lợi nhuận tốt đến đâu. Biên lợi nhuận yếu thường phản ánh áp lực giá bán, chi phí sản xuất cao hoặc quy mô chưa đủ hấp thụ chi phí cố định.",
      liquidity: "Nhóm thanh khoản cho biết tài sản ngắn hạn có đủ bù nghĩa vụ ngắn hạn hay không. Hệ số thanh toán hiện hành dưới 1,0 là tín hiệu cần theo dõi áp lực vốn lưu động.",
      efficiency: "Nhóm hiệu quả vận hành mô tả tốc độ luân chuyển hàng tồn kho, phải thu và phải trả. Chu kỳ chuyển đổi tiền mặt càng ngắn thường càng ít tiền bị khóa trong vận hành.",
      solvency: "Nhóm đòn bẩy cho biết mức phụ thuộc vào nợ và khả năng EBIT chi trả lãi vay. Khi vốn chủ sở hữu âm, ROE và Nợ/VCSH dễ gây hiểu nhầm nên nền tảng trả về rỗng.",
      qoe: "Chất lượng lợi nhuận so sánh dòng tiền HĐKD với lợi nhuận sau thuế. Nếu cả dòng tiền và lợi nhuận đều âm, tỷ lệ dương không nên được xem là tín hiệu khỏe.",
      disclosure: "Thuyết minh báo cáo tài chính cần được dùng để hiểu chính sách kế toán, kỳ hạn nợ vay, tài sản bảo đảm, số dư bên liên quan và các khoản bất thường. Đây là bối cảnh để đánh giá chỉ tiêu là vấn đề dài hạn hay chỉ tạm thời."
    }
  }
} as const;
