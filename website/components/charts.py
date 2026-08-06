def style_bar_chart(
    fig,
    x_title,
    y_title,
):
    fig.update_traces(
        textposition="outside",
    )

    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title=y_title,
        showlegend=False,
        template="plotly_dark",
    )

    return fig
