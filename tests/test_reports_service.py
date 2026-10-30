"""Tests for PDF rendering in the reports service."""

import os

os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "fake")
os.environ.setdefault("SUPABASE_SECRET_KEY", "fake")
os.environ.setdefault("SECRET_KEY", "fakesecret")

import pytest

from backend.app.services.reports_service import ReportsService


def test_service_import_does_not_require_weasyprint():
    assert not hasattr(ReportsService, "font_config")


def test_render_pdf_returns_pdf_bytes():
    try:
        pdf = ReportsService._render_pdf("<html><body><p>Relatório</p></body></html>")
    except (ImportError, OSError):
        pytest.skip("WeasyPrint system libraries (pango) are not installed")
    assert pdf.startswith(b"%PDF-")
