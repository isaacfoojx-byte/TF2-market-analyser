import streamlit as st


def metric_row(metrics: list[tuple]):
    """Render metrics, optionally with hover help as a fourth tuple value."""

    cols = st.columns(len(metrics))

    for col, metric in zip(cols, metrics):
        label, value, delta = metric[:3]
        help_text = metric[3] if len(metric) > 3 else None
        with col:
            st.metric(
                label=label,
                value=value,
                delta=delta,
                help=help_text,
            )
