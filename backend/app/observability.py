"""Observabilidade: relatório de erros para o Sentry (T0.6)."""

import logging

import sentry_sdk

from backend.app.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(config: Settings) -> bool:
    """Liga o Sentry se `SENTRY_DSN` estiver definido.

    Não envia dados pessoais (cabeçalhos, cookies, IP) nem o corpo dos pedidos, porque os
    pedidos têm tokens e geometrias dos utilizadores (Rules R8: sem PII em logs).

    Args:
        config: Definições da aplicação.

    Returns:
        True se o Sentry ficou ativo, False se não há DSN.
    """
    if not config.SENTRY_DSN:
        return False
    environment = config.SENTRY_ENVIRONMENT or ("development" if config.DEBUG else "production")
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=environment,
        release=f"{config.APP_NAME}@{config.APP_VERSION}",
        traces_sample_rate=config.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
        max_request_body_size="never",
    )
    logger.info("Sentry enabled (environment=%s)", environment)
    return True
