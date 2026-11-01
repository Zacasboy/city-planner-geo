"""Tests for PDF rendering in the reports service."""

import os

os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "fake")
os.environ.setdefault("SUPABASE_SECRET_KEY", "fake")
os.environ.setdefault("SECRET_KEY", "fakesecret")

from unittest.mock import MagicMock

import pytest

from backend.app.services import reports_service
from backend.app.services.reports_service import ReportsService


def test_service_import_does_not_require_weasyprint():
    assert not hasattr(ReportsService, "font_config")


def test_render_pdf_returns_pdf_bytes():
    try:
        pdf = ReportsService._render_pdf("<html><body><p>Relatório</p></body></html>")
    except (ImportError, OSError):
        pytest.skip("WeasyPrint system libraries (pango) are not installed")
    assert pdf.startswith(b"%PDF-")


BEAM = {
    "length": 5,
    "width": 0.2,
    "height": 0.4,
    "youngs_modulus": 210e9,
    "density": 7850,
    "yield_stress": 355e6,
    "point_loads": [{"magnitude": 10000, "position": 2.5}],
    "supports": [{"type": "pinned", "position": 0}, {"type": "roller", "position": 5}],
}
RESULTS = {
    "max_deflection": 0.002,
    "max_stress": 100e6,
    "utilization_ratio": 0.4,
    "details": {"max_moment": 12500},
}


@pytest.mark.asyncio
async def test_generated_html_escapes_request_values(monkeypatch):
    rendered = {}

    def fake_render(html_string: str) -> bytes:
        rendered["html"] = html_string
        return b"%PDF-fake"

    uploads = []
    storage = MagicMock()
    storage.from_.return_value.upload.side_effect = lambda *args: uploads.append(args)
    monkeypatch.setattr(reports_service, "supabase", MagicMock(storage=storage))
    monkeypatch.setattr(ReportsService, "_render_pdf", staticmethod(fake_render))

    beam = BEAM | {"supports": [{"type": "<script>alert(1)</script>", "position": 0}]}
    report_id = await ReportsService().generate_structural_report(beam, RESULTS, user_id="<b>x</b>")

    assert "<script>" not in rendered["html"]
    assert "&lt;script&gt;" in rendered["html"]
    assert "&lt;b&gt;x&lt;/b&gt;" in rendered["html"]
    assert uploads[0][0] == f"reports/{report_id}.pdf"
    assert uploads[0][1] == b"%PDF-fake"


@pytest.mark.asyncio
async def test_generated_html_shows_safe_status(monkeypatch):
    rendered = {}
    monkeypatch.setattr(
        ReportsService,
        "_render_pdf",
        staticmethod(lambda h: rendered.setdefault("html", h).encode()),
    )
    monkeypatch.setattr(reports_service, "supabase", MagicMock())

    await ReportsService().generate_structural_report(BEAM, RESULTS)

    assert "SAFE" in rendered["html"]
    assert "UNSAFE" not in rendered["html"]
