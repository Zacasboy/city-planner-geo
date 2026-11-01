"""Configuração comum dos testes.

Define as variáveis obrigatórias de `Settings` antes de qualquer import da aplicação,
para os testes correrem sem `.env` (por exemplo no CI).
"""

import os

os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "fake")
os.environ.setdefault("SUPABASE_SECRET_KEY", "fake")
os.environ.setdefault("SECRET_KEY", "fakesecret")
