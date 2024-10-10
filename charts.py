from pathlib import Path

import pandas as pd
import plotly.express as px
from process_energy_data import fetch_energy_data, get_energy_category_map
from process_fiscal_data import get_country_list, get_net_value_country


def main():
    pass


def get_macronutrient_timeseries_chart_div(category: str):
    cur_dir = Path(__file__).parent.resolve()
    df_path = str(cur_dir / "data" / "macronutrients" / "net_macronutrients.csv")
    df = pd.read_csv(df_path)

    # Create figure
    fig = px.line(df, x="date", y=category, markers=True)

    # Update layout title and add range slider
    fig.update_layout(
        title=f"Net {category} vs Time",
        xaxis=dict(rangeslider=dict(visible=True), type="date"),
    )

    fig.update_traces(
        line=dict(color="blue", width=2), marker=dict(size=8, color="red")
    )

    fig.update_xaxes(zeroline=True, zerolinewidth=2, zerolinecolor="LightPink")

    div = fig.to_html(
        full_html=False, include_plotlyjs=True, div_id=f"chart_{category}"
    )
    return div


def get_fiscal_timeseries_chart_div(country: str):
    df = get_net_value_country(country)

    # Create figure
    fig = px.line(df, x="Fiscal Year", y="net_value")
    # Set title
    fig.update_layout(title_text=f"{country} Net Value Products")
    # Add range slider
    fig.update_layout(
        xaxis=dict(rangeslider=dict(visible=True), type="-"),
    )
    div = fig.to_html(full_html=False, include_plotlyjs=True, div_id=f"chart_{country}")
    return div


def get_energy_timeseries_chart_div(category: str = "agricultural_consumption_mkwh"):
    df = fetch_energy_data()

    agricultural_categories_dict = get_energy_category_map()
    selected_category_col_name = agricultural_categories_dict[category]

    # Create figure
    fig = px.line(df, x="Date", y=selected_category_col_name)

    # Set title
    fig.update_layout(title_text="")

    # Add range slider
    fig.update_layout(
        xaxis=dict(rangeslider=dict(visible=True), type="date"),
    )

    div = fig.to_html(
        full_html=False, include_plotlyjs=True, div_id=f"chart_{category}"
    )

    return div


if __name__ == "__main__":
    main()
