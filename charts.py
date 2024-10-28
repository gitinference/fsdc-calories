from pathlib import Path

import pandas as pd
import plotly.express as px
from process_energy_data import fetch_energy_data, get_energy_category_map
from process_fiscal_data import get_country_list, get_net_value_country
from process_price_data import save_top_ranking_products


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


def get_product_price_ranking_timeseries_div(n: int = None):
    if not n:
        n = 100

    # Fetch imports and exports data for the given year
    imports, exports = save_top_ranking_products(n)

    # Convert year to datetime if it's not already in the right format
    if imports["year"].dtype != "datetime64[ns]":
        imports["year"] = pd.to_datetime(imports["year"], format="%Y")

    # Sort data by price_imports to order the hs4 traces by price amount
    imports.sort_values(by="price_imports", inplace=True, ascending=False)

    # Check for and remove any NaN or invalid values
    imports.dropna(subset=["price_imports", "year"], inplace=True)

    # Create bar chart with hs4 ordered by price_imports
    fig = px.bar(
        imports,
        x="year",
        y="price_imports",
        color="hs4",  # This will automatically order the traces by price_imports
        barmode="stack",  # You can switch to 'stack' if needed
        hover_data={"hs4": True, "price_imports": ":,.2f"},  # Adding hover info
        labels={
            "price_imports": "Import Price (USD)",
            "year": "Year",
            "hs4": "Product Code",
        },
        title="Product Price Ranking Time Series",
    )

    # Set title and improve chart layout for better interaction
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Import Price (in USD)",
        xaxis=dict(rangeslider=dict(visible=True), type="date"),  # Enables range slider
        yaxis=dict(
            automargin=True,  # Allows for automatic margins
        ),
        legend_title_text="Product Code (hs4)",
    )

    # Generate the HTML div for embedding
    div = fig.to_html(full_html=False, include_plotlyjs=True, div_id="price_chart")

    return div


if __name__ == "__main__":
    main()
    get_product_price_ranking_timeseries_div(2024)
