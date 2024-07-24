import pandas as pd
from pathlib import Path
from utils.converter_utils import ConverterUtils, get_macronutrients


def generate_net_macronutrients_data(import_data: pd.DataFrame, export_data: pd.DataFrame) -> pd.DataFrame:
    # Separate dataframe
    labels = import_data[["year", "trimester"]]

    # Add year-trimester section for labeling
    labels["period"] = labels["year"].apply(lambda x: 'Y' + str(x)[-2:]) + labels["trimester"]

    # Drop from main dataframe
    data_section_import = import_data.drop(columns=["year", "trimester"])
    data_section_export = export_data.drop(columns=["year", "trimester"])

    net_dataframe = data_section_import - data_section_export
    net_dataframe = pd.concat([labels, net_dataframe], axis=1)
    return net_dataframe


def generate_hts_macronutrients_data(hts_data: pd.DataFrame) -> pd.DataFrame:
    # Create ConverterUtils
    cur_dir = Path(__file__).parent.resolve()
    reference_file_path = str(cur_dir / "data" / "schedule_b_reference.xlsx")
    utils = ConverterUtils(reference_file_path)

    # Get list of valid schedule_b codes (codes for which macronutrient data exists)
    valid_codes = utils.get_valid_schedule_b_codes()

    # Cleans HTS code to n figures, removes apostrophe at start of code (ex. clean("'01028796", 4) => 0102)
    def clean_hts_value(hts_value, figures=4):
        return int(hts_value[1:figures + 1])

    hts_data["HTS"] = hts_data["HTS"].apply(clean_hts_value)

    # Filter rows based on valid schedule_b codes
    filtered_codes = hts_data[hts_data["HTS"].isin(valid_codes)]

    # Drop rows with no value in unit_1 (invalid unit)
    invalid_rows = filtered_codes[filtered_codes["unit_1"].apply(lambda x: not isinstance(x, str))]
    filtered_codes = filtered_codes.drop(invalid_rows.index)

    # Set mode if reading import or export data
    mode = "import" if hts_data.head(1)["import_export"].values[0] == "i" else "export"
    print("Current mode: ", mode)

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

    # function to map months to trimesters
    def month_to_trimester(month):
        if month in [1, 2, 3]:
            return 'Q1'
        elif month in [4, 5, 6]:
            return 'Q2'
        elif month in [7, 8, 9]:
            return 'Q3'
        elif month in [10, 11, 12]:
            return 'Q4'
        else:
            return None

    # Group rows by HTS, year and trimester and aggregate quantities, unit does not matter since all units are KG
    df = filtered_codes.copy()
    df['trimester'] = df['month'].apply(month_to_trimester)
    df = df.drop(df[df["year"] == 2002].index)  # Optional, not sure
    trimester_data = df.groupby(['HTS', 'year', 'trimester']).agg({'qty_1_conv': 'sum'}).reset_index()

    # Calculate total macronutrients for each valid code
    all_codes_data = utils.get_schedule_b_macronutrient_data_list(valid_codes)
    for code in all_codes_data:

        # Get macronutrient data for current code
        cur_code_data = all_codes_data[code]

        for macronutrient in cur_code_data:
            # macronutrient col = quantity * macronutrient amount per unit for current HTS code
            trimester_data.loc[trimester_data["HTS"] == code, macronutrient] = (trimester_data["qty_1_conv"] *
                                                                                cur_code_data[macronutrient])

    # Finish aggregating all macronutrient data for each quarter
    trimester_data = trimester_data.groupby(['year', 'trimester']).agg({
        macronutrient: "sum" for macronutrient in get_macronutrients()
    }).reset_index()

    return trimester_data


if __name__ == '__main__':
    from scraper import get_hts_dataframe

    raw_import, raw_export = get_hts_dataframe()
    processed_import = generate_hts_macronutrients_data(raw_import)
    processed_export = generate_hts_macronutrients_data(raw_export)

    net_data = generate_net_macronutrients_data(processed_import, processed_export)
