import streamlit as st

def metric_row(metrics: list[tuple[str, str, str | None]]):
    cols = st.columns(len(metrics))

    for col, (label, value, delta) in zip(cols, metrics):
        with col:
            st.metric(
                label=label,
                value=value,
                delta=delta,
            )