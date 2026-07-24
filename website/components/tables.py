import streamlit as st


def show_table(df):
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
    )

