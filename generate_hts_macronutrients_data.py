import pandas as pd
import matplotlib.pyplot as plt
from utils.converter_utils import ConverterUtils, get_macronutrients


def main():
    df = pd.read_csv("data/macronutrients/hts_macronutrients_data.csv")

    # min_year, max_year = df["year"].min(), df["year"].max()
    # yearly_calories = {
    #     year: df[df["year"] == year]["calories"].sum() for year in range(min_year, max_year + 1)
    # }

    print(df.groupby("year").head())


def generate_hts_macronutrients_data():
    hts_data_path = 'data/raw_hts/latest_hts.csv.csv'
    hts_data = pd.read_csv(hts_data_path)

    # Cleans HTS code to n figures, removes apostrophe at start of code (ex. clean('010287, 4) => 0102)
    def clean_hts_value(hts_value, figures=4):
        return int(hts_value[1:figures + 1])

    hts_data["HTS"] = hts_data["HTS"].apply(clean_hts_value)

    # Filter rows based on desired schedule_b codes
    utils = ConverterUtils('data/schedule_b_reference.xlsx')
    codes = utils.get_schedule_b_codes()
    filtered_codes = hts_data[hts_data["HTS"].isin(codes)]

    # Drop rows with no value in unit_1 (invalid)
    invalid_rows = filtered_codes[filtered_codes["unit_1"].apply(lambda x: not isinstance(x, str))]
    filtered_codes = filtered_codes.drop(invalid_rows.index)

    unit_to_kg_factor = {
        'L': 1,
        'T': 907.185,
        'KG': 1,
        'PFL': 1,
        'M3': 1,
        'KTS': 1,
        'DOZ': 1,
        'X': 1
    }

    # Generate new dataframe with code, year, unit and quantity
    filtered_codes = filtered_codes[["HTS", "year", "month", "unit_1", "qty_1"]]

    # Normalize all units to use uppercase
    filtered_codes["unit_1"] = filtered_codes["unit_1"].apply(lambda val: val.upper())

    # Add new columns of conversion factor quantity and converted to KG
    filtered_codes["qty_1_conv"] = filtered_codes["unit_1"].apply(lambda x: unit_to_kg_factor[x]) * filtered_codes[
        "qty_1"]

    # Add get total macronutrients for each product
    print("Calculating total macronutrients...")

    def get_total_macronutrients(row, macronutrient):
        return utils.get_schedule_b_macronutrient_data(row["HTS"])[macronutrient] * row["qty_1_conv"]

    for mn in get_macronutrients():
        print(mn)
        filtered_codes[mn] = filtered_codes.apply(lambda x: get_total_macronutrients(x, mn), axis=1)

    # Clean up empty cells with 0
    filtered_codes.fillna(0, inplace=True)

    macronutrients_data_out = 'data/macronutrients/hts_macronutrients_data.csv'
    filtered_codes.to_csv(macronutrients_data_out, index=False)

    print(f"Done, data written to {macronutrients_data_out}")


if __name__ == '__main__':
    generate_hts_macronutrients_data()
