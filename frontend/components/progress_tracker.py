"""Indicador de progresso por etapas.

T1.10: dashboards ecológico/florestal e ProgressTracker.
"""

import streamlit as st


def render_progress_tracker(steps: list[str], current_step_index: int) -> None:
    """Mostra uma barra de progresso e o estado de cada etapa.

    Args:
        steps: Nomes das etapas.
        current_step_index: Índice (a partir de 0) da etapa em curso.
    """
    if not steps:
        return

    progress = (current_step_index + 1) / len(steps) if current_step_index < len(steps) else 1.0
    st.progress(progress)

    columns = st.columns(len(steps))
    for index, (column, step) in enumerate(zip(columns, steps, strict=True)):
        with column:
            if index < current_step_index:
                st.markdown(f"✅ {step}")
            elif index == current_step_index:
                st.markdown(f"🔄 {step}")
            else:
                st.markdown(f"⏳ {step}")
