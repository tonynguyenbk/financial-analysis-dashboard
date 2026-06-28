# THÔNG SỐ KỸ THUẬT VÀ KIẾN TRÚC DỰ ÁN (PRD)
## DỰ ÁN: PHẦN MỀM DASHBOARD PHÂN TÍCH TÀI CHÍNH (FINANCIAL ANALYSIS DASHBOARD)

Tài liệu này tổng hợp toàn bộ phân tích, kiến trúc hệ thống, danh mục công nghệ và khung chỉ số tài chính đã được thống nhất. Mục tiêu nhằm làm dữ liệu đầu vào (Context) chất lượng cao cho AI Agent (Claude Code/GPT) để tiến hành sinh mã nguồn và xây dựng dự án tự động.

---

## 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)
* **Mục tiêu:** Xây dựng ứng dụng Web Dashboard phân tích báo cáo tài chính (BCTC) doanh nghiệp tự động.
* **Đầu vào (Input):** File BCTC định dạng PDF (giai đoạn 1: cào/tải từ internet) và file Excel/XLSX (giai đoạn 2: dữ liệu chuẩn của doanh nghiệp nội bộ).
* **Đầu ra (Output):** Dashboard trực quan hóa các chỉ số tài chính theo mô hình 4 trụ cột, phân tích DuPont và đánh giá chất lượng dòng tiền.

---

## 2. KIẾN TRÚC HỆ THỐNG & LUỒNG DỮ LIỆU (SYSTEM ARCHITECTURE & WORKFLOW)

Hệ thống được thiết kế theo kiến trúc phân lớp (Layered Architecture) kết hợp **Strategy Pattern** ở tầng tiếp nhận dữ liệu để đảm bảo tính mở rộng linh hoạt từ PDF sang Excel mà không ảnh hưởng tới lõi tính toán.

```
[User Input: PDF / Excel]
         │
         ▼
┌────────────────────────────────────────┐
│ 1. TẦNG TIẾP NHẬN (Parser Factory)     │
│    - Kiểm tra định dạng file (Extension)│
│    - Điều hướng sang Engine phù hợp     │
└──────────────────┬─────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌─────────────────┐ ┌──────────────────┐
│ PDF Parser      │ │ Excel Parser     │
│ (AI LLM Vision) │ │ (Pandas/openpyxl)│
└────────┬────────┘ └────────┬─────────┘
         │                   │
         └─────────┬─────────┘
                   ▼
┌────────────────────────────────────────┐
│ 2. CHUẨN HÓA DỮ LIỆU (Normalization)   │
│    - Ánh xạ từ khóa đồng nghĩa (Mapping)│
│    - Xuất ra chuỗi cấu trúc JSON chuẩn  │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ 3. LÕI TÍNH TOÁN (Calculation Engine)   │
│    - Tiếp nhận JSON chuẩn              │
│    - Chạy thuật toán xử lý số liệu     │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ 4. TẦNG HIỂN THỊ (Visualization UI)    │
│    - API endpoints (FastAPI)           │
│    - React/Next.js UI & Charts         │
└────────────────────────────────────────┘
```

### Các bước trong Workflow:
1.  **Parser Factory (Tầng tiếp nhận):** Kiểm tra loại file tải lên. Nếu là `.pdf`, kích hoạt *PDF Parser Engine*. Nếu là `.xlsx` / `.xls`, kích hoạt *Excel Parser Engine*.
2.  **Data Normalization (Chuẩn hóa):** Bất kể nguồn vào nào, dữ liệu thô sau khi bóc tách sẽ đi qua một bộ từ điển ánh xạ (Mapping Dictionary) nhằm quy đổi các thuật ngữ kế toán khác nhau (Ví dụ: *"Doanh thu thuần về bán hàng..."* hay *"Doanh thu thuần"*) về một mã định danh duy nhất (Ví dụ: `NET_REVENUE`). Đầu ra của tầng này là một cấu trúc JSON đồng nhất.
3.  **Calculation Engine (Lõi tính toán):** Chịu trách nhiệm thực hiện các công thức toán học/tài chính từ chuỗi JSON đầu vào để tạo ra các chỉ số đầu ra. Tầng này hoàn toàn độc lập với định dạng file gốc.
4.  **Visualization (Hiển thị):** Cung cấp dữ liệu qua API để Frontend vẽ biểu đồ và bảng số liệu.

