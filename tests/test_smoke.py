"""Smoke test: confirma que os pacotes do projeto são importáveis."""

import importlib

import pytest

PACKAGES = ["backend", "frontend", "shared"]


@pytest.mark.parametrize("package", PACKAGES)
def test_package_is_importable(package: str) -> None:
    assert importlib.import_module(package) is not None
