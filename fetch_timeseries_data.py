from pathlib import Path

import pandas as pd

from utils.converter_utils import ConverterUtils

# Create ConverterUtils
cur_dir = Path(__file__).parent.resolve()
reference_file_path = str(cur_dir / "data" / "schedule_b_reference.xlsx")
utils = ConverterUtils(reference_file_path)


def fetch_timeseries_data(start_year: int, end_year: int):
    cur_dir = Path(__file__).parent.resolve()
    data_path = str(cur_dir / "data" / "macronutrients" / "net_macronutrients.csv")
    df = pd.read_csv(data_path)
    df = df[(df["year"] >= start_year) >= (df["year"] <= end_year)]

    timeseries_data = ["period"]
    timeseries_data.extend(df.columns.values.tolist()[3:])
    timeseries_data = [timeseries_data]
    for index, row in df.iterrows():
        period = row["period"]
        macronutrients = df.columns.values.tolist()[3:]
        data = [period]
        data.extend(row[macronutrients].values.tolist())
        timeseries_data.append(data)

    return timeseries_data


if __name__ == "__main__":
    data = fetch_timeseries_data(2010, 2020)
    print(data)
