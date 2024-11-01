import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from process_price_data import save_top_ranking_products


def get_product_price_ranking_timeseries_div(n: int = None):
    if not n:
        n = 100

    # Generate and load the imports and exports data for the given year
    if not os.path.exists("data/prices/yearly_average_price_imports.csv"):
        save_top_ranking_products(n)

    imports = pd.read_csv("data/prices/yearly_average_price_imports.csv")
    exports = pd.read_csv("data/prices/yearly_average_price_exports.csv")

    # Ensure hs4 column is treated as a string and has 4 characters
    imports["hs4"] = imports["hs4"].astype(str).apply(lambda x: x.zfill(4))
    exports["hs4"] = exports["hs4"].astype(str).apply(lambda x: x.zfill(4))

    # Map each trimester to a month
    trimester_to_month = {1: "01", 2: "04", 3: "07", 4: "10"}

    # Create a synthetic date column based on year and trimester
    imports["date"] = pd.to_datetime(
        imports["year"].astype(str)
        + "-"
        + imports["trimester"].map(trimester_to_month)
        + "-01"
    )
    exports["date"] = pd.to_datetime(
        exports["year"].astype(str)
        + "-"
        + exports["trimester"].map(trimester_to_month)
        + "-01"
    )

    # Sort data by YoY percentage change in imports for display purposes
    imports.sort_values(by="yoy_pct_change_imports", inplace=True, ascending=False)

    # Remove rows with NaN values in YoY percentage change or date column
    imports.dropna(subset=["yoy_pct_change_imports", "date"], inplace=True)

    # Separate positive and negative YoY percentage change values for better color control
    positive_changes = imports[imports["yoy_pct_change_imports"] >= 0]
    negative_changes = imports[imports["yoy_pct_change_imports"] < 0]

    # Create figure with two bar traces
    fig = go.Figure()

    # Positive values bar trace
    fig.add_trace(
        go.Bar(
            x=positive_changes["date"],
            y=positive_changes["yoy_pct_change_imports"],
            name="Positive Change",
            marker=dict(color="blue"),
            hoverinfo="text",
            text=positive_changes.apply(
                lambda row: f"Product: {row['hs4']}<br>YoY % Change: {row['yoy_pct_change_imports']:.2f}",
                axis=1,
            ),
        )
    )

    # Negative values bar trace
    fig.add_trace(
        go.Bar(
            x=negative_changes["date"],
            y=negative_changes["yoy_pct_change_imports"],
            name="Negative Change",
            marker=dict(color="red"),
            hoverinfo="text",
            text=negative_changes.apply(
                lambda row: f"Product: {row['hs4']}<br>YoY % Change: {row['yoy_pct_change_imports']:.2f}",
                axis=1,
            ),
        )
    )

    # Set up layout with range slider, axis labels, and zero line
    fig.update_layout(
        title="Product Import Price YoY % Change by Trimester",
        xaxis_title="Date",
        yaxis_title="YoY % Change in Import Price",
        barmode="relative",  # Maintain relative stacking for clarity
        xaxis=dict(rangeslider=dict(visible=True), type="date"),
        yaxis=dict(
            automargin=True,
            zeroline=True,  # Draw a line at y=0
            zerolinewidth=2,
            zerolinecolor="black",
        ),
        legend_title_text="Change Type",
    )

    # Generate HTML div for embedding
    div = fig.to_html(full_html=False, include_plotlyjs=True, div_id="price_chart")

    return div
