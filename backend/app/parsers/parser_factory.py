from pathlib import Path

from app.parsers.base import FinancialStatementParser, ProgressCallback
from app.parsers.excel_parser import ExcelParser
from app.parsers.pdf_parser import PDFParser
from app.schemas.financial import FinancialStatement


class UnsupportedFileTypeError(ValueError):
    pass


class ParserFactory:
    """Selects the correct parser strategy based on file extension."""

    def __init__(self, parsers: list[FinancialStatementParser] | None = None) -> None:
        configured_parsers = parsers or [PDFParser(), ExcelParser()]
        self._parsers: dict[str, FinancialStatementParser] = {}

        for parser in configured_parsers:
            for extension in parser.supported_extensions:
                self._parsers[extension.lower().lstrip(".")] = parser

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return tuple(sorted(self._parsers.keys()))

    def get_parser(self, file_name: str) -> FinancialStatementParser:
        extension = Path(file_name).suffix.lower().lstrip(".")
        parser = self._parsers.get(extension)
        if parser is None:
            supported = ", ".join(f".{ext}" for ext in self.supported_extensions)
            raise UnsupportedFileTypeError(
                f"Unsupported file type '.{extension}'. Supported types: {supported}."
            )
        return parser

    def parse(
        self,
        file_name: str,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
    ) -> FinancialStatement:
        return self.get_parser(file_name).parse(file_name, content, progress_callback)
