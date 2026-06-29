import os
from hashlib import sha256
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.parsers.parser_factory import ParserFactory
from app.schemas.financial import FinancialStatement
from app.schemas.jobs import ParseJobSnapshot


PARSE_CACHE_VERSION = "financial-dashboard-parser-v11"


class ParseJobStore:
    def __init__(self, parser_factory: ParserFactory) -> None:
        max_workers = int(os.getenv("PARSE_JOB_WORKERS", "2"))
        default_cache_dir = Path(__file__).resolve().parents[2] / ".cache" / "parse_jobs"
        cache_dir = os.getenv("PARSE_JOB_CACHE_DIR", str(default_cache_dir))
        self._parser_factory = parser_factory
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: dict[str, ParseJobSnapshot] = {}
        self._statement_cache: dict[str, FinancialStatement] = {}
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir is not None:
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                self._cache_dir = None
        self._lock = Lock()

    def start_parse_job(self, file_name: str, content: bytes) -> ParseJobSnapshot:
        job_id = uuid4().hex
        content_hash = sha256(content).hexdigest()
        cached_statement = self._get_cached_statement(content_hash, file_name)
        if cached_statement is not None:
            snapshot = ParseJobSnapshot(
                job_id=job_id,
                status="completed",
                progress=100,
                stage="cache_hit",
                message="Standardized report loaded from cache.",
                file_name=file_name,
                statement=cached_statement,
            )
            with self._lock:
                self._jobs[job_id] = snapshot
            return snapshot.model_copy(deep=True)

        snapshot = ParseJobSnapshot(
            job_id=job_id,
            status="queued",
            progress=0,
            stage="queued",
            message="File queued for standardization.",
            file_name=file_name,
        )
        with self._lock:
            self._jobs[job_id] = snapshot

        self._executor.submit(self._run_parse_job, job_id, file_name, content, content_hash)
        return self.get_job(job_id) or snapshot

    def get_job(self, job_id: str) -> ParseJobSnapshot | None:
        with self._lock:
            snapshot = self._jobs.get(job_id)
            return snapshot.model_copy(deep=True) if snapshot else None

    def _run_parse_job(self, job_id: str, file_name: str, content: bytes, content_hash: str) -> None:
        self._update_job(
            job_id,
            status="running",
            progress=1,
            stage="received",
            message="File received. Starting standardization.",
        )

        def update_progress(
            progress: int,
            stage: str,
            message: str,
            statement: FinancialStatement | None = None,
        ) -> None:
            changes: dict[str, object] = {
                "status": "running",
                "progress": max(1, min(99, progress)),
                "stage": stage,
                "message": message,
            }
            if statement is not None:
                changes["statement"] = statement
            self._update_job(job_id, **changes)

        try:
            statement = self._parser_factory.parse(file_name, content, update_progress)
            self._store_cached_statement(content_hash, statement)
            self._update_job(
                job_id,
                status="completed",
                progress=100,
                stage="completed",
                message="Standardized report is ready.",
                statement=statement,
                error=None,
            )
        except Exception as exc:
            current = self.get_job(job_id)
            self._update_job(
                job_id,
                status="failed",
                progress=current.progress if current else 100,
                stage="failed",
                message="Standardization failed.",
                error=str(exc),
            )

    def _update_job(self, job_id: str, **changes: object) -> None:
        with self._lock:
            current = self._jobs.get(job_id)
            if current is None:
                return
            data = current.model_dump()
            data.update(changes)
            self._jobs[job_id] = ParseJobSnapshot(**data)

    def _get_cached_statement(self, content_hash: str, file_name: str) -> FinancialStatement | None:
        with self._lock:
            cached = self._statement_cache.get(content_hash)
        if cached is not None:
            return self._statement_for_file_name(cached, file_name)

        cache_path = self._cache_path(content_hash)
        if cache_path is None or not cache_path.exists():
            return None

        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("cache_version") != PARSE_CACHE_VERSION:
                return None
            statement = FinancialStatement(**payload["statement"])
        except Exception:
            return None

        with self._lock:
            self._statement_cache[content_hash] = statement
        return self._statement_for_file_name(statement, file_name)

    def _store_cached_statement(self, content_hash: str, statement: FinancialStatement) -> None:
        with self._lock:
            self._statement_cache[content_hash] = statement

        cache_path = self._cache_path(content_hash)
        if cache_path is None:
            return

        payload = {
            "cache_version": PARSE_CACHE_VERSION,
            "statement": statement.model_dump(mode="json"),
        }
        try:
            cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except OSError:
            return

    def _cache_path(self, content_hash: str) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / f"{content_hash}.json"

    def _statement_for_file_name(self, statement: FinancialStatement, file_name: str) -> FinancialStatement:
        cached = statement.model_copy(deep=True)
        cached.metadata["source_file"] = file_name
        cached.metadata["cache_hit"] = True
        return cached