---

## 3. DANH MỤC CÔNG NGHỆ (TECH STACK)

### Frontend (Giao diện người dùng)
* **Framework:** `React.js` hoặc `Next.js` (Ưu tiên Next.js để tối ưu định tuyến và quản lý state).
* **Style & UI Components:** `Tailwind CSS` phối hợp với `Shadcn/ui` hoặc `Ant Design` (Xây dựng nhanh các widget cho dashboard).
* **Data Visualization (Biểu đồ):** `Apache ECharts` (Khuyên dùng cho dữ liệu tài chính lớn nhờ hiệu năng cao và đa dạng biểu đồ) hoặc `Recharts`.

### Backend (Logic & Tính toán số liệu)
* **Framework:** `FastAPI` (Python) - Đảm bảo tốc độ xử lý nhanh, nhẹ, tài liệu hóa API tự động bằng Swagger.
* **Data Processing:** `Pandas` và `NumPy` - Thư viện xử lý dữ liệu dạng bảng và tính toán ma trận mạnh mẽ nhất của Python.

### Data Ingestion (Trích xuất dữ liệu)
* **Xử lý PDF (Phức tạp):** Tích hợp **LLM Vision API** (như `GPT-4o mini` hoặc `Claude 3.5 Sonnet`). Viết Prompt chặt chẽ định dạng dữ liệu đầu ra là JSON để xử lý triệt để vấn đề lệch dòng, lệch cột của file scan. (Dự phòng truyền thống: `pdfplumber`, `Camelot`).
* **Xử lý Excel:** Thư viện `openpyxl` và tích hợp hàm `pandas.read_excel()`.

### Cơ sở dữ liệu (Database & Caching)
* **Database chính:** `PostgreSQL` - Đảm bảo tính toàn vẹn dữ liệu kế toán (ACID), hỗ trợ lưu trữ dữ liệu có cấu trúc cao.
* **Caching:** `Redis` - Lưu trữ các chỉ số tài chính đã tính toán xong của các mã doanh nghiệp phổ biến nhằm tăng tốc độ tải trang dashboard.

---

## 4. KHUNG CHỈ SỐ TÀI CHÍNH ĐẦU RA (FINANCIAL METRICS FRAMEWORK)

Hệ thống phải triển khai đầy đủ bộ khung phân tích logic dưới đây để thể hiện toàn vẹn mối quan hệ nhân quả trong tài chính:

### Thống kê 4 Trụ cột Cốt lõi (The 4 Pillars)
1.  **Khả năng sinh lời (Profitability):**
    * *Biên lợi nhuận gộp (Gross Profit Margin):* Lợi nhuận gộp / Doanh thu thuần.
    * *Biên lợi nhuận thuần (Net Profit Margin):* Lợi nhuận sau thuế / Doanh thu thuần.
    * *ROA (Tỷ suất sinh lời trên tài sản):* Lợi nhuận sau thuế / Tổng tài sản bình quân.
    * *ROE (Tỷ suất sinh lời trên vốn chủ sở hữu):* Lợi nhuận sau thuế / Vốn chủ sở hữu bình quân.
2.  **Khả năng thanh toán (Liquidity):**
    * *Hệ số thanh toán hiện hành (Current Ratio):* Tài sản ngắn hạn / Nợ ngắn hạn.
    * *Hệ số thanh toán nhanh (Quick Ratio):* (Tài sản ngắn hạn - Hàng tồn kho) / Nợ ngắn hạn.
