"""ProgressTracker Component
T1.10: Dashboards ecológico/florestal e ProgressTracker
"""

import streamlit as st


def render_progress_tracker(steps, current_step_index):
    """Render a progress tracker with steps and current step index.

    Args:
        steps: List of step labels (strings)
        current_step_index: Index of the current step (0-based)
    """
    if not steps:
        return

    # Calculate progress percentage
    progress = (current_step_index + 1) / len(steps) if current_step_index < len(steps) else 1.0

    # Display progress bar
    st.progress(progress)

    # Display step labels
    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if i < current_step_index:
                st.markdown(f"✅ {step}")
            elif i == current_step_index:
                st.markdown(f"🔄 {step}")
            else:
                st.markdown(f"⏳ {step}")
