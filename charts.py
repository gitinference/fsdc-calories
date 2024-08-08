import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go

from process_energy_data import fetch_energy_data


def main():
    get_energy_timeseries_chart_div()


def get_energy_timeseries_chart_div(category: str = "agricultural_consumption_mkwh"):
    df = fetch_energy_data()

    agricultural_categories_dict = {
        "agricultural_consumption_mkwh": "Consumo agrícola (mkWh)",
        "active_agricultural_customers": "Clientes Activos-clase agrícola",
        "basic_income_agricultural_m$": "Ingreso básico-clase agrícola (M$)",
        "provisional_tariff_income_agricultural_m$": "Ingreso tarifa provisional-clase agrícola (M$)",
        "fuel_adjustment_income_agricultural_m$": "Ingresos Ajuste Combustible-clase agrícola (M$)",
        "purchased_energy_income_agricultural_m$": "Ingresos energía comprada-clase agrícola (M$)",
        "celi_income_agricultural_m$": "Ingresos CELI-clase agrícola (M$)",
        "hh_subsidy_income_agricultural_m$": "Ingresos Subsidio-HH-clase agrícola (M$)",
        "nhh_subsidy_income_agricultural_m$": "Ingresos Subsidio-NHH-clase agrícola (M$)",
        "provisional_tariff_return_tup_agricultural_m$": "Devolución tarifa provisional  TUP-clase agrícola (M$)",
        "total_income_agricultural_m$": "Ingreso Total-clase agrícola (M$)",
        "avg_basic_income_cost_agricultural_ckwh": "Costo promedio ingreso básico-clase agrícola (¢kWh)",
        "avg_fuel_income_cost_agricultural_ckwh": "Costo promedio ingreso combustible-clase agrícola (¢kWh)",
        "avg_purchased_energy_cost_agricultural_ckwh": "Costo promedio ingreso energía comprada-clase agrícola (¢kWh)",
        "avg_celi_income_cost_agricultural_ckwh": "Costo promedio ingreso CELI-clase agrícola (¢kWh)",
        "avg_hh_subsidy_income_cost_agricultural_ckwh": "Costo promedio ingreso Subsidio-HH-clase agrícola (¢kWh)",
        "avg_nhh_subsidy_income_cost_agricultural_ckwh": "Costo promedio ingreso Subsidio-NHH-clase agrícola (¢kWh)"
    }

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

    div = fig.to_html(full_html=False, include_plotlyjs='cdn')

    return div


if __name__ == '__main__':
    main()
