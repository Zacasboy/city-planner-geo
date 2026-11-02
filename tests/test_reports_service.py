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
    assert uploads[0][0] == f"<b>x</b>/{report_id}.pdf"
    assert uploads[0][1] == b"%PDF-fake"


ECOLOGY = {
    "total_records": 120,
    "records_excluded_by_license": 7,
    "allowed_licenses": ["CC0_1_0", "CC_BY_4_0"],
    "species": [{"scientific_name": "Quercus suber <b>", "records": 42}],
    "notes": ["Only open licences."],
}


def _render(monkeypatch, **kwargs):
    rendered = {}
    monkeypatch.setattr(
        ReportsService,
        "_render_pdf",
        staticmethod(lambda h: rendered.setdefault("html", h).encode()),
    )
    monkeypatch.setattr(reports_service, "supabase", MagicMock())
    return rendered, kwargs


@pytest.mark.asyncio
async def test_html_has_neutral_status_and_disclaimer(monkeypatch):
    rendered, _ = _render(monkeypatch)

    await ReportsService().generate_structural_report(BEAM, RESULTS, user_id="ana")

    assert "not a code check" in rendered["html"]
    assert "preliminary estimate" in rendered["html"]
    assert "Ecological Context" not in rendered["html"]


@pytest.mark.asyncio
async def test_html_includes_escaped_ecology_context(monkeypatch):
    rendered, _ = _render(monkeypatch)

    await ReportsService().generate_structural_report(BEAM, RESULTS, user_id="ana", ecology=ECOLOGY)

    html = rendered["html"]
    assert "Ecological Context" in html
    assert "Quercus suber &lt;b&gt;" in html
    assert "<b>" not in html.split("Ecological Context")[1].split("Disclaimer")[0]
    assert "CC0_1_0" in html


@pytest.mark.asyncio
async def test_html_supports_explicit_section(monkeypatch):
    rendered, _ = _render(monkeypatch)
    beam = {k: v for k, v in BEAM.items() if k not in ("width", "height")} | {
        "section": {"area": 0.01, "moment_of_inertia": 1e-5, "height": 0.2}
    }

    await ReportsService().generate_structural_report(beam, RESULTS, user_id="ana")

    assert "Moment of Inertia" in rendered["html"]
