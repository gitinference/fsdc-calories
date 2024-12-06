from pathlib import Path

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from process_energy_data import fetch_energy_data, get_energy_category_map
from process_fiscal_data import get_country_list, get_net_value_country
from process_price_data import save_top_ranking_products


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
    df = pd.read_csv("data/energy/processed_energy_data.csv")
    
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


def get_product_price_ranking_timeseries_div():
    # Load the imports and exports data
    if not os.path.exists("data/prices/price_imports.csv"):
        save_top_ranking_products()

    imports = pd.read_csv("data/prices/price_imports.csv")
    exports = pd.read_csv("data/prices/price_exports.csv")

    # Ensure hs4 column is treated as a string
    imports["hs4"] = imports["hs4"].astype(str)
    exports["hs4"] = exports["hs4"].astype(str)

    # Create figure with two bar traces
    fig = go.Figure()

    # Add a bar trace for the imports with hover labels
    fig.add_trace(go.Bar(
        x=imports['hs4'],
        y=imports['pct_change_moving_price'],
        name='Imports Price Change',
        marker_color='blue',
        hovertemplate='<b>HS4 Code: %{x}</b><br>' +
                      'Price Change: %{y:.2f} %<br>' +
                      '<extra></extra>'  # Remove the secondary info (trace name)
    ))

    # Optionally, add a trace for exports with hover labels
    fig.add_trace(go.Bar(
        x=exports['hs4'],
        y=exports['pct_change_moving_price'],
        name='Exports Price Change',
        marker_color='orange',
        hovertemplate='<b>HS4 Code: %{x}</b><br>' +
                      'Price Change: %{y:.2f} %<br>' +
                      '<extra></extra>'  # Remove the secondary info (trace name)
    ))

    # Update layout
    fig.update_layout(
        title='Price Change by HS4 Code',
        xaxis_title='HS4 Code',
        yaxis_title='Percentage Change in Price',
        barmode='group',
        xaxis_tickangle=-45  # Rotate x-axis labels for better readability
    )

    # Generate the HTML div for embedding
    div = fig.to_html(full_html=False, include_plotlyjs=True, div_id="price_chart")

    return div


if __name__ == "__main__":
    get_product_price_ranking_timeseries_div()
