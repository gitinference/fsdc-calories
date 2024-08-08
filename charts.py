import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go


from process_energy_data import fetch_energy_data


def main():
    get_energy_timeseries_chart_div()


def get_energy_timeseries_chart_div(category: str = "gross_generation"):
    df = fetch_energy_data()

    # Create figure
    fig = px.line(df, x="Date", y="Generación Bruta  (mkWh)")

    # Set title
    fig.update_layout(
        title_text=""
    )

    # Add range slider
    fig.update_layout(
        xaxis=dict(
            rangeslider=dict(
                visible=True
            ),
            type="date"
        ),
    )

    div = fig.to_html(full_html=False, include_plotlyjs='cdn')

    return div


if __name__ == '__main__':
    main()
