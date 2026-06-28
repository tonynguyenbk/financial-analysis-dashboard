import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.parsers.parser_factory import ParserFactory, UnsupportedFileTypeError
from app.parsers.sample_data import build_mock_statement
from app.schemas.financial import FinancialStatement
from app.schemas.jobs import ParseJobSnapshot
from app.services.metrics_engine import calculate_all_metrics
from app.services.parse_jobs import ParseJobStore

router = APIRouter(tags=["analysis"])
parser_factory = ParserFactory()
parse_job_store = ParseJobStore(parser_factory)
TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


@router.get("/mock-statement", response_model=FinancialStatement)
def get_mock_statement() -> FinancialStatement:
    return build_mock_statement(source_type="mock")


@router.get("/mock-dashboard")
def get_mock_dashboard() -> dict:
    statement = build_mock_statement(source_type="mock")
    return calculate_all_metrics(statement)


@router.get("/fixtures/vinfast-statement", response_model=FinancialStatement)
def get_vinfast_statement() -> FinancialStatement:
    return _load_statement_fixture("vinfast_statement.json")


@router.get("/fixtures/vinfast-dashboard")
def get_vinfast_dashboard() -> dict:
    statement = _load_statement_fixture("vinfast_statement.json")
    return calculate_all_metrics(statement)


@router.post(
    "/parse-jobs",
    response_model=ParseJobSnapshot,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_parse_job(file: UploadFile = File(...)) -> ParseJobSnapshot:
    file_name = file.filename or ""
    content = await file.read()
    try:
        parser_factory.get_parser(file_name)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc

    return parse_job_store.start_parse_job(file_name, content)


@router.get("/parse-jobs/{job_id}", response_model=ParseJobSnapshot)
def get_parse_job(job_id: str) -> ParseJobSnapshot:
    snapshot = parse_job_store.get_job(job_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parse job not found: {job_id}",
        )
    return snapshot


@router.post("/parse", response_model=FinancialStatement)
async def parse_financial_statement(file: UploadFile = File(...)) -> FinancialStatement:
    content = await file.read()
    try:
        return await run_in_threadpool(parser_factory.parse, file.filename or "", content)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/analyze")
async def analyze_uploaded_statement(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    try:
        statement = await run_in_threadpool(parser_factory.parse, file.filename or "", content)
        return await run_in_threadpool(calculate_all_metrics, statement)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/metrics")
def calculate_metrics(statement: FinancialStatement) -> dict:
    return calculate_all_metrics(statement)


def _load_statement_fixture(file_name: str) -> FinancialStatement:
    fixture_path = TEST_DATA_DIR / file_name
    if not fixture_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fixture not found: {file_name}",
        )

    with fixture_path.open(encoding="utf-8") as fixture_file:
        return FinancialStatement(**json.load(fixture_file))
