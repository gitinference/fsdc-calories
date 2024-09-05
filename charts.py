import plotly.express as px

from process_energy_data import fetch_energy_data, get_energy_category_map


def main():
    get_energy_timeseries_chart_div()


def get_energy_timeseries_chart_div(category: str = "agricultural_consumption_mkwh"):
    df = fetch_energy_data()

    agricultural_categories_dict = get_energy_category_map()
    selected_category_col_name = agricultural_categories_dict[category]

    # Create figure
    fig = px.line(df, x="Date", y=selected_category_col_name)

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

    div = fig.to_html(full_html=False, include_plotlyjs=True, div_id=f"chart_{category}")

    return div


if __name__ == '__main__':
    main()