3.  **Hiệu quả hoạt động (Efficiency):**
    * *Số ngày vòng quay hàng tồn kho (DIO):* (Hàng tồn kho bình quân / Giá vốn hàng bán) * 365.
    * *Số ngày phải thu khách hàng (DSO):* (Phải thu khách hàng bình quân / Doanh thu thuần) * 365.
    * *Chu kỳ tiền mặt (Cash Conversion Cycle - CCC):* DIO + DSO - DPO (Số ngày phải trả nhà cung cấp).
4.  **Sức khỏe tài chính & Đòn bẩy (Solvency/Leverage):**
    * *Tỷ lệ Nợ / Vốn chủ sở hữu (D/E):* Tổng nợ phải trả / Vốn chủ sở hữu.
    * *Hệ số khả năng trả lãi tiền vay (Interest Coverage Ratio):* EBIT / Chi phí lãi vay.

### Lõi Phân tích Nâng cao (Advanced Core Analysis)
* **Sơ đồ phân rã DuPont (3 bước):**
    $$	ext{ROE} = 	ext{Biên lợi nhuận thuần (NPM)} 	imes 	ext{Vòng quay tài sản (Asset Turnover)} 	imes 	ext{Đòn bẩy tài chính (Equity Multiplier)}$$
    *(Yêu cầu UI: Hiển thị dạng sơ đồ cây phân rã để người dùng thấy rõ biến động của ROE bắt nguồn từ đâu).*
* **Kiểm tra chất lượng lợi nhuận (Quality of Earnings):**
    * *Tỷ lệ:* Dòng tiền từ hoạt động kinh doanh (CFO) / Lợi nhuận sau thuế (Net Income).
    * *Logic cảnh báo:* Nếu tỷ lệ < 0 trong nhiều kỳ liên tiếp -> Kích hoạt cảnh báo Đỏ (Doanh nghiệp bị đọng vốn, rủi ro "chết trên đống lãi").

---

## 5. ĐỊNH HƯỚNG GIAO DIỆN VÀ TRẢI NGHIỆM (UX/UI DESIGN)

Áp dụng nguyên lý thiết kế **"Tổng quan trước, Chi tiết sau"**:
1.  **Tab 1 - Executive Summary:** Hiển thị 3 chỉ số lớn (Doanh thu, Lợi nhuận, Dòng tiền). Sử dụng hệ thống đèn báo hiệu sức khỏe doanh nghiệp (Xanh/Vàng/Đỏ) cho 4 trụ cột tài chính dựa trên ngưỡng an toàn được thiết lập.
2.  **Tab 2 - Deep Dive (Phân tích sâu):** Chứa đồ thị đường (Line Chart) thể hiện xu hướng của các chỉ số tài chính qua các năm/quý. Khu vực hiển thị cây phân tích DuPont.
3.  **Tab 3 - Benchmarking (So sánh ngành):** Bảng so sánh các chỉ số của doanh nghiệp hiện tại với chỉ số trung bình ngành hoặc đối thủ cạnh tranh trực tiếp cùng quy mô.

---

## 6. HƯỚNG DẪN DÀNH CHO CLAUDE CODE (PROMPT COMMAND TO AI AGENT)

*Copy đoạn prompt mẫu dưới đây khi đưa file này vào Claude Code:*

> "I have provided the `financial_dashboard_spec.md` which contains the PRD, architecture, tech stack, and financial formulas for a Financial Analysis Dashboard. Please act as a Senior Full-Stack Engineer and Solution Architect. 
> Your task is to initialize the project structure based on this document. Start by setting up the Backend using Python FastAPI, incorporating Pandas for the calculation engine, and mock the LLM Vision API parsing behavior into a standardized JSON format. Then, initialize the Frontend workspace using Next.js, Tailwind CSS, and Apache ECharts. Ensure the Strategy Pattern structure for input parsing (PDF vs Excel) is properly stubbed out in the backend code. Let's start step by step."
