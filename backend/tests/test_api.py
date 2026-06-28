import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_vinfast_fixture_dashboard_endpoint():
    response = client.get("/api/v1/fixtures/vinfast-dashboard")
    payload = response.json()

    assert response.status_code == 200
    assert payload["company"]["ticker"] == "VFS"
    assert payload["quality_of_earnings"]["alert_level"] == "red"
    assert payload["pillars"]["profitability"][-1]["roe"] is None
    assert payload["pillars"]["solvency"][-1]["debt_to_equity"] is None


def test_metrics_endpoint_accepts_normalized_json():
    fixture_path = Path(__file__).parents[1] / "test_data" / "vinfast_statement.json"
    statement = json.loads(fixture_path.read_text(encoding="utf-8"))

    response = client.post("/api/v1/metrics", json=statement)

    assert response.status_code == 200
    assert response.json()["company"]["ticker"] == "VFS"


def test_parse_job_endpoint_tracks_status_until_completed():
    pdf_bytes = _simple_pdf(
        [
            "2024 2025",
            "total assets 100,000 120,000",
            "total equity 40,000 45,000",
            "net revenue 80,000 95,000",
            "net income 8,000 9,500",
            "operating cash flow 7,500 10,000",
        ]
    )

    response = client.post(
        "/api/v1/parse-jobs",
        files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
    )
    payload = response.json()

    assert response.status_code == 202
    assert payload["job_id"]

    snapshot = payload
    for _ in range(50):
        status_response = client.get(f"/api/v1/parse-jobs/{payload['job_id']}")
        snapshot = status_response.json()
        if snapshot["status"] == "completed":
            break
        time.sleep(0.1)

    assert snapshot["status"] == "completed"
    assert snapshot["progress"] == 100
    assert snapshot["statement"]["source_type"] == "pdf"
    assert snapshot["statement"]["periods"][-1]["income_statement"]["net_revenue"] == 95000.0

    cached_response = client.post(
        "/api/v1/parse-jobs",
        files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
    )
    cached_payload = cached_response.json()

    assert cached_response.status_code == 202
    assert cached_payload["status"] == "completed"
    assert cached_payload["stage"] == "cache_hit"
    assert cached_payload["statement"]["metadata"]["cache_hit"] is True


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
