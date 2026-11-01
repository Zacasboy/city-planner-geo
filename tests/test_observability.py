"""Testes da configuração do Sentry."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.observability import init_sentry

DSN = "https://chave@o0.ingest.sentry.io/1"


def _settings(**overrides: object) -> Settings:
    return Settings(
        SUPABASE_URL="http://fake",
        SUPABASE_PUBLISHABLE_KEY="fake",
        SUPABASE_SECRET_KEY="fake",
        _env_file=None,
        **overrides,  # type: ignore[arg-type]
    )


def test_sentry_stays_off_without_dsn() -> None:
    with patch("sentry_sdk.init") as init:
        assert init_sentry(_settings()) is False
    init.assert_not_called()


def test_sentry_never_sends_personal_data_or_request_bodies() -> None:
    with patch("sentry_sdk.init") as init:
        assert init_sentry(_settings(SENTRY_DSN=DSN)) is True
    kwargs = init.call_args.kwargs
    assert kwargs["dsn"] == DSN
    assert kwargs["send_default_pii"] is False
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["traces_sample_rate"] == 0.0


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "production"),
        ({"DEBUG": True}, "development"),
        ({"SENTRY_ENVIRONMENT": "staging"}, "staging"),
    ],
)
def test_sentry_environment(overrides: dict[str, object], expected: str) -> None:
    with patch("sentry_sdk.init") as init:
        init_sentry(_settings(SENTRY_DSN=DSN, **overrides))
    assert init.call_args.kwargs["environment"] == expected


def test_trace_sample_rate_must_be_a_probability() -> None:
    with pytest.raises(ValidationError):
        _settings(SENTRY_TRACES_SAMPLE_RATE=1.5)
