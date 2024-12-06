from pathlib import Path

import pandas as pd

from utils.converter_utils import ConverterUtils


def process_hts_data() -> pd.DataFrame:
    # Create ConverterUtils
    cur_dir = Path(__file__).parent.resolve()
    reference_file_path = str(cur_dir / "data" / "schedule_b_reference.xlsx")
    utils = ConverterUtils(reference_file_path)
    
    df = pd.read_csv("data/macronutrients/raw_macro.csv")
    df["hts_code"] = df["hts_code"].astype(str)

    # Drop rice
    def is_rice_hs(row):
        return str(row["hts_code"]).startswith("1006")

    rice = df[df.apply(is_rice_hs, axis=1)]
    df = df.drop(rice.index)

    # Get net qty (Import - Export)
    df["net_qty"] = df["qty_imports"] - df["qty_exports"]

    # Calculate total macronutrients for each valid code
    valid_codes: pd.Series = utils.get_valid_schedule_b_codes()
    all_codes_data: dict = utils.get_schedule_b_macronutrient_data_list(valid_codes)

    # Create a DataFrame to hold macronutrient multipliers for each code
    macronutrient_df = pd.DataFrame(all_codes_data).T
    macronutrient_df.index.name = "hts_code"  # Set index name to match the 'hs' column in df
    
    # Convert each multiplier to kilograms
    for m in ConverterUtils.get_macronutrients():
        if "mg" in m:
            macronutrient_df[m] = macronutrient_df[m] / 1000000
        elif "g" in m:
            macronutrient_df[m] = macronutrient_df[m] / 1000
        else:
            print(f"Unit for {m} not found. Assuming kilograms...")

    # Create a new column with the first 4 characters of the index in macronutrient_df
    macronutrient_df["hs4"] = macronutrient_df.index.str[:4]

    # Create a new column with the first 4 characters of 'hs' in df
    df["hs4"] = df["hts_code"].str[:4]
    
    # Group by hs4
    df = df.groupby(by=["hs4", "year", "qrt"]).agg("sum").reset_index()
    
    # FIX: Drop Otas and Rice
    df = df[(df["hs4"] != "1004") & (df["hs4"] != "1006")]

    # Perform the merge using the new column
    df = df.merge(macronutrient_df, on="hs4", how="left", suffixes=("", "_mult"), validate="many_to_one")

    # Calculate the total macronutrients
    macronutrient_list = ConverterUtils.get_macronutrients()
    
    for m in macronutrient_list:
        df[m] = df["net_qty"] * df[m].fillna(0.00).astype("Float64")

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
            raise ValueError(f"Quarter must be between 1 and 4, got {quarter}")

        # Create the datetime object for the first day of the quarter
        return pd.Timestamp(year=year, month=month, day=1)

    df["date"] = df["date"] = df.apply(year_quarter_to_datetime, axis=1)
    grouped_df = df.groupby("date").agg("sum").reset_index()
    final_columns = ["date"] + utils.get_macronutrients()
    
    grouped_df[final_columns].to_csv("data/macronutrients/net_macronutrients.csv")
    return grouped_df[final_columns]


if __name__ == "__main__":
    processed = process_hts_data()
    processed.to_csv("data/macronutrients/net_macronutrients.csv", index=False)
