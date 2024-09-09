from pathlib import Path

import pandas as pd
from jp_imports import data_process

from utils.converter_utils import ConverterUtils, get_macronutrients


def process_hts_data() -> pd.DataFrame:
    CUR_DIR = Path(__file__).parent.resolve()
    SAVING_DIR = str(CUR_DIR / "data") + "/"
    df = data_process.DataProcess(saving_dir=SAVING_DIR, instance="jp_instetute").process_int_jp(time="monthly", types="total")
    print(df.head())
    pass
    # # Group rows by HTS, year and trimester and aggregate quantities, unit does not matter since all units are KG
    # df = filtered_codes.copy()
    # df['trimester'] = df['month'].apply(month_to_trimester)
    # df = df.drop(df[df["year"] == 2002].index)  # Optional, not sure
    # trimester_data = df.groupby(['HTS', 'year', 'trimester']).agg({'qty_1_conv': 'sum'}).reset_index()

    # # Calculate total macronutrients for each valid code
    # all_codes_data = utils.get_schedule_b_macronutrient_data_list(valid_codes)
    # for code in all_codes_data:

    #     # Get macronutrient data for current code
    #     cur_code_data = all_codes_data[code]

    #     for macronutrient in cur_code_data:
    #         # macronutrient col = quantity * macronutrient amount per unit for current HTS code
    #         trimester_data.loc[trimester_data["HTS"] == code, macronutrient] = (trimester_data["qty_1_conv"] *
    #                                                                             cur_code_data[macronutrient])

    # # Finish aggregating all macronutrient data for each quarter
    # trimester_data = trimester_data.groupby(['year', 'trimester']).agg({
    #     macronutrient: "sum" for macronutrient in get_macronutrients()
    # }).reset_index()

    # return trimester_data


if __name__ == '__main__':
    print(process_hts_data())
