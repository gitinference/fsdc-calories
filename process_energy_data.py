import ssl
import urllib.request

import chardet
import numpy as np
import pandas as pd

ssl._create_default_https_context = ssl._create_unverified_context

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


def main():
    fetch_energy_data()


def get_energy_category_map():
    return agricultural_categories_dict


def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        detector = chardet.universaldetector.UniversalDetector()
        for line in file:
            detector.feed(line)
            if detector.done:
                break
        detector.close()
    return detector.result['encoding']


def fetch_energy_data():
    # Fetch energy indicators from LUMA dataset
    url = ('https://indicadores.pr/dataset/49746389-12ce-48f6-b578-65f6dc46f53f/resource/8025f821-45c1-4c6a-b2f4'
           '-8d641cc03df1/download/aee-meta-ultimo.csv')

    f, res = urllib.request.urlretrieve(url)
    encoding = detect_encoding(f)

    # Read CSV into dataframe
    df = pd.read_csv(url, encoding=encoding)
    df = df.drop('Comentarios', axis=1)

    def parse_date(row: pd.Series):
        val = row.split('/')
        val = [num.zfill(2) for num in val]  # Add left zeros up to 2 characters

        # Convert from MM/DD/YYYY to ISO standard YYYY-MM-DD
        val[0], val[1], val[2] = val[2], val[0], val[1]
        val = "-".join(val)
        return val

    df["Mes"] = df["Mes"].map(parse_date)
    df["Mes"] = pd.to_datetime(df["Mes"])

    df.rename(columns={"Mes": "Date"}, inplace=True)

    # Clean column names to remove random spaces with rstrip and lstrip
    df.rename(columns={
        colname: colname.rstrip().lstrip() for colname in df.columns.values
    }, inplace=True)

    # Clean values in each column to allow float casting
    def clean_value(val: any):
        val = str(val)
        val = val.replace(",", "")

        try:
            val = float(val)
        except ValueError:
            val = np.nan

        return val

    for colname in df.columns[1:]:
        df[colname] = df[colname].map(clean_value)

    return df


if __name__ == '__main__':
    main()
