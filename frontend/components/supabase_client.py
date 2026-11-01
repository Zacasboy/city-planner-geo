"""Cliente Supabase partilhado pelas páginas de login e registo."""

import streamlit as st

from frontend.components.settings import get_setting
from supabase import Client, create_client


def get_supabase_client() -> Client | None:
    """Cria o cliente Supabase com a chave publicável.

    Mostra um aviso ou um erro no ecrã se a configuração faltar ou for inválida.

    Returns:
        O cliente, ou None se não for possível criá-lo.
    """
    url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_PUBLISHABLE_KEY")
    if not (url and key):
        st.warning(
            "Supabase credentials not configured. "
            "Please set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."
        )
        return None
    try:
        return create_client(url, key)
    except Exception as e:  # a biblioteca levanta tipos diferentes para URL/chave inválidas
        st.error(f"Failed to initialize Supabase client: {e}")
        return None
