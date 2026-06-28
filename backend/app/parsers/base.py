from abc import ABC, abstractmethod
from collections.abc import Callable

from app.schemas.financial import FinancialStatement

ProgressCallback = Callable[[int, str, str, FinancialStatement | None], None]


class FinancialStatementParser(ABC):
    """Strategy interface for financial statement ingestion."""

    supported_extensions: tuple[str, ...] = ()

    def supports(self, extension: str) -> bool:
        normalized_extension = extension.lower().lstrip(".")
        return normalized_extension in self.supported_extensions

    @abstractmethod
    def parse(
        self,
        file_name: str,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
    ) -> FinancialStatement:
        """Parse raw file bytes into the normalized financial JSON contract."""
