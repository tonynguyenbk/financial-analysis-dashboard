from datetime import date

from app.main import app
from app.parsers.normalization import normalize_label
from app.parsers.pdf_parser import PDFParser
from fastapi.testclient import TestClient


def test_pdf_parse_endpoint_accepts_text_layer_pdf():
    client = TestClient(app)
    pdf_bytes = _simple_pdf(
        [
            "2022 2023 2024",
            "current assets 470,000 520,000 580,000",
            "inventory 126,000 140,000 155,000",
            "accounts receivable 98,000 110,000 128,000",
            "total assets 1,080,000 1,200,000 1,350,000",
            "current liabilities 235,000 260,000 295,000",
            "accounts payable 76,000 85,000 97,000",
            "total liabilities 590,000 650,000 720,000",
            "total equity 490,000 550,000 630,000",
            "net revenue 820,000 950,000 1,120,000",
            "gross profit 238,000 280,000 342,000",
            "cost of goods sold 582,000 670,000 778,000",
            "ebit 123,000 145,000 181,000",
            "interest expense 29,000 32,000 35,000",
            "net income 78,000 92,000 116,000",
            "operating cash flow 69,000 108,000 121,000",
        ]
    )

    response = client.post(
        "/api/v1/parse",
        files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["source_type"] == "pdf"
    assert len(payload["periods"]) == 3
    assert payload["periods"][-1]["income_statement"]["net_revenue"] == 1120000.0
    assert payload["metadata"]["extracted_page_count"] == 1
    assert payload["metadata"]["extracted_pages"][0]["page"] == 1
    assert "current assets" in payload["metadata"]["extracted_pages"][0]["text"]


def test_pdf_text_records_are_normalized():
    parser = PDFParser()
    text = """
    2022 2023 2024
    current assets 470,000 520,000 580,000
    inventory 126,000 140,000 155,000
    accounts receivable 98,000 110,000 128,000
    total assets 1,080,000 1,200,000 1,350,000
    current liabilities 235,000 260,000 295,000
    accounts payable 76,000 85,000 97,000
    total liabilities 590,000 650,000 720,000
    total equity 490,000 550,000 630,000
    net revenue 820,000 950,000 1,120,000
    gross profit 238,000 280,000 342,000
    cost of goods sold 582,000 670,000 778,000
    ebit 123,000 145,000 181,000
    interest expense 29,000 32,000 35,000
    net income 78,000 92,000 116,000
    operating cash flow 69,000 108,000 121,000
    """

    records = parser._extract_records_from_text(text)

    assert len(records) == 45
    assert {
        "metric": "NET_REVENUE",
        "period": "2024",
        "value": 1120000.0,
    } in records
    assert {
        "metric": "OPERATING_CASH_FLOW",
        "period": "2023",
        "value": 108000.0,
    } in records


def test_vietnamese_d_stroke_is_normalized_for_ocr_labels():
    parser = PDFParser()
    text = """
    So cuoi nam So dau nam
    23 Trong đó: Chi phí đi vay (18.017.359) (17.031.267)
    30 | 11. Lỗ thuần từ hoạt động kinh doanh (83.604.752) (50.901.809)
    """

    records = parser._extract_records_from_text(text, ["2025", "2024"])

    assert normalize_label("Lỗ thuần từ hoạt động kinh doanh") == "lo thuan tu hoat dong kinh doanh"
    assert {"metric": "INTEREST_EXPENSE", "period": "2025", "value": -18017359.0} in records
    assert {"metric": "EBIT", "period": "2024", "value": -50901809.0} in records


def test_default_periods_ignore_future_years_from_pdf_noise():
    parser = PDFParser()
    report_year = date.today().year - 1
    future_year = date.today().year + 2
    text = f"""
    Legal schedule runs through {future_year}.
    Bao cao tai chinh cho nam ket thuc ngay 31 thang 12 nam {report_year}.
    Nam truoc {report_year - 1}.
    """

    assert parser._infer_default_periods("financial-report.pdf", text) == [
        str(report_year),
        str(report_year - 1),
    ]


def test_ocr_page_count_zero_means_process_all_pages():
    parser = PDFParser()

    assert parser._ocr_page_count(total_pages=79, max_pages=0) == 79
    assert parser._ocr_page_count(total_pages=79, max_pages=-1) == 79
    assert parser._ocr_page_count(total_pages=79, max_pages=25) == 25


def test_clean_ocr_text_repairs_common_vietnamese_financial_headings():
    parser = PDFParser()
    text = "\n".join(
        [
            "BANG CAN BOI KE TOÁN HỢP NHÁT",
            "BÁO CÁO KÉT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHÁT",
            "Báo cáo tài chính hợp nhắt",
            "TÀI SÄN",
            "Cổ phan",
            "Don vi tính: tiêu VND",
        ]
    )

    cleaned = parser._clean_ocr_text(text)

    assert "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT" in cleaned
    assert "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT" in cleaned
    assert "Báo cáo tài chính hợp nhất" in cleaned
    assert "TÀI SẢN" in cleaned
    assert "Cổ phần" in cleaned
    assert "Đơn vị tính: triệu VND" in cleaned


def test_report_navigation_uses_table_of_contents_and_resolves_actual_pages():
    parser = PDFParser()
    pages = [
        "Cover page",
        """
        MỤC LỤC
        Trang
        Thông tin chung 1-2
        Báo cáo kiểm toán độc lập 4-5
        Bảng cân đối kế toán hợp nhất 6-9
        Báo cáo kết quả hoạt động kinh doanh hợp nhất 10 - 11
        Thuyết minh báo cáo tài chính hợp nhất 18 - 76
        """,
        "THÔNG TIN CHUNG\nCÔNG TY",
        "THÔNG TIN CHUNG (tiếp theo)",
        "BÁO CÁO CỦA BAN GIÁM ĐỐC",
        "BÁO CÁO KIỂM TOÁN ĐỘC LẬP",
        "BÁO CÁO KIỂM TOÁN ĐỘC LẬP (tiếp theo)",
        "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT",
        "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT (tiếp theo)",
        "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT (tiếp theo)",
        "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT (tiếp theo)",
        "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT",
        "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT (tiếp theo)",
        "BÁO CÁO LƯU CHUYỂN TIỀN TỆ HỢP NHẤT",
        "BÁO CÁO LƯU CHUYỂN TIỀN TỆ HỢP NHẤT (tiếp theo)",
        "BÁO CÁO LƯU CHUYỂN TIỀN TỆ HỢP NHẤT (tiếp theo)",
        "Other page",
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT",
    ]

    navigation = parser._build_report_navigation(pages)
    by_title = {normalize_label(item["title"]): item for item in navigation}

    assert by_title["thong tin chung"]["page"] == 3
    assert by_title["bao cao kiem toan doc lap"]["page"] == 6
    assert by_title["bang can doi ke toan hop nhat"]["page"] == 8
    assert by_title["bao cao ket qua hoat dong kinh doanh hop nhat"]["page"] == 12
    assert "thuyet minh bao cao tai chinh hop nhat" not in by_title


def test_statement_tables_extract_main_numeric_statement_rows():
    parser = PDFParser()
    pages = [
        """
        BANG CAN DOI KE TOAN HOP NHAT
        100 A. TAI SAN NGAN HAN 89.151.874 93.783.676
        110 1. Tien va cac khoan tuong duong tien 5 2.164.948 4.160.316
        """,
        """
        BAO CAO KET QUA HOAT DONG KINH DOANH HOP NHAT
        01 1. Doanh thu ban hang va cung cap dich vu 29.1 99.365.981 53.169.842
        60 17. Lo sau thue TNDN (62.083.550) (31.935.669)
        """,
        """
        BAO CAO LUU CHUYEN TIEN TE HOP NHAT
        01 Loi nhuan truoc thue (62.028.370) (31.880.489)
        20 Luu chuyen tien thuan tu hoat dong kinh doanh (18.617.631) (22.880.537)
        """,
    ]

    tables = parser._build_statement_tables(pages, ["2025", "2024"])
    by_key = {table["key"]: table for table in tables}

    assert [column["key"] for column in by_key["financial_position"]["columns"][:3]] == ["label", "code", "note"]
    assert by_key["financial_position"]["columns"][3]["label"] == "31/12/2025"
    assert by_key["financial_position"]["columns"][4]["label"] == "31/12/2024"
    assert by_key["income_statement"]["columns"][3]["label"] == "2025"
    assert by_key["cash_flow"]["columns"][4]["label"] == "2024"
    assert by_key["financial_position"]["rows"][0]["code"] == "100"
    assert by_key["financial_position"]["rows"][0]["values"]["2025"] == 89151874.0
    assert by_key["financial_position"]["rows"][1]["note"] == "5"
    assert by_key["income_statement"]["rows"][0]["note"] == "29.1"
    assert by_key["income_statement"]["rows"][1]["values"]["2024"] == -31935669.0
    assert by_key["cash_flow"]["rows"][1]["code"] == "20"
    assert by_key["cash_flow"]["rows"][1]["values"]["2025"] == -18617631.0


def test_statement_tables_prefer_statement_header_periods_over_filing_year_noise():
    parser = PDFParser()
    pages = [
        """
        CONSOLIDATED BALANCE SHEET
        Code Note 31 December 2025 VND 31 December 2024 VND
        100 CURRENT ASSETS 58.137.438.254.000 45.535.942.846.000
        440 TOTAL RESOURCES 88.141.991.634.625 71.999.995.678.620
        """,
    ]

    tables = parser._build_statement_tables(pages, ["2026", "2025"])
    table = next(table for table in tables if table["key"] == "financial_position")

    assert table["columns"][3]["key"] == "2025"
    assert table["columns"][3]["label"] == "31/12/2025"
    assert table["columns"][4]["key"] == "2024"
    assert table["columns"][4]["label"] == "31/12/2024"
    assert table["rows"][0]["values"]["2025"] == 58137438254000.0


def test_primary_statement_pages_are_targeted_from_table_of_contents():
    parser = PDFParser()
    pages = [
        "Cover page",
        """
        MUC LUC
        Trang
        Thong tin chung 1-2
        Bang can doi ke toan hop nhat 6-9
        Bao cao ket qua hoat dong kinh doanh hop nhat 10-11
        Bao cao luu chuyen tien te hop nhat 12-14
        Thuyet minh bao cao tai chinh hop nhat 18-76
        """,
        "THONG TIN CHUNG",
        "THONG TIN CHUNG tiep theo",
        """
        Trang
        Bang can doi ke toan hop nhat 6-9
        Bao cao ket qua hoat dong kinh doanh hop nhat 10-11
        Bao cao luu chuyen tien te hop nhat 12-14
        Thuyet minh bao cao tai chinh hop nhat 18-76
        """,
        "Bao cao kiem toan doc lap",
        "Bao cao kiem toan doc lap tiep theo",
        "BANG CAN DOI KE TOAN HOP NHAT",
        "BANG CAN DOI KE TOAN HOP NHAT tiep theo",
        "BANG CAN DOI KE TOAN HOP NHAT tiep theo",
        "BANG CAN DOI KE TOAN HOP NHAT tiep theo",
        "BAO CAO KET QUA HOAT DONG KINH DOANH HOP NHAT",
        "BAO CAO KET QUA HOAT DONG KINH DOANH HOP NHAT tiep theo",
        "BAO CAO LUU CHUYEN TIEN TE HOP NHAT",
        "BAO CAO LUU CHUYEN TIEN TE HOP NHAT tiep theo",
        "BAO CAO LUU CHUYEN TIEN TE HOP NHAT tiep theo",
    ]

    indexes = parser._target_statement_page_indexes(pages, len(pages))

    assert set(range(7, 16)).issubset(indexes)
    assert 17 not in indexes


def test_toc_resolution_prefers_common_offset_over_early_title_mentions():
    parser = PDFParser()
    pages = [
        "Cover page",
        """
        MUC LUC
        Trang
        Thong tin chung 1-2
        Bang can doi ke toan hop nhat 6-9
        Bao cao ket qua hoat dong kinh doanh hop nhat 10-11
        Bao cao luu chuyen tien te hop nhat 12-14
        """,
        "THONG TIN CHUNG",
        "THONG TIN CHUNG tiep theo",
        """
        Bao cao cua Ban Giam doc
        Bang can doi ke toan hop nhat
        Bao cao ket qua hoat dong kinh doanh hop nhat
        Bao cao luu chuyen tien te hop nhat
        """,
        "Bao cao kiem toan doc lap",
        "Bao cao kiem toan doc lap tiep theo",
        "BANG CAN DOI KE TOAN HOP NHAT",
        "BANG CAN DOI KE TOAN HOP NHAT tiep theo",
        "BANG CAN DOI KE TOAN HOP NHAT tiep theo",
        "BANG CAN DOI KE TOAN HOP NHAT tiep theo",
        "BAO CAO KET QUA HOAT DONG KINH DOANH HOP NHAT",
        "BAO CAO KET QUA HOAT DONG KINH DOANH HOP NHAT tiep theo",
        "BAO CAO LUU CHUYEN TIEN TE HOP NHAT",
        "BAO CAO LUU CHUYEN TIEN TE HOP NHAT tiep theo",
        "BAO CAO LUU CHUYEN TIEN TE HOP NHAT tiep theo",
    ]

    resolved = parser._resolve_toc_navigation_pages(parser._extract_toc_navigation_entries(pages), pages)
    by_title = {normalize_label(item["title"]): item for item in resolved}

    assert by_title["bao cao ket qua hoat dong kinh doanh hop nhat"]["page"] == 12
    assert by_title["bao cao luu chuyen tien te hop nhat"]["page"] == 14


def test_statement_rows_strip_report_header_noise_from_cash_flow_lines():
    parser = PDFParser()
    line = (
        "11 Cong ty Co phan Sua Viet Nam va cac cong ty con Bao cao luu chuyen tien te hop nhat "
        "cho nam ket thuc ngay 31 thang 12 nam 2025 Mau B 03 - DN/HN Ban hanh theo Thong tu "
        "so 202/2014/TT-BTC cua Bo Tai chinh Ma Thuyet 2025 2024 so minh VND VND "
        "LUU CHUYEN TIEN TU HOAT DONG DAU TU Tien chi mua tai san co dinh va tai san dai han khac "
        "21 -1.762.010.725.342 -1.741.501.711.051"
    )

    row = parser._parse_statement_table_row(line, 13, ["2025", "2024"], "cash_flow")

    assert row is not None
    assert row["code"] == "11"
    assert row["note"] == "21"
    assert row["label"] == "Tien chi mua tai san co dinh va tai san dai han khac"
    assert row["values"]["2025"] == -1762010725342.0


def test_statement_tables_use_toc_page_ranges_before_heading_scan():
    parser = PDFParser()
    pages = [
        "Cover",
        """
        MUC LUC
        Bang can doi ke toan hop nhat 6-7
        Bao cao ket qua hoat dong kinh doanh hop nhat 8
        Bao cao luu chuyen tien te hop nhat 9
        """,
        "Other",
        "Other",
        "Other",
        "100 TAI SAN NGAN HAN 1.200.000 1.100.000",
        "270 TONG CONG TAI SAN 9.200.000 8.100.000",
        "01 Doanh thu ban hang va cung cap dich vu 99.365.981 53.169.842",
        "20 Luu chuyen tien thuan tu hoat dong kinh doanh 18.617.631 22.880.537",
    ]

    tables = parser._build_statement_tables(pages, ["2025", "2024"])
    by_key = {table["key"]: table for table in tables}

    assert set(by_key) == {"financial_position", "income_statement", "cash_flow"}
    assert by_key["financial_position"]["pages"] == [6, 7]
    assert by_key["income_statement"]["pages"] == [8]
    assert by_key["cash_flow"]["pages"] == [9]


def test_statement_rows_use_previous_label_when_value_line_only_has_formula():
    parser = PDFParser()
    pages = [
        """
        BANG CAN DOI KE TOAN HOP NHAT
        TAI SAN NGAN HAN
        (100 = 110 + 120 + 130 + 140 + 150) 100 36.261.180.908.033 37.553.650.065.098
        """,
    ]

    rows = parser._extract_statement_table_rows(pages, [0], ["2025", "2024"], "financial_position")

    assert rows[0]["code"] == "100"
    assert rows[0]["label"] == "TAI SAN NGAN HAN"
    assert rows[0]["values"]["2025"] == 36261180908033.0


def test_label_first_rows_repair_embedded_code_from_ocr_tail():
    parser = PDFParser()
    line = "Gia von hang ban va dich vu cung cap 11 VIL2 37.436.412.561696 36.192.433.205.321"

    row = parser._parse_statement_table_row(line, 10, ["2025", "2024"], "income_statement")

    assert row is not None
    assert row["code"] == "11"
    assert row["note"] == "VIL2"
    assert row["label"] == "Gia von hang ban va dich vu cung cap"


def test_statement_rows_repair_split_amount_groups_without_moving_them_to_note():
    parser = PDFParser()
    line = "02 Khau hao TSCD 2.116.245.292 358 2.095.159.644.941"

    row = parser._parse_statement_table_row(line, 12, ["2025", "2024"], "cash_flow")

    assert row is not None
    assert row["code"] == "02"
    assert row["note"] is None
    assert row["values"]["2025"] == 2116245292358.0
    assert row["values"]["2024"] == 2095159644941.0


def test_statement_rows_do_not_extract_formula_numbers_as_notes():
    parser = PDFParser()
    line = "50 Luu chuyen tien thuan trong ky (50 = 20 + 30 + 40) 1.312.623.193.814 1.044.198.899.933"

    row = parser._parse_statement_table_row(line, 14, ["2025", "2024"], "cash_flow")

    assert row is not None
    assert row["code"] == "50"
    assert row["note"] is None
    assert "40" not in row["label"]
    assert row["values"]["2025"] == 1312623193814.0


def test_statement_rows_keep_total_assets_with_table_border_prefix():
    parser = PDFParser()
    pages = [
        """
        BANG CAN DOI KE TOAN HOP NHAT
        | 270 TONG CONG TAI SAN 221.761.361 212.972.002
        300 NO PHAI TRA 213.360.072 202.010.518
        """,
    ]

    rows = parser._extract_statement_table_rows(pages, [0], ["2025", "2024"], "financial_position")
    by_code = {row["code"]: row for row in rows}

    assert by_code["270"]["label"] == "TONG CONG TAI SAN"
    assert by_code["270"]["values"]["2025"] == 221761361.0
    assert by_code["270"]["values"]["2024"] == 212972002.0


def test_statement_rows_prefer_real_total_assets_over_same_page_noise():
    parser = PDFParser()
    pages = [
        """
        BANG CAN DOI KE TOAN HOP NHAT
        270 Loi the thuong mai 19 37.923 46.580
        — 270 TONG CONG TAI SAN 221.761.361 212.972.002
        300 NO PHAI TRA 213.360.072 202.010.518
        """,
    ]

    rows = parser._extract_statement_table_rows(pages, [0], ["2025", "2024"], "financial_position")
    row = next(row for row in rows if row["code"] == "270")

    assert row["label"] == "TONG CONG TAI SAN"
    assert row["values"]["2025"] == 221761361.0
    assert row["values"]["2024"] == 212972002.0


def test_statement_tables_reconstruct_missing_total_assets_before_liabilities():
    parser = PDFParser()
    pages = [
        """
        BANG CAN DOI KE TOAN HOP NHAT
        254 Du phong dau tu tai chinh dai han (937.268) -
        255 Dau tu nam giu den ngay dao han 5.312 5.312
        261 Chi phi tra truoc dai han 802.581 1.848.632
        289 Loi the thuong mai 37.923 46.580
        300 NO PHAI TRA 213.360.072 202.010.518
        400 VON CHU SO HUU 8.401.289 10.961.484
        """,
    ]

    tables = parser._build_statement_tables(pages, ["2025", "2024"])
    inserted = parser._ensure_financial_position_total_assets_row(tables, [])
    table = next(table for table in tables if table["key"] == "financial_position")
    codes = [row["code"] for row in table["rows"]]
    row = next(row for row in table["rows"] if row["code"] == "270")

    assert inserted is True
    assert codes.index("270") < codes.index("300")
    assert row["reconstructed"] is True
    assert row["values"]["2025"] == 221761361.0
    assert row["values"]["2024"] == 212972002.0


def test_statement_tables_keep_alphanumeric_equity_breakdown_codes():
    parser = PDFParser()
    pages = [
        """
        BANG CAN DOI KE TOAN HOP NHAT
        400 VON CHU SO HUU 8.401.289 10.961.484
        410 Von chu so huu 28 8.401.289 10.961.484
        421 Loi nhuan sau thue chua phan phoi (81.992.839) (129.786.304)
        421a - Lo luy ke den cuoi nam truoc (19.934.603) (100.737.591)
        421b - Lo nam nay (62.058.236) (29.048.713)
        429 Loi ich co dong khong kiem soat (24.895) 419
        440 TONG CONG NGUON VON 221.761.361 212.972.002
        """,
    ]

    tables = parser._build_statement_tables(pages, ["2025", "2024"])
    table = next(table for table in tables if table["key"] == "financial_position")
    by_code = {row["code"]: row for row in table["rows"]}

    assert {"421", "421a", "421b"}.issubset(by_code)
    assert by_code["421a"]["parent_code"] == "421"
    assert by_code["421b"]["parent_code"] == "421"
    assert by_code["421a"]["values"]["2025"] == -19934603.0
    assert by_code["421a"]["values"]["2024"] == -100737591.0
    assert by_code["421b"]["values"]["2025"] == -62058236.0
    assert by_code["421b"]["values"]["2024"] == -29048713.0


def test_statement_rows_normalize_uppercase_alphanumeric_codes():
    parser = PDFParser()
    line = "421A - Lo luy ke den cuoi nam truoc (19.934.603) (100.737.591)"

    row = parser._parse_statement_table_row(line, 9, ["2025", "2024"], "financial_position")

    assert row is not None
    assert row["code"] == "421a"
    assert row["values"]["2025"] == -19934603.0
    assert row["values"]["2024"] == -100737591.0


def test_statement_rows_keep_single_period_receivable_loan_line():
    parser = PDFParser()
    line = "135 3. Phai thu ve cho vay ngan han 36.3 1.914.106"

    row = parser._parse_statement_table_row(line, 7, ["2025", "2024"], "financial_position")

    assert row is not None
    assert row["code"] == "135"
    assert row["note"] == "36.3"
    assert row["label"] == "Phai thu ve cho vay ngan han"
    assert row["values"]["2025"] == 1914106.0
    assert row["values"]["2024"] is None


def test_statement_rows_infer_receivable_loan_code_when_ocr_drops_code():
    parser = PDFParser()
    line = "3. Phai thu ve cho vay ngan han 36.3 1.914.106"

    row = parser._parse_statement_table_row(line, 7, ["2025", "2024"], "financial_position")

    assert row is not None
    assert row["code"] == "135"
    assert row["note"] == "36.3"
    assert row["label"] == "Phai thu ve cho vay ngan han"
    assert row["values"]["2025"] == 1914106.0
    assert row["values"]["2024"] is None


def test_statement_tables_apply_template_mapping_by_code():
    parser = PDFParser()
    pages = [
        """
        BANG CAN DOI KE TOAN HOP NHAT
        135 3. Phai thu ve cho vay ngan han 36.3 1.914.106
        """,
    ]

    tables = parser._build_statement_tables(pages, ["2025", "2024"])
    table = next(table for table in tables if table["key"] == "financial_position")
    row = table["rows"][0]

    assert table["mapping_source"] == "PL1_TT201_2014_BTC.xlsx"
    assert row["code"] == "135"
    assert row["label"] == "Phải thu về cho vay ngắn hạn"
    assert row["raw_label"] == "Phai thu ve cho vay ngan han"
    assert row["parent_code"] == "130"
    assert row["level"] == 3


def _simple_pdf(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 10 Tf", "72 740 Td", "14 TL"]
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"({safe}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
        ),
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        (
            b"5 0 obj\n<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream\nendobj\n"
        ),
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)
