from pathlib import Path

import pandas as pd

from jp_imports.data_process import DataProcess

from utils.converter_utils import ConverterUtils


def process_hts_data() -> pd.DataFrame:
    # Create ConverterUtils
    cur_dir = Path(__file__).parent.resolve()
    reference_file_path = str(cur_dir / "data" / "schedule_b_reference.xlsx")
    utils = ConverterUtils(reference_file_path)

    # Get net hs4 data
    time = "qrt"
    types = "hs"
    df: pd.DataFrame = (
        DataProcess("data/")
        .process_int_org(time, types, agr=True)
        .collect()
        .to_pandas()
    )
    df = df[["hs", "year", "qrt", "imports_qty", "exports_qty"]]

    # Drop rice
    def is_rice_hs(row):
        return str(row["hs"]).startswith("1006")

    rice = df[df.apply(is_rice_hs, axis=1)]
    df = df.drop(rice.index)

    # Get net qty (Import - Export)
    df["net_qty"] = df["imports_qty"] - df["exports_qty"]

    # Calculate total macronutrients for each valid code
    valid_codes: pd.Series = utils.get_valid_schedule_b_codes()
    all_codes_data: dict = utils.get_schedule_b_macronutrient_data_list(valid_codes)

    # Create a DataFrame to hold macronutrient multipliers for each code
    macronutrient_df = pd.DataFrame(all_codes_data).T
    macronutrient_df.index.name = "hs"  # Set index name to match the 'hs' column in df

    # Create a new column with the first 4 characters of the index in macronutrient_df
    macronutrient_df["hs4"] = macronutrient_df.index.str[:4]

    # Create a new column with the first 4 characters of 'hs' in df
    df["hs4"] = df["hs"].str[:4]

    # Perform the merge using the new column
    df = df.merge(macronutrient_df, on="hs4", how="left", suffixes=("", "_mult"))

    # Calculate the total macronutrients
    macronutrient_list = list(macronutrient_df.columns)[1:]
    for m in macronutrient_list:
        df[m] = df["net_qty"] * df[m].fillna(0.00).astype("Float64")

    # for m in macronutrient_list:
    #     print(df[m][df[m] > 0])

    def year_quarter_to_datetime(row):
        year = row["year"]
        quarter = row["qrt"]
        # Calculate the start date of the quarter
        if quarter == 1:
            month = 1
        elif quarter == 2:
            month = 4
        elif quarter == 3:
            month = 7
        elif quarter == 4:
            month = 10
        else:
            raise ValueError("Quarter must be between 1 and 4")

        # Create the datetime object for the first day of the quarter
        return pd.Timestamp(year=year, month=month, day=1)

    df["date"] = df["date"] = df.apply(year_quarter_to_datetime, axis=1)
    grouped_df = df.groupby("date").agg("sum").reset_index()
    final_columns = ["date"] + utils.get_macronutrients()
    return grouped_df[final_columns]


if __name__ == "__main__":
    processed = process_hts_data()
    processed.to_csv("data/macronutrients/net_macronutrients.csv", index=False)
