from io import BytesIO
from typing import Any

import pandas as pd

from app.parsers.base import FinancialStatementParser, ProgressCallback
from app.parsers.normalization import build_statement_from_metric_records, normalize_label
from app.parsers.sample_data import build_mock_statement
from app.schemas.financial import FinancialStatement


class ExcelParser(FinancialStatementParser):
    """Pandas/openpyxl Excel parser strategy.

    Supported input shapes:
    - Long format: metric/period/value columns.
    - Wide format: first column is metric, remaining columns are periods.
    """

    supported_extensions = ("xls", "xlsx")

    def parse(
        self,
        file_name: str,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
    ) -> FinancialStatement:
        self._report_progress(progress_callback, 5, "received", "Excel file received.")
        if not content:
            return self._fallback_mock(file_name, "Empty Excel file content.")

        try:
            self._report_progress(progress_callback, 25, "extracting", "Reading Excel workbook.")
            sheets = pd.read_excel(BytesIO(content), sheet_name=None)
        except Exception as exc:
            return self._fallback_mock(file_name, f"Pandas could not parse workbook: {exc}")

        self._report_progress(progress_callback, 65, "extracting", "Extracting financial rows from workbook sheets.")
        records = self._extract_metric_records(sheets)
        if not records:
            return self._fallback_mock(file_name, "Workbook did not match a supported template.")

        self._report_progress(progress_callback, 92, "normalizing", "Normalizing extracted Excel rows.")
        return build_statement_from_metric_records(
            company={"name": "Imported Excel Company"},
            records=records,
            source_type="excel",
            metadata={
                "parser": "ExcelParser",
                "source_file": file_name,
                "sheets": list(sheets.keys()),
            },
        )

    def _fallback_mock(self, file_name: str, reason: str) -> FinancialStatement:
        statement = build_mock_statement(source_type="excel")
        statement.metadata.update(
            {
                "parser": "ExcelParser",
                "source_file": file_name,
                "warning": reason,
                "fallback": "Returned mock normalized data for early API integration.",
            }
        )
        return statement

    def _report_progress(
        self,
        progress_callback: ProgressCallback | None,
        progress: int,
        stage: str,
        message: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(progress, stage, message, None)

    def _extract_metric_records(self, sheets: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for sheet_name, frame in sheets.items():
            if frame.empty:
                continue

            normalized_columns = {column: normalize_label(column) for column in frame.columns}
            metric_column = self._find_column(normalized_columns, ["metric", "label", "account", "item", "chi tieu", "code"])
            if metric_column is None:
                continue

            period_column = self._find_column(normalized_columns, ["period", "year", "fiscal year", "nam", "ky"])
            value_column = self._find_column(normalized_columns, ["value", "amount", "gia tri", "so tien"])

            if period_column is not None and value_column is not None:
                records.extend(
                    {
                        "metric": row.get(metric_column),
                        "period": row.get(period_column),
                        "value": row.get(value_column),
                        "sheet": sheet_name,
                    }
                    for _, row in frame.iterrows()
                )
                continue

            period_value_columns = [
                column
                for column in frame.columns
                if column != metric_column and self._looks_like_period(column)
            ]
            for _, row in frame.iterrows():
                for period in period_value_columns:
                    records.append(
                        {
                            "metric": row.get(metric_column),
                            "period": period,
                            "value": row.get(period),
                            "sheet": sheet_name,
                        }
                    )

        return records

    def _find_column(self, columns: dict[Any, str], candidates: list[str]) -> Any | None:
        candidate_set = {normalize_label(candidate) for candidate in candidates}
        for original_column, normalized_column in columns.items():
            if normalized_column in candidate_set:
                return original_column
        return None

    def _looks_like_period(self, column: Any) -> bool:
        normalized = normalize_label(column)
        return normalized.isdigit() and len(normalized) == 4
