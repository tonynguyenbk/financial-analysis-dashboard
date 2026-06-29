import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import pdfplumber
import pypdfium2 as pdfium
import pytesseract

from app.parsers.base import FinancialStatementParser, ProgressCallback
from app.parsers.normalization import (
    METRIC_ALIASES,
    build_statement_from_metric_records,
    coerce_number,
    normalize_label,
)
from app.parsers.statement_mapping import StatementMappingItem, get_statement_mapping
from app.schemas.financial import FinancialStatement


YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
DATE_PATTERN = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[\-/\.](0?[1-9]|1[0-2])[\-/\.]((?:19|20)\d{2})\b")
WRITTEN_VI_DATE_PATTERN = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])\s+thang\s+(0?[1-9]|1[0-2])\s+nam\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
WRITTEN_EN_DATE_PATTERN = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])\s+"
    r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+"
    r"((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(
    r"\(?-?\d{1,3}(?:[,.]\d{3})+(?:[,.]\d+)?\)?|\(?-?\d+(?:[,.]\d+)?\)?"
)
STATEMENT_NOTE_PATTERN = re.compile(
    r"(?<![\w.])(?:[IVXLCDM]{1,5}\.?\d{1,2}[A-Za-z]?|[A-Z]{1,4}\d{1,2}|\d{1,2}(?:\.\d{1,2})?)(?![\w.])",
    re.IGNORECASE,
)
STATEMENT_CODE_TEXT_PATTERN = r"\d{2,3}[A-Za-z]?"
STATEMENT_ROW_PATTERN = re.compile(rf"^\s*\|?\s*({STATEMENT_CODE_TEXT_PATTERN})\s*(?:[|.)]\s*)?(.*)$")
TOC_LINE_PATTERN = re.compile(r"^(.+?)\s+(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\D*$")
DEFAULT_OCR_MAX_PAGES = 0
DEFAULT_OCR_SCALE = 1.8
DEFAULT_TOC_OCR_SCALE = 1.6
DEFAULT_OCR_WORKERS = 1
DEFAULT_OCR_LANGUAGES = "vie"
DEFAULT_OCR_CONFIG = "--oem 1 --psm 6 -c preserve_interword_spaces=1"
DEFAULT_TOC_SCAN_PAGES = 12
PREVIEW_PROGRESS = 65
MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
REPORT_PERIOD_CONTEXT_MARKERS = (
    "as at",
    "as of",
    "tai ngay",
    "nam ket thuc",
    "nam tai chinh ket thuc",
    "cho nam ket thuc",
    "for the year ended",
    "year ended",
    "fiscal year ended",
    "so cuoi nam",
    "so dau nam",
    "nam nay",
    "nam truoc",
    "current year",
    "previous year",
)
DISCLOSURE_NAVIGATION_MARKERS = (
    "notes to the financial statements",
    "thuyet minh bao cao tai chinh",
    "accounting policies",
    "chinh sach ke toan",
)
NAVIGATION_HEADINGS = (
    "thong tin chung",
    "bao cao cua ban giam doc",
    "bao cao kiem toan doc lap",
    "bang can doi ke toan hop nhat",
    "bao cao ket qua hoat dong kinh doanh hop nhat",
    "bao cao luu chuyen tien te hop nhat",
    "phu luc",
)
MAIN_STATEMENT_SPECS = (
    {
        "key": "financial_position",
        "title": "Báo cáo tình hình tài chính",
        "aliases": (
            "bao cao tinh hinh tai chinh",
            "bang can doi ke toan hop nhat",
            "bang can doi ke toan",
            "statement of financial position",
            "balance sheet",
        ),
    },
    {
        "key": "income_statement",
        "title": "Báo cáo kết quả hoạt động kinh doanh",
        "aliases": (
            "bao cao ket qua hoat dong kinh doanh hop nhat",
            "bao cao ket qua hoat dong kinh doanh",
            "income statement",
            "statement of profit or loss",
        ),
    },
    {
        "key": "cash_flow",
        "title": "Báo cáo lưu chuyển tiền tệ",
        "aliases": (
            "bao cao luu chuyen tien te hop nhat",
            "bao cao luu chuyen tien te",
            "cash flow statement",
            "statement of cash flows",
        ),
    },
)


