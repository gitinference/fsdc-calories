from pathlib import Path

import pandas as pd

from jp_imports.data_process import DataProcess

from utils.converter_utils import ConverterUtils


def generate_net_macronutrients_data(
    import_data: pd.DataFrame, export_data: pd.DataFrame
) -> pd.DataFrame:
    # Separate dataframe
    labels = import_data[["year", "trimester"]]

    # Add year-trimester section for labeling
    labels["period"] = (
        labels["year"].apply(lambda x: "Y" + str(x)[-2:]) + labels["trimester"]
    )

    # Drop from main dataframe
    data_section_import = import_data.drop(columns=["year", "trimester"])
    data_section_export = export_data.drop(columns=["year", "trimester"])

    net_dataframe = data_section_import - data_section_export
    net_dataframe = pd.concat([labels, net_dataframe], axis=1)
    return net_dataframe


def process_hts_data() -> pd.DataFrame:
    # Create ConverterUtils
    cur_dir = Path(__file__).parent.resolve()
    reference_file_path = str(cur_dir / "data" / "schedule_b_reference.xlsx")
    utils = ConverterUtils(reference_file_path)

    # Get Import data
    time = "qrt"
    types = "hs"
    df: pd.DataFrame = (
        DataProcess("data/")
        .process_int_org(time, types, agr=True)
        .collect()
        .to_pandas()
    )
    df = df[["hs", "year", "qrt", "imports_qty"]]

    # Calculate total macronutrients for each valid code
    valid_codes: pd.Series = df["hs"].unique().tolist()
    all_codes_data: dict = utils.get_schedule_b_macronutrient_data_list(valid_codes)

    # Create a DataFrame to hold macronutrient multipliers for each code
    macronutrient_df = pd.DataFrame(all_codes_data).T
    macronutrient_df.index.name = "hs"  # Set index name to match the 'hs' column in d

    # Merge the original DataFrame with the macronutrient DataFrame
    df = df.merge(macronutrient_df, on="hs", how="left", suffixes=("", "_mult"))

    # Calculate the total macronutrients
    for macronutrient in macronutrient_df.columns:
        df[macronutrient] = df["imports_qty"] * df[macronutrient].fillna(0)

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