class PDFParser(FinancialStatementParser):
    """PDF parser strategy for digital PDFs and scanned financial statements."""

    supported_extensions = ("pdf",)

    def parse(
        self,
        file_name: str,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
    ) -> FinancialStatement:
        self._report_progress(progress_callback, 2, "received", "PDF file received.")
        if not content:
            raise ValueError("Empty PDF file content.")

        extracted = self._extract_pdf_content(content, progress_callback)
        ocr_used = False
        if not extracted["text"].strip():
            self._report_progress(
                progress_callback,
                22,
                "ocr",
                "No text layer found. Starting OCR for scanned PDF pages.",
            )
            extracted["pages"] = self._extract_ocr_pages_progressively(
                content,
                file_name,
                extracted["metadata"],
                progress_callback,
            )
            extracted["text"] = "\n".join(extracted["pages"])
            ocr_used = True

        if not extracted["text"].strip():
            raise ValueError("No readable text was found in this PDF after text-layer and OCR extraction.")

        self._report_progress(progress_callback, 88, "normalizing", "Extracting financial line items.")
        default_periods = self._infer_default_periods(file_name, extracted["text"])
        table_records = self._extract_records_from_tables(extracted["tables"], default_periods)
        text_records = self._extract_records_from_text(extracted["text"], default_periods)
        statement_tables = self._build_statement_tables(extracted["pages"], default_periods)
        statement_table_records = self._extract_records_from_statement_tables(statement_tables)
        records = self._deduplicate_records([*table_records, *text_records, *statement_table_records])
        if self._ensure_financial_position_total_assets_row(statement_tables, records):
            statement_table_records = self._extract_records_from_statement_tables(statement_tables)
            records = self._deduplicate_records([*table_records, *text_records, *statement_table_records])

        if not records:
            raise ValueError(
                "No recognizable financial statement metrics were found in the PDF. "
                "The report may use unsupported labels or require OCR/LLM extraction."
            )

        metadata = {
            "parser": "PDFParser",
            "source_file": file_name,
            "page_count": extracted["page_count"],
            "text_characters": len(extracted["text"]),
            "table_records": len(table_records),
            "text_records": len(text_records),
            "statement_table_records": len(statement_table_records),
            "ocr_used": ocr_used,
            "extracted_page_count": len([page for page in extracted["pages"] if page.strip()]),
            "extracted_pages": self._build_extracted_pages(extracted["pages"]),
            "statement_tables": statement_tables,
            "report_navigation": self._build_report_navigation(extracted["pages"]),
        }

        self._report_progress(progress_callback, 96, "normalizing", "Building standardized financial report.")
        return build_statement_from_metric_records(
            company={"name": self._infer_company_name(file_name, extracted["metadata"])},
            records=records,
            source_type="pdf",
            metadata=metadata,
        )

    def _extract_pdf_content(
        self,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        text_pages: list[str] = []
        tables: list[list[list[str | None]]] = []
        metadata: dict[str, Any] = {}

        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                metadata = dict(pdf.metadata or {})
                page_count = len(pdf.pages)
                for page_index, page in enumerate(pdf.pages):
                    text_pages.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
                    tables.extend(page.extract_tables() or [])
                    if page_count:
                        progress = 4 + round(((page_index + 1) / page_count) * 16)
                        self._report_progress(
                            progress_callback,
                            progress,
                            "text_layer",
                            f"Reading PDF page {page_index + 1}/{page_count}.",
                        )
        except Exception as exc:
            raise ValueError(f"Could not read PDF file: {exc}") from exc

        return {
            "text": "\n".join(text_pages),
            "pages": text_pages,
            "tables": tables,
            "metadata": metadata,
            "page_count": page_count,
        }

    def _extract_ocr_pages(
        self,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
    ) -> list[str]:
        max_pages = int(os.getenv("PDF_OCR_MAX_PAGES", str(DEFAULT_OCR_MAX_PAGES)))
        scale = float(os.getenv("PDF_OCR_SCALE", str(DEFAULT_OCR_SCALE)))
        workers = int(os.getenv("PDF_OCR_WORKERS", str(DEFAULT_OCR_WORKERS)))
        languages = os.getenv("PDF_OCR_LANGUAGES", DEFAULT_OCR_LANGUAGES)
        ocr_config = os.getenv("PDF_OCR_CONFIG", DEFAULT_OCR_CONFIG)

        try:
            pdf = pdfium.PdfDocument(BytesIO(content))
        except Exception as exc:
            raise ValueError(f"Could not render scanned PDF for OCR: {exc}") from exc

        page_count = self._ocr_page_count(len(pdf), max_pages)
        page_texts = [""] * page_count
        ocr_scales: dict[int, float] = {}
        self._report_progress(
            progress_callback,
            25,
            "ocr",
            f"OCR will process {page_count} scanned PDF pages.",
        )
        self._ocr_page_indexes(
            content=content,
            page_indexes=list(range(page_count)),
            page_count=page_count,
            page_texts=page_texts,
            ocr_scales=ocr_scales,
            scale=scale,
            languages=languages,
            ocr_config=ocr_config,
            workers=workers,
            progress_callback=progress_callback,
            progress_start=25,
            progress_span=60,
            stage="ocr",
            message_builder=lambda completed, total, page_index: (
                f"OCR page {completed}/{total} (PDF page {page_index + 1}/{page_count})."
            ),
        )

        return page_texts

    def _extract_ocr_pages_progressively(
        self,
        content: bytes,
        file_name: str,
        source_metadata: dict[str, Any],
        progress_callback: ProgressCallback | None = None,
    ) -> list[str]:
        max_pages = int(os.getenv("PDF_OCR_MAX_PAGES", str(DEFAULT_OCR_MAX_PAGES)))
        scale = float(os.getenv("PDF_OCR_SCALE", str(DEFAULT_OCR_SCALE)))
        toc_scale = float(os.getenv("PDF_TOC_OCR_SCALE", str(DEFAULT_TOC_OCR_SCALE)))
        workers = int(os.getenv("PDF_OCR_WORKERS", str(DEFAULT_OCR_WORKERS)))
        languages = os.getenv("PDF_OCR_LANGUAGES", DEFAULT_OCR_LANGUAGES)
        ocr_config = os.getenv("PDF_OCR_CONFIG", DEFAULT_OCR_CONFIG)
        toc_scan_pages = int(os.getenv("PDF_TOC_SCAN_PAGES", str(DEFAULT_TOC_SCAN_PAGES)))

        try:
            pdf = pdfium.PdfDocument(BytesIO(content))
        except Exception as exc:
            raise ValueError(f"Could not render scanned PDF for OCR: {exc}") from exc

        page_count = self._ocr_page_count(len(pdf), max_pages)
        page_texts = [""] * page_count
        ocr_scales: dict[int, float] = {}

        toc_limit = min(page_count, max(1, toc_scan_pages))
        self._report_progress(
            progress_callback,
            25,
            "toc",
            f"OCR will process {page_count} scanned PDF pages. Scanning the first {toc_limit} pages for the table of contents.",
        )

        self._ocr_page_indexes(
            content=content,
            page_indexes=list(range(toc_limit)),
            page_count=page_count,
            page_texts=page_texts,
            ocr_scales=ocr_scales,
            scale=toc_scale,
            languages=languages,
            ocr_config=ocr_config,
            workers=workers,
            progress_callback=progress_callback,
            progress_start=25,
            progress_span=10,
            stage="toc",
            message_builder=lambda completed, total, page_index: (
                f"Scanning PDF page {page_index + 1}/{page_count} for the table of contents ({completed}/{total})."
            ),
        )

        target_indexes = self._target_statement_page_indexes(page_texts, page_count)
        if not target_indexes:
            fallback_limit = min(page_count, max(toc_limit + 10, 16))
            target_indexes = list(range(fallback_limit))

        self._ocr_page_indexes(
            content=content,
            page_indexes=target_indexes,
            page_count=page_count,
            page_texts=page_texts,
            ocr_scales=ocr_scales,
            scale=scale,
            languages=languages,
            ocr_config=ocr_config,
            workers=workers,
            progress_callback=progress_callback,
            progress_start=35,
            progress_span=26,
            stage="primary_statements",
            message_builder=lambda completed, total, page_index: (
                "Preparing primary financial statement page "
                f"{completed}/{total} (PDF page {page_index + 1}/{page_count})."
            ),
        )

        preview_statement = self._build_preview_statement(
            file_name=file_name,
            source_metadata=source_metadata,
            pages=page_texts,
            page_count=page_count,
        )
        if preview_statement is not None:
            self._report_progress(
                progress_callback,
                PREVIEW_PROGRESS,
                "preview_ready",
                "Primary financial statements are ready for review.",
                preview_statement,
            )

        return page_texts

    def _ocr_page_indexes(
        self,
        content: bytes,
        page_indexes: list[int],
        page_count: int,
        page_texts: list[str],
        ocr_scales: dict[int, float],
        scale: float,
        languages: str,
        ocr_config: str,
        workers: int,
        progress_callback: ProgressCallback | None,
        progress_start: int,
        progress_span: int,
        stage: str,
        message_builder: Callable[[int, int, int], str],
    ) -> None:
        work_indexes = [
            page_index
            for page_index in dict.fromkeys(page_indexes)
            if 0 <= page_index < page_count and self._ocr_scale_is_stale(ocr_scales.get(page_index), scale)
        ]
        if not work_indexes:
            return

        worker_count = max(1, min(workers, len(work_indexes)))
        if worker_count == 1:
            for completed, page_index in enumerate(work_indexes, start=1):
                page_texts[page_index] = self._extract_ocr_page_text_from_content(
                    content,
                    page_index,
                    scale,
                    languages,
                    ocr_config,
                )
                ocr_scales[page_index] = scale
                self._report_ocr_batch_progress(
                    progress_callback,
                    progress_start,
                    progress_span,
                    stage,
                    completed,
                    len(work_indexes),
                    page_index,
                    message_builder,
                )
            return

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_page = {
                executor.submit(
                    self._extract_ocr_page_text_from_content,
                    content,
                    page_index,
                    scale,
                    languages,
                    ocr_config,
                ): page_index
                for page_index in work_indexes
            }
            for completed, future in enumerate(as_completed(future_to_page), start=1):
                page_index = future_to_page[future]
                page_texts[page_index] = future.result()
                ocr_scales[page_index] = scale
                self._report_ocr_batch_progress(
                    progress_callback,
                    progress_start,
                    progress_span,
                    stage,
                    completed,
                    len(work_indexes),
                    page_index,
                    message_builder,
                )

    def _report_ocr_batch_progress(
        self,
        progress_callback: ProgressCallback | None,
        progress_start: int,
        progress_span: int,
        stage: str,
        completed: int,
        total: int,
        page_index: int,
        message_builder: Callable[[int, int, int], str],
    ) -> None:
        progress = progress_start + round((completed / max(total, 1)) * progress_span)
        self._report_progress(
            progress_callback,
            progress,
            stage,
            message_builder(completed, total, page_index),
        )

    def _ocr_scale_is_stale(self, current_scale: float | None, required_scale: float) -> bool:
        return current_scale is None or current_scale + 0.01 < required_scale

    def _extract_ocr_page_text_from_content(
        self,
        content: bytes,
        page_index: int,
        scale: float,
        languages: str,
        ocr_config: str,
    ) -> str:
        try:
            pdf = pdfium.PdfDocument(BytesIO(content))
        except Exception as exc:
            raise ValueError(f"Could not render scanned PDF for OCR: {exc}") from exc

        return self._extract_ocr_page_text(pdf, page_index, scale, languages, ocr_config)

    def _extract_ocr_page_text(
        self,
        pdf: Any,
        page_index: int,
        scale: float,
        languages: str,
        ocr_config: str,
    ) -> str:
        page = pdf[page_index]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        try:
            text = pytesseract.image_to_string(
                image,
                lang=languages,
                config=ocr_config,
            )
        except pytesseract.TesseractNotFoundError as exc:
            raise ValueError(
                "Tesseract OCR is not installed. Run the Docker backend image or install Tesseract locally."
            ) from exc
        finally:
            close_image = getattr(image, "close", None)
            if callable(close_image):
                close_image()
            close_bitmap = getattr(bitmap, "close", None)
            if callable(close_bitmap):
                close_bitmap()
            close_page = getattr(page, "close", None)
            if callable(close_page):
                close_page()
        return self._clean_ocr_text(text or "")

    def _target_statement_page_indexes(self, pages: list[str], page_count: int) -> list[int]:
        toc_entries = self._extract_toc_navigation_entries(pages)
        target_indexes: set[int] = set()

        if toc_entries:
            resolved_entries = self._resolve_toc_navigation_pages(toc_entries, pages)
            for spec in MAIN_STATEMENT_SPECS:
                entry = self._find_navigation_entry_for_aliases(resolved_entries, spec["aliases"])
                if entry is None:
                    continue

                start_page = int(entry.get("page") or entry.get("report_page") or 0)
                if start_page <= 0:
                    continue

                report_start = entry.get("report_page")
                report_end = entry.get("report_page_end")
                if isinstance(report_start, int) and isinstance(report_end, int) and report_end >= report_start:
                    end_page = start_page + (report_end - report_start)
                else:
                    end_page = start_page

                buffer_pages = 0
                if entry.get("resolved_by") != "heading" and start_page == int(entry.get("report_page") or start_page):
                    buffer_pages = 2

                for page in range(max(1, start_page - buffer_pages), min(page_count, end_page + buffer_pages) + 1):
                    target_indexes.add(page - 1)

        if target_indexes:
            return sorted(target_indexes)

        for spec in MAIN_STATEMENT_SPECS:
            target_indexes.update(self._find_statement_page_indexes(pages, spec["aliases"]))

        return sorted(index for index in target_indexes if 0 <= index < page_count)

    def _find_navigation_entry_for_aliases(
        self,
        entries: list[dict[str, Any]],
        aliases: tuple[str, ...],
    ) -> dict[str, Any] | None:
        for entry in entries:
            normalized_title = normalize_label(entry.get("title"))
            if any(alias in normalized_title or normalized_title in alias for alias in aliases):
                return entry
        return None

    def _build_preview_statement(
        self,
        file_name: str,
        source_metadata: dict[str, Any],
        pages: list[str],
        page_count: int,
    ) -> FinancialStatement | None:
        text = "\n".join(page for page in pages if page.strip())
        if not text.strip():
            return None

        default_periods = self._infer_default_periods(file_name, text)
        statement_tables = self._build_statement_tables(pages, default_periods)
        if not statement_tables:
            return None

        text_records = self._extract_records_from_text(text, default_periods)
        statement_table_records = self._extract_records_from_statement_tables(statement_tables)
        records = self._deduplicate_records([*text_records, *statement_table_records])
        if self._ensure_financial_position_total_assets_row(statement_tables, records):
            statement_table_records = self._extract_records_from_statement_tables(statement_tables)
            records = self._deduplicate_records([*text_records, *statement_table_records])
        if not records:
            return None

        return build_statement_from_metric_records(
            company={"name": self._infer_company_name(file_name, source_metadata)},
            records=records,
            source_type="pdf",
            metadata={
                "parser": "PDFParser",
                "source_file": file_name,
                "page_count": page_count,
                "text_characters": len(text),
                "text_records": len(text_records),
                "statement_table_records": len(statement_table_records),
                "ocr_used": True,
                "preview_ready": True,
                "preview_scope": "primary_financial_statements",
                "extracted_page_count": len([page for page in pages if page.strip()]),
                "statement_tables": statement_tables,
                "report_navigation": self._build_report_navigation(pages),
            },
        )

    def _extract_records_from_tables(
        self, tables: list[list[list[str | None]]], default_periods: list[str]
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for table in tables:
            rows = [[self._clean_cell(cell) for cell in row] for row in table if row]
            if not rows:
                continue

            header_index, year_by_column = self._find_table_header(rows, default_periods)
            if header_index is None or not year_by_column:
                continue

            first_year_column = min(year_by_column)
            for row in rows[header_index + 1 :]:
                metric_cell = self._find_metric_cell(row, first_year_column)
                if not metric_cell:
                    continue

                metric = self._canonical_metric_from_text(metric_cell)
                if metric is None:
                    continue

                for column_index, year in year_by_column.items():
                    if column_index >= len(row):
                        continue
                    value = coerce_number(row[column_index])
                    if value is None:
                        continue
                    records.append(
                        {
                            "metric": metric,
                            "period": year,
                            "value": value,
                        }
                    )

        return records

    def _extract_records_from_statement_tables(self, statement_tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for table in statement_tables:
            for row in table.get("rows", []):
                metric = self._canonical_metric_from_text(row.get("label"))
                if metric is None:
                    continue

                values = row.get("values") or {}
                if not isinstance(values, dict):
                    continue

                for period, value in values.items():
                    if value is None:
                        continue
                    records.append(
                        {
                            "metric": metric,
                            "period": str(period),
                            "value": value,
                        }
                    )
        return records

    def _extract_records_from_text(self, text: str, default_periods: list[str] | None = None) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        default_periods = default_periods or []
        current_years: list[str] = default_periods.copy()
        pending_metric: str | None = None
        pending_values: list[float] = []

        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue

            years = self._periods_in_text(line)
            metric = self._canonical_metric_from_text(line)
            if metric is None and self._looks_like_period_header(line):
                current_years = years if len(years) >= 2 else default_periods.copy()
                continue
            if len(years) >= 2 and metric is None and self._looks_like_compact_year_header(line):
                current_years = years
                continue

            if metric is not None and metric != pending_metric:
                pending_values = []

            active_metric = metric or pending_metric
            if active_metric is None:
                continue

            period_labels = years if len(years) >= 2 else current_years
            if not period_labels:
                continue

            values = self._numeric_values_excluding_years(line)
            combined_values = [*pending_values, *values] if pending_metric and metric is None else values
            statement_values = self._select_statement_amounts(combined_values, len(period_labels))
            if len(statement_values) < len(period_labels):
                pending_metric = active_metric
                pending_values = self._material_values(combined_values)
                continue

            for period, value in zip(period_labels, statement_values, strict=False):
                records.append(
                    {
                        "metric": active_metric,
                        "period": period,
                        "value": value,
                    }
                )
            pending_metric = None
            pending_values = []

        return records

    def _find_table_header(
        self, rows: list[list[str]], default_periods: list[str]
    ) -> tuple[int | None, dict[int, str]]:
        for index, row in enumerate(rows[:8]):
            year_by_column = {
                column_index: years[0]
                for column_index, cell in enumerate(row)
                if (years := self._periods_in_text(cell))
            }
            if len(year_by_column) >= 2:
                return index, year_by_column
            normalized_row = " ".join(normalize_label(cell) for cell in row)
            if default_periods and self._looks_like_period_header(normalized_row):
                numeric_columns = [
                    column_index
                    for column_index, cell in enumerate(row)
                    if any(marker in normalize_label(cell) for marker in ("so cuoi nam", "so cudi nam", "so dau nam", "nam nay", "nam truoc"))
                ]
                if len(numeric_columns) >= 2:
                    return index, dict(zip(numeric_columns[-2:], default_periods[:2], strict=False))
        return None, {}

    def _find_metric_cell(self, row: list[str], first_year_column: int) -> str | None:
        candidates = row[:first_year_column] or row[:1]
        for cell in candidates:
            if self._canonical_metric_from_text(cell):
                return cell
        return None

    def _canonical_metric_from_text(self, text: Any) -> str | None:
        normalized = normalize_label(text)
        if not normalized:
            return None

        for alias, metric in sorted(METRIC_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if normalized == alias or normalized.startswith(f"{alias} ") or f" {alias} " in f" {normalized} ":
                return metric
        return None

    def _numeric_values_excluding_years(self, text: str) -> list[float]:
        values: list[float] = []
        for token in NUMBER_PATTERN.findall(text):
            cleaned = token.strip()
            if self._is_year_token(cleaned):
                continue
            value = coerce_number(cleaned)
            if value is not None:
                values.append(value)
        return values

    def _select_statement_amounts(self, values: list[float], period_count: int) -> list[float]:
        if len(values) < period_count:
            return []

        material_values = self._material_values(values)
        if len(material_values) >= period_count:
            return material_values[-period_count:]

        return []

    def _material_values(self, values: list[float]) -> list[float]:
        return [value for value in values if abs(value) >= 1000]

    def _years_in_text(self, text: Any) -> list[str]:
        seen: set[str] = set()
        years: list[str] = []
        for match in YEAR_PATTERN.findall(str(text or "")):
            if match not in seen:
                years.append(match)
                seen.add(match)
        return years

    def _periods_in_text(self, text: Any) -> list[str]:
        value = str(text or "")
        periods: list[str] = []
        seen: set[str] = set()

        def add_period_from_date(day: str, month: int | str, year_text: str) -> None:
            year = int(year_text)
            period_year = year - 1 if int(day) == 1 and int(month) == 1 else year
            period = str(period_year)
            if period not in seen:
                periods.append(period)
                seen.add(period)

        for day, month, year_text in DATE_PATTERN.findall(value):
            add_period_from_date(day, month, year_text)

        normalized_value = normalize_label(value)
        for day, month, year_text in WRITTEN_VI_DATE_PATTERN.findall(normalized_value):
            add_period_from_date(day, month, year_text)

        for day, month_name, year_text in WRITTEN_EN_DATE_PATTERN.findall(normalized_value):
            add_period_from_date(day, MONTH_NAME_TO_NUMBER[month_name.lower()], year_text)

        if len(periods) >= 2:
            return periods

        for year in self._years_in_text(value):
            if year not in seen:
                periods.append(year)
                seen.add(year)
        return periods

    def _infer_default_periods(self, file_name: str, text: str) -> list[str]:
        file_years = self._filter_report_years(int(year) for year in self._years_in_text(file_name))
        if file_years:
            latest = self._select_fallback_report_year(file_years)
            return [str(latest), str(latest - 1)]

        context_periods = self._infer_periods_from_context_lines(text[:6000], max_lines=120)
        if len(context_periods) >= 2:
            return context_periods[:2]
        if len(context_periods) == 1 and context_periods[0].isdigit():
            latest = int(context_periods[0])
            return [str(latest), str(latest - 1)]

        candidates = [text[:6000]]
        raw_years: list[int] = []
        for source in candidates:
            for year in self._years_in_text(source):
                value = int(year)
                if value not in raw_years:
                    raw_years.append(value)

        years = self._filter_report_years(raw_years)
        if not years:
            return []

        latest = self._select_fallback_report_year(years)
        return [str(latest), str(latest - 1)]

    def _select_fallback_report_year(self, years: list[int]) -> int:
        current_year = date.today().year
        prior_years = [year for year in years if year < current_year]
        if prior_years:
            return max(prior_years)
        return max(years)

    def _filter_report_years(self, years: Any) -> list[int]:
        current_year = date.today().year
        filtered: list[int] = []
        for year in years:
            if 1900 <= int(year) <= current_year and int(year) not in filtered:
                filtered.append(int(year))
        return filtered

    def _infer_periods_from_context_lines(self, text: str, max_lines: int = 60) -> list[str]:
        lines = [self._clean_statement_line(line) for line in str(text or "").splitlines()]
        lines = [line for line in lines if line][:max_lines]
        best_single_periods: list[str] = []

        for window_size in (1, 2, 3, 4):
            for start in range(0, max(0, len(lines) - window_size + 1)):
                window = " ".join(lines[start : start + window_size])
                normalized = normalize_label(window)
                has_period_context = any(marker in normalized for marker in REPORT_PERIOD_CONTEXT_MARKERS)
                periods = self._filter_period_labels(self._periods_in_text(window))
                if (
                    len(periods) >= 2
                    and (has_period_context or self._looks_like_period_column_header(normalized))
                    and self._periods_are_plausible_statement_pair(periods)
                ):
                    return periods[:2]
                if has_period_context and periods and not best_single_periods:
                    best_single_periods = periods[:1]

        return best_single_periods

    def _looks_like_period_column_header(self, normalized_text: str) -> bool:
        markers = ("vnd", "ma so", "thuyet minh", "code", "note")
        return any(marker in normalized_text for marker in markers)

    def _periods_are_plausible_statement_pair(self, periods: list[str]) -> bool:
        if len(periods) < 2 or not periods[0].isdigit() or not periods[1].isdigit():
            return False
        current = int(periods[0])
        previous = int(periods[1])
        return current - previous == 1

    def _filter_period_labels(self, periods: list[str]) -> list[str]:
        current_year = date.today().year
        filtered: list[str] = []
        for period in periods:
            if not str(period).isdigit():
                continue
            year = int(period)
            if 1900 <= year <= current_year and period not in filtered:
                filtered.append(str(year))
        return filtered

    def _looks_like_period_header(self, text: str) -> bool:
        normalized = normalize_label(text)
        markers = (
            "so cuoi nam",
            "so cudi nam",
            "so dau nam",
            "nam nay",
            "nam truoc",
            "current year",
            "previous year",
        )
        return any(marker in normalized for marker in markers)

    def _looks_like_compact_year_header(self, text: str) -> bool:
        normalized = normalize_label(text)
        if len(normalized.split()) > 8:
            return False
        return len(self._periods_in_text(text)) >= 2

    def _is_year_token(self, token: str) -> bool:
        cleaned = token.strip("()").replace(",", "").replace(" ", "")
        return bool(YEAR_PATTERN.fullmatch(cleaned))

    def _deduplicate_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[tuple[str, str], dict[str, Any]] = {}
        for record in records:
            key = (str(record.get("metric")), str(record.get("period")))
            existing = deduped.get(key)
            if existing is None or self._record_value_strength(record) > self._record_value_strength(existing):
                deduped[key] = record
        return list(deduped.values())

    def _record_value_strength(self, record: dict[str, Any]) -> float:
        try:
            return abs(float(record.get("value") or 0))
        except (TypeError, ValueError):
            return 0

    def _build_extracted_pages(self, pages: list[str]) -> list[dict[str, Any]]:
        extracted_pages: list[dict[str, Any]] = []
        for index, text in enumerate(pages):
            page_text = text.rstrip()
            if page_text.strip():
                extracted_pages.append({"page": index + 1, "text": page_text})
        return extracted_pages

    def _build_statement_tables(self, pages: list[str], default_periods: list[str]) -> list[dict[str, Any]]:
        fallback_periods = default_periods[:2]
        if len(fallback_periods) < 2:
            fallback_periods = self._infer_default_periods("", "\n".join(pages))[:2]
        if len(fallback_periods) < 2:
            fallback_periods = ["current", "previous"]

        tables: list[dict[str, Any]] = []
        for spec in MAIN_STATEMENT_SPECS:
            page_indexes = self._find_statement_page_indexes_for_spec(pages, spec)
            statement_key = str(spec["key"])
            template_key = self._template_key_for_statement(statement_key, pages, page_indexes)
            periods = self._infer_statement_periods(pages, page_indexes, fallback_periods)
            rows = self._extract_statement_table_rows(pages, page_indexes, periods, statement_key)
            rows = self._apply_statement_mapping(rows, statement_key, template_key)
            if not rows:
                continue
            tables.append(
                {
                    "key": spec["key"],
                    "template_key": template_key,
                    "mapping_source": get_statement_mapping().source_name,
                    "title": spec["title"],
                    "pages": [page_index + 1 for page_index in page_indexes],
                    "columns": self._statement_table_columns(str(spec["key"]), periods),
                    "rows": rows,
                }
            )
        return tables

    def _ensure_financial_position_total_assets_row(
        self,
        statement_tables: list[dict[str, Any]],
        records: list[dict[str, Any]],
    ) -> bool:
        table = next(
            (table for table in statement_tables if table.get("key") == "financial_position"),
            None,
        )
        if table is None:
            return False

        rows = table.get("rows")
        if not isinstance(rows, list) or any(str(row.get("code") or "").strip() == "270" for row in rows):
            return False

        periods = [
            str(column.get("key"))
            for column in table.get("columns", [])
            if column.get("key") not in {"label", "code", "note"}
        ]
        if not periods:
            return False

        values = self._metric_values_from_records(records, "TOTAL_ASSETS", periods)
        if not self._has_any_statement_value(values):
            values = self._statement_values_by_code(table, "440", periods)
        if not self._has_any_statement_value(values):
            values = self._sum_statement_period_values(
                self._statement_values_by_code(table, "300", periods),
                self._statement_values_by_code(table, "400", periods),
                periods,
            )
        if not self._has_any_statement_value(values):
            values = self._sum_statement_period_values(
                self._statement_values_by_code(table, "300", periods),
                self._statement_values_by_code(table, "410", periods),
                periods,
            )
        if not self._has_any_statement_value(values):
            values = self._sum_statement_period_values(
                self._metric_values_from_records(records, "TOTAL_LIABILITIES", periods),
                self._metric_values_from_records(records, "TOTAL_EQUITY", periods),
                periods,
            )
        if not self._has_any_statement_value(values):
            return False

        mapping_item = self._find_mapping_item_by_code(
            "financial_position",
            "270",
            str(table.get("template_key") or "financial_position"),
        )
        mapping = get_statement_mapping()
        reconstructed_row: dict[str, Any] = {
            "code": "270",
            "label": mapping_item.label if mapping_item is not None else "TONG CONG TAI SAN",
            "note": None,
            "values": values,
            "page": self._statement_page_near_code(table, "300") or self._statement_page_near_code(table, "289"),
            "raw_text": "Reconstructed TOTAL_ASSETS row from extracted balance sheet totals.",
            "raw_label": "TONG CONG TAI SAN",
            "reconstructed": True,
            "reconstructed_from": "TOTAL_ASSETS",
        }
        if mapping_item is not None:
            reconstructed_row.update(
                {
                    "template_label": mapping_item.label,
                    "parent_code": mapping_item.parent_code,
                    "level": mapping_item.level,
                    "mapping_source": mapping.source_name,
                    "mapping_row": mapping_item.row_number,
                }
            )

        insert_index = self._statement_insert_index_before_code(rows, "300")
        rows.insert(insert_index, reconstructed_row)
        return True

    def _metric_values_from_records(
        self,
        records: list[dict[str, Any]],
        metric: str,
        periods: list[str],
    ) -> dict[str, float | None]:
        values: dict[str, float | None] = {period: None for period in periods}
        for record in records:
            record_metric = record.get("metric") or record.get("label") or record.get("code")
            if record_metric != metric and self._canonical_metric_from_text(record_metric) != metric:
                continue

            period = str(record.get("period") or record.get("fiscal_year") or "")
            if period not in values:
                continue

            value = coerce_number(record.get("value"))
            if value is not None:
                values[period] = value
        return values

    def _statement_values_by_code(
        self,
        table: dict[str, Any],
        code: str,
        periods: list[str],
    ) -> dict[str, float | None]:
        values: dict[str, float | None] = {period: None for period in periods}
        for row in table.get("rows", []):
            if str(row.get("code") or "").strip() != code:
                continue
            row_values = row.get("values") if isinstance(row.get("values"), dict) else {}
            for period in periods:
                value = coerce_number(row_values.get(period))
                if value is not None:
                    values[period] = value
        return values

    def _sum_statement_period_values(
        self,
        left: dict[str, float | None],
        right: dict[str, float | None],
        periods: list[str],
    ) -> dict[str, float | None]:
        values: dict[str, float | None] = {period: None for period in periods}
        for period in periods:
            left_value = coerce_number(left.get(period))
            right_value = coerce_number(right.get(period))
            if left_value is None or right_value is None:
                continue
            values[period] = left_value + right_value
        return values

    def _has_any_statement_value(self, values: dict[str, float | None]) -> bool:
        return any(value is not None for value in values.values())

    def _statement_insert_index_before_code(self, rows: list[dict[str, Any]], code: str) -> int:
        target_number = self._statement_code_number(code)
        for index, row in enumerate(rows):
            row_number = self._statement_code_number(row.get("code"))
            if target_number is not None and row_number is not None and row_number >= target_number:
                return index
        return len(rows)

    def _statement_page_near_code(self, table: dict[str, Any], code: str) -> int | None:
        for row in table.get("rows", []):
            if str(row.get("code") or "").strip() == code:
                try:
                    return int(row.get("page") or 0) or None
                except (TypeError, ValueError):
                    return None
        return None

    def _statement_code_number(self, code: Any) -> int | None:
        match = re.match(r"\d+", str(code or "").strip())
        return int(match.group(0)) if match else None

    def _infer_statement_periods(
        self,
        pages: list[str],
        page_indexes: list[int],
        fallback_periods: list[str],
    ) -> list[str]:
        page_text = "\n".join(
            pages[index]
            for index in page_indexes
            if 0 <= index < len(pages)
        )
        periods = self._infer_periods_from_context_lines(page_text, max_lines=45)
        if len(periods) >= 2:
            return periods[:2]
        if len(periods) == 1 and periods[0].isdigit():
            latest = int(periods[0])
            return [str(latest), str(latest - 1)]
        return fallback_periods[:2]

    def _template_key_for_statement(self, statement_key: str, pages: list[str], page_indexes: list[int]) -> str:
        if statement_key != "cash_flow":
            return statement_key

        relevant_text = "\n".join(pages[index] for index in page_indexes if 0 <= index < len(pages))
        normalized = normalize_label(relevant_text)
        if "phuong phap truc tiep" in normalized:
            return "cash_flow_direct"
        if "phuong phap gian tiep" in normalized:
            return "cash_flow_indirect"
        return "cash_flow_indirect"

    def _apply_statement_mapping(
        self,
        rows: list[dict[str, Any]],
        statement_key: str,
        template_key: str,
    ) -> list[dict[str, Any]]:
        mapping = get_statement_mapping()
        mapped_rows: list[dict[str, Any]] = []
        for row in rows:
            row = self._repair_statement_table_row_code(row, statement_key, template_key)
            item = self._find_statement_mapping_item(row, statement_key, template_key)
            if item is None:
                if self._statement_has_template_mapping(statement_key, template_key):
                    continue
                mapped_rows.append(row)
                continue

            mapped_row = row.copy()
            mapped_row["raw_label"] = row.get("label")
            mapped_row["label"] = item.label
            mapped_row["template_label"] = item.label
            mapped_row["parent_code"] = item.parent_code
            mapped_row["level"] = item.level
            mapped_row["mapping_source"] = mapping.source_name
            mapped_row["mapping_row"] = item.row_number
            mapped_rows.append(mapped_row)
        return mapped_rows

    def _find_statement_mapping_item(
        self,
        row: dict[str, Any],
        statement_key: str,
        template_key: str,
    ) -> StatementMappingItem | None:
        mapping = get_statement_mapping()
        code = row.get("code")
        candidates = [template_key]
        if statement_key == "cash_flow":
            candidates.extend(["cash_flow_indirect", "cash_flow_direct"])

        for candidate_key in dict.fromkeys(candidates):
            item = mapping.get(candidate_key, code)
            if item is not None:
                return item

        for candidate_key in dict.fromkeys(candidates):
            item = mapping.find_by_label(candidate_key, row.get("label"))
            if item is not None:
                return item
        return None

    def _statement_has_template_mapping(self, statement_key: str, template_key: str | None = None) -> bool:
        mapping = get_statement_mapping()
        candidate_keys = self._statement_mapping_candidate_keys(statement_key, template_key)
        return any(item.statement_key in candidate_keys for item in mapping.items)

    def _statement_mapping_candidate_keys(
        self,
        statement_key: str,
        template_key: str | None = None,
    ) -> list[str]:
        candidates = [template_key or statement_key]
        if statement_key == "cash_flow":
            candidates.extend(["cash_flow_indirect", "cash_flow_direct", "cash_flow"])
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    def _find_mapping_item_by_code(
        self,
        statement_key: str,
        code: Any,
        template_key: str | None = None,
    ) -> StatementMappingItem | None:
        mapping = get_statement_mapping()
        for candidate_key in self._statement_mapping_candidate_keys(statement_key, template_key):
            item = mapping.get(candidate_key, code)
            if item is not None:
                return item
        return None

    def _statement_table_columns(self, statement_key: str, periods: list[str]) -> list[dict[str, str]]:
        return [
            {"key": "label", "label": "Chỉ tiêu"},
            {"key": "code", "label": "Mã số"},
            {"key": "note", "label": "Thuyết minh"},
            *(
                {
                    "key": period,
                    "label": self._statement_period_label(statement_key, period),
                }
                for period in periods
            ),
        ]

    def _statement_period_label(self, statement_key: str, period: str) -> str:
        if statement_key == "financial_position" and period.isdigit() and len(period) == 4:
            return f"31/12/{period}"
        return period

    def _find_statement_page_indexes_for_spec(self, pages: list[str], spec: dict[str, Any]) -> list[int]:
        toc_indexes = self._find_statement_page_indexes_from_toc(pages, spec["aliases"])
        if toc_indexes:
            return toc_indexes
        return self._find_statement_page_indexes(pages, spec["aliases"])

    def _find_statement_page_indexes_from_toc(self, pages: list[str], aliases: tuple[str, ...]) -> list[int]:
        toc_entries = self._extract_toc_navigation_entries(pages)
        if not toc_entries:
            return []

        resolved_entries = self._resolve_toc_navigation_pages(toc_entries, pages)
        entry = self._find_navigation_entry_for_aliases(resolved_entries, aliases)
        if entry is None:
            return []

        start_page = int(entry.get("page") or 0)
        if start_page <= 0:
            return []

        report_start = entry.get("report_page")
        report_end = entry.get("report_page_end")
        if isinstance(report_start, int) and isinstance(report_end, int) and report_end >= report_start:
            end_page = start_page + (report_end - report_start)
        else:
            end_page = start_page

        return [
            page_number - 1
            for page_number in range(start_page, end_page + 1)
            if 1 <= page_number <= len(pages)
        ]

    def _find_statement_page_indexes(self, pages: list[str], aliases: tuple[str, ...]) -> list[int]:
        matched: list[int] = []
        for index, page_text in enumerate(pages):
            if self._page_looks_like_toc(page_text):
                continue
            if self._page_has_different_primary_heading(page_text, aliases):
                continue
            heading_text = "\n".join(str(page_text or "").splitlines()[:24])
            normalized = normalize_label(heading_text)
            if any(alias in normalized for alias in aliases):
                matched.append(index)
        return matched

    def _extract_statement_table_rows(
        self,
        pages: list[str],
        page_indexes: list[int],
        periods: list[str],
        statement_key: str = "",
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        pending_line: str | None = None
        pending_page: int | None = None
        pending_label_hint: str | None = None

        for page_index in page_indexes:
            for raw_line in pages[page_index].splitlines():
                line = self._clean_statement_line(raw_line)
                if not line:
                    continue

                if STATEMENT_ROW_PATTERN.match(line):
                    if pending_line:
                        row = self._parse_statement_table_row_with_hint(
                            pending_line,
                            pending_page or page_index + 1,
                            periods,
                            statement_key,
                            pending_label_hint,
                        )
                        if row:
                            rows.append(row)
                            pending_label_hint = None
                    pending_line = line
                    pending_page = page_index + 1
                elif pending_line:
                    pending_line = f"{pending_line} {line}"
                else:
                    row = self._parse_statement_table_row_with_hint(
                        line,
                        page_index + 1,
                        periods,
                        statement_key,
                        pending_label_hint,
                    )
                    if row:
                        rows.append(row)
                        pending_label_hint = None
                    elif self._looks_like_statement_label_hint(line):
                        pending_label_hint = self._merge_statement_label_hint(pending_label_hint, line)

                if pending_line:
                    row = self._parse_statement_table_row_with_hint(
                        pending_line,
                        pending_page or page_index + 1,
                        periods,
                        statement_key,
                        pending_label_hint,
                    )
                    if row:
                        rows.append(row)
                        pending_label_hint = None
                        pending_line = None
                        pending_page = None

        if pending_line:
            row = self._parse_statement_table_row_with_hint(
                pending_line,
                pending_page or 0,
                periods,
                statement_key,
                pending_label_hint,
            )
            if row:
                rows.append(row)

        return self._deduplicate_statement_rows(rows, statement_key)

    def _parse_statement_table_row_with_hint(
        self,
        line: str,
        page: int,
        periods: list[str],
        statement_key: str,
        label_hint: str | None,
    ) -> dict[str, Any] | None:
        row = self._parse_statement_table_row(line, page, periods, statement_key)
        if row:
            return self._apply_statement_label_hint(row, label_hint)

        if not label_hint:
            return None

        hinted_row = self._parse_statement_table_row(
            f"{label_hint} {line}",
            page,
            periods,
            statement_key,
        )
        if hinted_row:
            hinted_row["raw_text"] = line
            hinted_row["raw_label_hint"] = label_hint
        return hinted_row

    def _parse_statement_table_row(
        self,
        line: str,
        page: int,
        periods: list[str],
        statement_key: str = "",
    ) -> dict[str, Any] | None:
        candidates: list[dict[str, Any]] = []
        match = STATEMENT_ROW_PATTERN.match(line)
        if match:
            row = self._build_statement_table_row(
                code=match.group(1),
                body=match.group(2).strip(),
                page=page,
                periods=periods,
                statement_key=statement_key,
                raw_line=line,
            )
            if row:
                candidates.append(row)

        label_first_row = self._parse_label_first_statement_table_row(line, page, periods, statement_key)
        if label_first_row:
            candidates.append(label_first_row)

        if not candidates:
            return None

        repaired_candidates = [
            self._repair_statement_table_row_code(row, statement_key)
            for row in candidates
        ]
        return min(repaired_candidates, key=self._statement_row_noise_score)

    def _build_statement_table_row(
        self,
        code: str,
        body: str,
        page: int,
        periods: list[str],
        statement_key: str,
        raw_line: str,
    ) -> dict[str, Any] | None:
        body = self._repair_split_number_groups(body)
        value_matches = self._material_number_matches(body)
        if not value_matches:
            return None

        selected_value_matches = value_matches[-min(len(periods), len(value_matches)) :]
        values = self._statement_values_from_matches(selected_value_matches, periods)

        label_source = self._remove_spans(body, [(start, end) for start, end, _ in selected_value_matches])
        note, label_source = self._extract_statement_note(label_source)
        label = self._clean_statement_label(label_source, statement_key)
        if not label or self._statement_label_is_noise(label):
            return None

        return {
            "code": self._normalize_statement_code(code),
            "label": label,
            "note": note,
            "values": values,
            "page": page,
            "raw_text": raw_line,
        }

    def _parse_label_first_statement_table_row(
        self,
        line: str,
        page: int,
        periods: list[str],
        statement_key: str,
    ) -> dict[str, Any] | None:
        line = self._repair_split_number_groups(line)
        value_matches = self._material_number_matches(line)
        if not value_matches:
            return None

        selected_value_matches = value_matches[-min(len(periods), len(value_matches)) :]
        values = self._statement_values_from_matches(selected_value_matches, periods)
        label_and_codes = self._remove_spans(line, [(start, end) for start, end, _ in selected_value_matches])
        label_and_codes = self._clean_statement_line(label_and_codes)
        match = re.match(
            rf"^(?P<label>.+?)\s+(?P<code>{STATEMENT_CODE_TEXT_PATTERN})(?:\s+(?P<note>\d+(?:\.\d+)?))?\s*$",
            label_and_codes,
        )
        if not match:
            note, label_source = self._extract_statement_note(label_and_codes)
            label = self._clean_statement_label(label_source, statement_key)
            code = self._infer_statement_code_from_label(label, statement_key)
            if code is None:
                code = self._infer_statement_code_from_mapped_label(label, statement_key)
            if code is None:
                return None
        else:
            label = self._clean_statement_label(match.group("label"), statement_key)
            code = self._normalize_statement_code(match.group("code"))
            note = self._normalize_statement_note(match.group("note"))
        label, code, note = self._repair_embedded_statement_code(label, code, note)
        if not label or self._statement_label_is_noise(label):
            return None

        return {
            "code": self._normalize_statement_code(code),
            "label": label,
            "note": note,
            "values": values,
            "page": page,
            "raw_text": line,
        }

    def _statement_values_from_matches(
        self,
        value_matches: list[tuple[int, int, float]],
        periods: list[str],
    ) -> dict[str, float | None]:
        values: dict[str, float | None] = {period: None for period in periods}
        for period, (_, _, value) in zip(periods, value_matches, strict=False):
            values[period] = value
        return values

    def _infer_statement_code_from_label(self, label: str, statement_key: str) -> str | None:
        if statement_key != "financial_position":
            return None

        normalized = normalize_label(label)
        code_aliases = (
            ("total resources", "440"),
            ("total liabilities and owners equity", "440"),
            ("total liabilities and equity", "440"),
            ("tong cong nguon von", "440"),
            ("nguon von", "440"),
            ("total assets", "270"),
            ("tong cong tai san", "270"),
            ("tong tai san", "270"),
            ("owners equity", "400"),
            ("owner s equity", "400"),
            ("von chu so huu", "400"),
            ("total liabilities", "300"),
            ("tong cong no phai tra", "300"),
            ("tong no phai tra", "300"),
            ("no phai tra", "300"),
            ("phai thu ngan han cua khach hang", "131"),
            ("phai thu khach hang", "131"),
            ("tra truoc cho nguoi ban", "132"),
            ("phai thu ve cho vay ngan han", "135"),
            ("phai thu ve cho vay", "135"),
            ("phai thu ngan han khac", "136"),
            ("du phong phai thu ngan han kho doi", "137"),
            ("du phong phai thu kho doi", "137"),
        )
        for alias, code in code_aliases:
            if alias in normalized:
                return code
        return None

    def _infer_statement_code_from_mapped_label(self, label: str, statement_key: str) -> str | None:
        for code in self._statement_code_tokens(label):
            if self._find_mapping_item_by_code(statement_key, code) is not None:
                return code
        return None

    def _material_number_matches(self, text: str) -> list[tuple[int, int, float]]:
        matches: list[tuple[int, int, float]] = []
        for match in NUMBER_PATTERN.finditer(text):
            token = match.group(0)
            if self._is_year_token(token):
                continue
            value = coerce_number(token)
            if value is not None and abs(value) >= 1000:
                matches.append((match.start(), match.end(), value))
        return matches

    def _extract_statement_note(self, text: str) -> tuple[str | None, str]:
        text_without_formulas = self._remove_formula_spans(text)
        note_matches: list[tuple[int, int, str]] = []
        for match in STATEMENT_NOTE_PATTERN.finditer(text_without_formulas):
            token = match.group(0)
            normalized_note = self._normalize_statement_note(token)
            if normalized_note is None:
                continue
            note_matches.append((match.start(), match.end(), normalized_note))

        if not note_matches:
            return None, text_without_formulas

        start, end, note = note_matches[-1]
        is_structured_note = bool(re.search(r"[A-Za-z.]", note))
        is_trailing_note = start >= max(0, int(len(text_without_formulas) * 0.55))
        has_item_number = len(note_matches) >= 2
        if not (is_structured_note or is_trailing_note or has_item_number):
            return None, text_without_formulas

        return note, self._remove_spans(text_without_formulas, [(start, end)])

    def _normalize_statement_note(self, token: str | None) -> str | None:
        note = str(token or "").strip(" .|()")
        if not note:
            return None

        if re.fullmatch(r"\d+", note):
            value = int(note)
            if not 0 < value <= 99:
                return None
            return str(value)

        if re.fullmatch(r"\d{1,2}[,.]\d{1,2}", note):
            return note.replace(",", ".")

        if re.fullmatch(r"[IVXLCDM]{1,5}\.?\d{1,2}[A-Za-z]?", note, flags=re.IGNORECASE):
            return note.upper()

        if re.fullmatch(r"[A-Z]{1,4}\d{1,2}", note, flags=re.IGNORECASE):
            return note.upper()

        return None

    def _remove_formula_spans(self, text: str) -> str:
        cleaned = re.sub(r"\([^)]*=\s*[^)]*\)", " ", text)
        return self._clean_statement_line(cleaned)

    def _repair_split_number_groups(self, text: str) -> str:
        tokens = str(text or "").split()
        if len(tokens) < 2:
            return str(text or "")

        repaired: list[str] = []
        index = 0
        while index < len(tokens):
            merged_token = tokens[index]
            index += 1
            while index < len(tokens) and self._can_merge_split_thousand_group(merged_token, tokens[index]):
                merged_token = self._merge_split_thousand_group(merged_token, tokens[index])
                index += 1
            repaired.append(merged_token)

        return " ".join(repaired)

    def _can_merge_split_thousand_group(self, token: str, next_token: str) -> bool:
        if not re.fullmatch(r"\d{3}\)?", next_token):
            return False

        bare_token = token.strip("()")
        if not re.fullmatch(r"-?\d{1,3}(?:[,.]\d{3})+", bare_token):
            return False

        return True

    def _merge_split_thousand_group(self, token: str, next_token: str) -> str:
        closing = ")" if token.startswith("(") or next_token.endswith(")") else ""
        cleaned_token = token.rstrip(")")
        cleaned_next = next_token.rstrip(")")
        return f"{cleaned_token}.{cleaned_next}{closing}"

    def _remove_spans(self, text: str, spans: list[tuple[int, int]]) -> str:
        if not spans:
            return text
        output: list[str] = []
        cursor = 0
        for start, end in sorted(spans):
            output.append(text[cursor:start])
            cursor = end
        output.append(text[cursor:])
        return "".join(output)

    def _clean_statement_line(self, line: str) -> str:
        cleaned = " ".join(str(line or "").replace("\t", " ").split())
        cleaned = re.sub(r"^[|_\-–—=\s]+(?=\d{2,3}\b)", "", cleaned)
        return cleaned.strip()

    def _clean_statement_label(self, label: str) -> str:
        cleaned = re.sub(r"[|¬]+", " ", label)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip(" .:-–—")

    def _clean_statement_label(self, label: str, statement_key: str = "") -> str:
        cleaned = re.sub(r"[|Â¬]+", " ", label)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip(" .:-â€“â€”")
        cleaned = self._strip_statement_boilerplate(cleaned, statement_key)
        cleaned = re.sub(r"^(?:[IVX]+|\d+)\s*[.)]\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip(" .:-â€“â€”")

    def _strip_statement_boilerplate(self, label: str, statement_key: str) -> str:
        cleaned = label
        if not cleaned:
            return cleaned

        vnd_matches = list(re.finditer(r"\bVND\b", cleaned, flags=re.IGNORECASE))
        if len(vnd_matches) >= 2:
            cleaned = cleaned[vnd_matches[-1].end() :].strip(" .:-â€“â€”")

        normalized = normalize_label(cleaned)
        if statement_key == "cash_flow":
            section_markers = (
                "luu chuyen tien tu hoat dong kinh doanh",
                "luu chuyen tien tu hoat dong dau tu",
                "luu chuyen tien tu hoat dong tai chinh",
            )
            for marker in section_markers:
                if marker not in normalized:
                    continue
                trimmed = self._substring_from_normalized_window(cleaned, marker, after=True)
                if trimmed is not None:
                    cleaned = trimmed
                    normalized = normalize_label(cleaned)
                    break

        generic_markers = (
            "ma so thuyet minh",
            "ma thuyet",
            "mau so",
            "mau b",
            "ban hanh theo",
            "bo tai chinh",
        )
        if any(marker in normalized for marker in generic_markers):
            row_start = self._find_likely_row_label_start(cleaned, statement_key)
            if row_start:
                cleaned = row_start

        return cleaned

    def _substring_from_normalized_window(self, text: str, normalized_window: str, after: bool) -> str | None:
        tokens = text.split()
        normalized_tokens = [normalize_label(token) for token in tokens]
        window_size = len(normalized_window.split())
        for start in range(len(tokens)):
            window = " ".join(normalized_tokens[start : start + window_size])
            if window != normalized_window:
                continue
            output_tokens = tokens[start + window_size :] if after else tokens[start:]
            return " ".join(output_tokens).strip(" .:-â€“â€”")
        return None

    def _find_likely_row_label_start(self, label: str, statement_key: str) -> str | None:
        anchors_by_statement = {
            "financial_position": (
                "tai san ngan han",
                "tien va cac khoan tuong duong tien",
                "cac khoan phai thu ngan han",
                "hang ton kho",
                "tai san dai han",
                "tong cong tai san",
                "no phai tra",
                "no ngan han",
                "von chu so huu",
                "tong cong nguon von",
            ),
            "income_statement": (
                "doanh thu ban hang",
                "cac khoan giam tru",
                "doanh thu thuan",
                "gia von hang ban",
                "loi nhuan gop",
                "doanh thu hoat dong tai chinh",
                "chi phi tai chinh",
                "chi phi ban hang",
                "chi phi quan ly doanh nghiep",
                "loi nhuan thuan",
                "tong loi nhuan ke toan truoc thue",
                "loi nhuan sau thue",
            ),
            "cash_flow": (
                "loi nhuan truoc thue",
                "khau hao",
                "cac khoan du phong",
                "lai lo chenh lech ty gia",
                "lai tu hoat dong dau tu",
                "chi phi lai vay",
                "tang giam cac khoan phai thu",
                "tang giam hang ton kho",
                "tang giam cac khoan phai tra",
                "tien chi mua",
                "tien thu tu thanh ly",
                "tien chi cho vay",
                "tien thu hoi cho vay",
                "tien chi dau tu",
                "tien thu hoi dau tu",
                "tien thu lai cho vay",
                "tien thu tu di vay",
                "tien tra no goc vay",
                "co tuc loi nhuan da tra",
                "luu chuyen tien thuan",
                "tien va tuong duong tien dau nam",
                "anh huong cua thay doi ty gia",
                "tien va tuong duong tien cuoi nam",
            ),
        }
        anchors = anchors_by_statement.get(statement_key, ())
        normalized = normalize_label(label)
        best_anchor: str | None = None
        best_index = -1
        for anchor in anchors:
            index = normalized.rfind(anchor)
            if index > best_index:
                best_anchor = anchor
                best_index = index

        if best_anchor is None:
            return None
        return self._substring_from_normalized_window(label, best_anchor, after=False)

    def _statement_label_is_noise(self, label: str) -> bool:
        normalized = normalize_label(label)
        if not normalized:
            return True
        noisy_markers = (
            "cong ty",
            "bao cao tai chinh",
            "bao cao luu chuyen tien te",
            "bao cao ket qua hoat dong kinh doanh",
            "bang can doi ke toan",
            "mau so",
            "ban hanh theo",
            "bo tai chinh",
            "thong tu",
            "thuyet minh bao cao tai chinh",
        )
        if any(marker in normalized for marker in noisy_markers):
            return True
        return len(normalized.split()) > 36

    def _statement_row_noise_score(self, row: dict[str, Any]) -> int:
        label = str(row.get("label") or "")
        normalized = normalize_label(label)
        score = len(normalized.split())
        if self._statement_label_is_noise(label):
            score += 100
        if str(row.get("note") or "").isdigit():
            score -= 2
        return score

    def _repair_statement_table_row_code(
        self,
        row: dict[str, Any],
        statement_key: str,
        template_key: str | None = None,
    ) -> dict[str, Any]:
        current_code = self._normalize_statement_code(row.get("code"))
        current_note = str(row.get("note") or "").strip() if row.get("note") is not None else None
        current_label = str(row.get("label") or "")

        if self._find_mapping_item_by_code(statement_key, current_code, template_key) is not None:
            if current_code == row.get("code"):
                return row
            repaired = row.copy()
            repaired["code"] = current_code
            return repaired

        label_code = self._first_mapped_code_token(current_label, statement_key, template_key)
        note_code = self._first_mapped_code_token(current_note or "", statement_key, template_key)
        alias_code = self._infer_statement_code_from_label(current_label, statement_key)
        selected_code = label_code or note_code or alias_code
        if selected_code is None:
            return row

        repaired = row.copy()
        repaired["code"] = self._normalize_statement_code(selected_code)

        if label_code is not None:
            repaired["label"] = self._remove_statement_code_token_from_label(current_label, selected_code)
            if current_note is None and current_code and current_code != selected_code:
                repaired["note"] = current_code
        elif note_code is not None:
            repaired["note"] = None

        return repaired

    def _first_mapped_code_token(
        self,
        text: str,
        statement_key: str,
        template_key: str | None = None,
    ) -> str | None:
        for code in self._statement_code_tokens(text):
            if self._find_mapping_item_by_code(statement_key, code, template_key) is not None:
                return code
        return None

    def _statement_code_tokens(self, text: str) -> list[str]:
        tokens: list[str] = []
        for match in re.finditer(rf"(?<![\w.,])({STATEMENT_CODE_TEXT_PATTERN})(?![\w.,])", str(text or "")):
            token = self._normalize_statement_code(match.group(1))
            if token not in tokens:
                tokens.append(token)
        return tokens

    def _remove_statement_code_token_from_label(self, label: str, code: str) -> str:
        cleaned = re.sub(
            rf"(?<![\w.,]){re.escape(code)}(?![\w.,])",
            " ",
            label,
            count=1,
            flags=re.IGNORECASE,
        )
        cleaned = self._clean_statement_label(cleaned)
        return cleaned or label

    def _normalize_statement_code(self, code: Any) -> str:
        text = str(code or "").strip()
        match = re.fullmatch(rf"(\d{{2,3}})([A-Za-z]?)", text)
        if not match:
            return text
        return f"{match.group(1)}{match.group(2).lower()}"

    def _repair_embedded_statement_code(
        self,
        label: str,
        code: str,
        note: str | None,
    ) -> tuple[str, str, str | None]:
        parsed_code = self._statement_code_number(code) or 0

        if parsed_code <= 200:
            return label, code, note

        match = re.match(
            rf"^(?P<label>.+?)\s+(?P<code>{STATEMENT_CODE_TEXT_PATTERN})(?:\s+(?P<note>[A-Za-z0-9.]+))?$",
            label,
        )
        if not match:
            return label, code, note

        repaired_label = self._clean_statement_label(match.group("label"))
        repaired_code = self._normalize_statement_code(match.group("code"))
        repaired_note = self._normalize_statement_note(note or match.group("note"))
        return repaired_label, repaired_code, repaired_note

    def _looks_like_statement_label_hint(self, line: str) -> bool:
        normalized = normalize_label(line)
        if not normalized or len(normalized.split()) > 24:
            return False
        if self._material_number_matches(line):
            return False
        noisy_markers = (
            "cong ty",
            "bao cao",
            "bang can doi",
            "ma thuyet",
            "mau b",
            "mau so",
            "ban hanh",
            "bo tai chinh",
            "thong tu",
            "vnd",
            "trang",
            "thuyet minh",
        )
        if any(marker in normalized for marker in noisy_markers):
            return False
        if normalized in {"tai san", "nguon von", "ma so"}:
            return False
        if "31 12" in normalized or "1 1" in normalized:
            return False
        return any(char.isalpha() for char in normalized)

    def _merge_statement_label_hint(self, existing: str | None, line: str) -> str:
        if not existing:
            return line
        merged = f"{existing} {line}"
        return merged if len(normalize_label(merged).split()) <= 28 else line

    def _apply_statement_label_hint(self, row: dict[str, Any], hint: str | None) -> dict[str, Any]:
        if not hint:
            return row
        current_label = str(row.get("label") or "")
        normalized = normalize_label(current_label)
        needs_hint = (
            "=" in current_label
            or normalized in {"dich vu", "doanh", "tra khac"}
            or len(normalized.split()) <= 3
        )
        if not needs_hint:
            return row

        updated = row.copy()
        if len(normalized.split()) <= 3 and "=" not in current_label:
            updated["label"] = self._clean_statement_label(f"{hint} {current_label}")
        else:
            updated["label"] = self._clean_statement_label(hint)
        return updated

    def _deduplicate_statement_rows(self, rows: list[dict[str, Any]], statement_key: str) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        index_by_key: dict[tuple[str, int], int] = {}
        for row in rows:
            key = (str(row.get("code") or ""), int(row.get("page") or 0))
            existing_index = index_by_key.get(key)
            if existing_index is None:
                index_by_key[key] = len(deduped)
                deduped.append(row)
                continue

            existing = deduped[existing_index]
            if self._statement_row_confidence_score(row, statement_key) > self._statement_row_confidence_score(
                existing,
                statement_key,
            ):
                deduped[existing_index] = row
        return deduped

    def _statement_row_confidence_score(self, row: dict[str, Any], statement_key: str) -> int:
        label = str(row.get("label") or "")
        normalized = normalize_label(label)
        code = str(row.get("code") or "").strip()
        values = row.get("values") if isinstance(row.get("values"), dict) else {}
        value_count = sum(1 for value in values.values() if value is not None)
        score = value_count * 20

        if not self._statement_label_is_noise(label):
            score += 10
        else:
            score -= 100

        mapping_item = self._find_mapping_item_by_code(statement_key, code)
        if mapping_item is not None:
            score += 10
            if mapping_item.normalized_label in normalized or normalized in mapping_item.normalized_label:
                score += 60

        inferred_code = self._infer_statement_code_from_label(label, statement_key)
        if inferred_code == code:
            score += 40

        if code in {"100", "200", "270", "300", "400", "440"} and "tong" in normalized:
            score += 20

        return score

    def _build_report_navigation(self, pages: list[str]) -> list[dict[str, Any]]:
        toc_entries = self._extract_toc_navigation_entries(pages)
        heading_entries = self._extract_heading_navigation_entries(pages)
        if toc_entries:
            entries = self._resolve_toc_navigation_pages(toc_entries, pages)
            entries.extend(
                entry
                for entry in heading_entries
                if not self._has_navigation_duplicate(entries, entry)
            )
        else:
            entries = heading_entries

        entries = [
            entry
            for entry in entries
            if isinstance(entry.get("page"), int) and 1 <= int(entry["page"]) <= max(len(pages), 1)
        ]
        entries.sort(key=lambda item: (int(item["page"]), int(item.get("level") or 1), str(item.get("title") or "")))
        return self._deduplicate_navigation(entries)

    def _is_disclosure_navigation_title(self, normalized_title: str) -> bool:
        return any(marker in normalized_title for marker in DISCLOSURE_NAVIGATION_MARKERS)

    def _extract_toc_navigation_entries(self, pages: list[str]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for page_index, page_text in enumerate(pages[:10]):
            if "muc luc" not in normalize_label(page_text):
                continue

            for raw_line in page_text.splitlines():
                line = self._clean_navigation_line(raw_line)
                normalized = normalize_label(line)
                if not line or normalized in {"muc luc", "trang"} or len(line) < 6:
                    continue

                match = TOC_LINE_PATTERN.match(line)
                if not match:
                    continue

                title = match.group(1).strip(" ._-–—")
                normalized_title = normalize_label(title)
                if len(normalized_title) < 6:
                    continue
                if self._is_disclosure_navigation_title(normalized_title):
                    continue

                entries.append(
                    {
                        "title": title,
                        "page": None,
                        "report_page": int(match.group(2)),
                        "report_page_end": int(match.group(3)) if match.group(3) else None,
                        "level": 1,
                        "source": "toc",
                        "toc_page": page_index + 1,
                    }
                )
            break

        return entries

    def _resolve_toc_navigation_pages(
        self,
        entries: list[dict[str, Any]],
        pages: list[str],
    ) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        offsets: list[int] = []

        for entry in entries:
            actual_page = self._find_navigation_page_for_title(str(entry["title"]), pages)
            item = entry.copy()
            if actual_page is not None:
                item["page"] = actual_page
                item["resolved_by"] = "heading"
                report_page = item.get("report_page")
                if isinstance(report_page, int):
                    offsets.append(actual_page - report_page)
            resolved.append(item)

        fallback_offset = self._most_common_offset(offsets)
        for item in resolved:
            report_page = item.get("report_page")
            actual_page = item.get("page")
            if (
                offsets
                and item.get("resolved_by") == "heading"
                and isinstance(report_page, int)
                and isinstance(actual_page, int)
                and abs((actual_page - report_page) - fallback_offset) > 2
            ):
                item["page"] = max(1, min(len(pages), report_page + fallback_offset))
                item["resolved_by"] = "offset"

        for item in resolved:
            if item.get("page") is None and isinstance(item.get("report_page"), int):
                item["page"] = max(1, min(len(pages), int(item["report_page"]) + fallback_offset))
                item["resolved_by"] = "offset" if fallback_offset else "toc_report_page"
        return resolved

    def _extract_heading_navigation_entries(self, pages: list[str]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for page_index, page_text in enumerate(pages):
            if self._page_looks_like_toc(page_text):
                continue

            for raw_line in page_text.splitlines()[:18]:
                line = self._clean_navigation_line(raw_line)
                normalized = normalize_label(line)
                if len(normalized) < 6:
                    continue
                if self._is_disclosure_navigation_title(normalized):
                    continue

                if any(heading in normalized for heading in NAVIGATION_HEADINGS):
                    entries.append(
                        {
                            "title": self._format_navigation_title(line),
                            "page": page_index + 1,
                            "level": 1,
                            "source": "heading",
                        }
                    )
                    break

        return self._deduplicate_navigation(entries)

    def _find_navigation_page_for_title(self, title: str, pages: list[str]) -> int | None:
        normalized_title = normalize_label(title)
        if not normalized_title:
            return None

        for index, page_text in enumerate(pages):
            if self._page_looks_like_toc(page_text):
                continue
            if self._page_has_different_primary_heading(page_text, (normalized_title,)):
                continue
            page_head = "\n".join(str(page_text or "").splitlines()[:24])
            normalized_page_head = normalize_label(page_head)
            if normalized_title in normalized_page_head:
                return index + 1
            if self._navigation_title_matches_page(normalized_title, normalized_page_head):
                return index + 1
        return None

    def _page_looks_like_toc(self, page_text: str) -> bool:
        normalized = normalize_label(page_text)
        if not normalized:
            return False
        if "muc luc" in normalized:
            return True

        navigation_hits = sum(1 for heading in NAVIGATION_HEADINGS if heading in normalized)
        has_page_marker = "trang" in normalized or bool(re.search(r"\b\d{1,3}\s*-\s*\d{1,3}\b", normalized))
        return navigation_hits >= 3 and has_page_marker

    def _page_has_different_primary_heading(self, page_text: str, normalized_targets: tuple[str, ...]) -> bool:
        for raw_line in str(page_text or "").splitlines()[:12]:
            normalized_line = normalize_label(raw_line)
            if len(normalized_line) < 6:
                continue
            if not any(heading in normalized_line for heading in NAVIGATION_HEADINGS):
                continue
            return not any(
                target in normalized_line or normalized_line in target
                for target in normalized_targets
            )
        return False

    def _navigation_title_matches_page(self, normalized_title: str, normalized_page: str) -> bool:
        title_tokens = [
            token
            for token in normalized_title.split()
            if len(token) > 2 and not token.isdigit()
        ]
        if len(title_tokens) < 3:
            return False
        page_head = " ".join(normalized_page.split()[:160])
        hits = sum(1 for token in title_tokens if token in page_head)
        return hits / len(title_tokens) >= 0.72

    def _most_common_offset(self, offsets: list[int]) -> int:
        if not offsets:
            return 0
        return max(set(offsets), key=offsets.count)

    def _has_navigation_duplicate(self, entries: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
        candidate_title = normalize_label(candidate.get("title"))
        candidate_page = candidate.get("page")
        for entry in entries:
            same_title = normalize_label(entry.get("title")) == candidate_title
            same_page = entry.get("page") == candidate_page
            if same_title or (same_page and candidate_title in normalize_label(entry.get("title"))):
                return True
        return False

    def _deduplicate_navigation(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for entry in entries:
            page = int(entry.get("page") or 0)
            key = (normalize_label(entry.get("title")), page)
            if key in seen or not key[0] or page <= 0:
                continue
            seen.add(key)
            deduped.append(entry)
        return deduped

    def _clean_navigation_line(self, line: str) -> str:
        cleaned = " ".join(str(line or "").replace("\t", " ").split())
        return cleaned.strip(" .|`'\"")

    def _format_navigation_title(self, title: str) -> str:
        cleaned = self._clean_navigation_line(title)
        return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned

    def _clean_ocr_text(self, text: str) -> str:
        replacements = {
            "BANG CAN BOI KE TOÁN HỢP NHÁT": "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT",
            "BẰNG CÂN ĐÓI KÉ TOÁN HỢP NHÁT": "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT",
            "BẢNG CÂN ĐÓI KÉ TOÁN HỢP NHÁT": "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT",
            "BAO CAO KET QUA HOẠT ĐỘNG KINH DOANH HỢP NHAT": "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT",
            "BAO CAO KET QUA HOẠT ĐỘNG KINH DOANH HỢP NHẤT": "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT",
            "BÁO CÁO KÉT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHÁT": "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT",
            "Báo cáo tài chinh": "Báo cáo tài chính",
            "hợp nhắt": "hợp nhất",
            "Cổ phan": "Cổ phần",
            "Cô phân": "Cổ phần",
            "Sản xuât": "Sản xuất",
            "Đơn vi tính": "Đơn vị tính",
            "Đơn vỉ tính": "Đơn vị tính",
            "Don vị tính": "Đơn vị tính",
            "Don vi tính": "Đơn vị tính",
            "triêu VND": "triệu VND",
            "tiêu VND": "triệu VND",
            "ngay 31 thang 12 nam": "ngày 31 tháng 12 năm",
            "ngảy 31 tháng 12 năm": "ngày 31 tháng 12 năm",
            "TÀI SAN": "TÀI SẢN",
            "TÀI SÄN": "TÀI SẢN",
            "TÀI SẢN NGAN HAN": "TÀI SẢN NGẮN HẠN",
            "ngan han": "ngắn hạn",
            "ngắn han": "ngắn hạn",
            "ban hang": "bán hàng",
            "cung cap": "cung cấp",
            "dich vu": "dịch vụ",
            "Chi phi": "Chi phí",
            "Gia vốn": "Giá vốn",
        }
        cleaned = text
        for source, target in replacements.items():
            cleaned = cleaned.replace(source, target)
        return cleaned

    def _report_progress(
        self,
        progress_callback: ProgressCallback | None,
        progress: int,
        stage: str,
        message: str,
        statement: FinancialStatement | None = None,
    ) -> None:
        if progress_callback is not None:
            progress_callback(progress, stage, message, statement)

    def _ocr_page_count(self, total_pages: int, max_pages: int) -> int:
        if max_pages <= 0:
            return total_pages
        return min(total_pages, max_pages)

    def _infer_company_name(self, file_name: str, metadata: dict[str, Any]) -> str:
        title = str(metadata.get("Title") or metadata.get("title") or "").strip()
        if title and normalize_label(title) not in {"untitled", "none"}:
            return title
        return Path(file_name).stem.replace("_", " ").replace("-", " ").title() or "Imported PDF Company"

    def _clean_cell(self, value: Any) -> str:
        return " ".join(str(value or "").replace("\n", " ").split())
