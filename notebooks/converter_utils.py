import json
from typing import List, Set

import numpy as np
import pandas as pd


class ConverterUtils:

    def __init__(self, filename: str):
        self.data = pd.read_excel(filename, dtype="object")
        self.data = self.data.replace(".", 0)  # Replace "." with NaN value
        # Drop all rows that contain NaN values after first 2 columns
        self.data = self.data.dropna(how="any", subset=self.data.columns[2:])
        self.data = self.data[self.data.columns[:-7]]
        self.data["schedule_b"] = self.data["schedule_b"].astype(str)
        self.data = self.data.dropna()
        self.data.loc[:, "schedule_b"] = self.data["schedule_b"].apply(
            lambda x: x.ljust(10, "0")
        )

    # Returns a dictionary of schedule_b -> my_plate_category
    def schedule_b_to_category(self):
        from utils.constants import Constants

        schedule_b_data = pd.DataFrame(self.data)

        code_to_category = dict()
        row: pd.Series
        for index, row in schedule_b_data.iterrows():
            try:
                current_category = row[row == 1].index[0]
            except:
                code_to_category[row["schedule_b"]] = "other"
                continue
            if current_category in Constants.get_food_categories():
                code_to_category[row["schedule_b"]] = current_category

        return code_to_category

    def get_valid_schedule_b_codes(self):
        return [code for code in self.data["schedule_b"].to_list()]

    def get_schedule_b_macronutrient_data(self, schedule_b_code: str):
        padded_code = schedule_b_code[:4].ljust(10, "0")
        index = self.data["schedule_b"] == padded_code
        data = self.data[index]

        if data.empty:
            return {i: 0 for i in self.get_macronutrients()}

        return {i: float(data[i].values[0]) for i in self.get_macronutrients()}

    def get_schedule_b_macronutrient_data_list(self, schedule_b_code_list: list[str]):
        # Returns a dictionary with each code and the associated macronutrient data
        return {
            code: self.get_schedule_b_macronutrient_data(code)
            for code in schedule_b_code_list
        }

    @staticmethod
    def get_macronutrients():
        return [
            "calories",
            "total_fat_g",
            "protein_g",
            "saturated_fat_g",
            "cholesterol_mg",
            "sodium_mg",
            "carbohydrate_g",
            "fiber_g",
            "sugar_g",
            "vitamin_d_iu",
            "calcium_mg",
            "potassium_mg",
            "iron_mg",
        ]

    @staticmethod
    def get_agriculture_codes() -> Set[str]:
        with open("data/external/code_agr.json") as f:
            d: dict = dict(json.load(f))
        agr_codes: List[str] = list(d.values())
        agr_codes = [str(x).zfill(4) for x in agr_codes]
        return set(agr_codes)


def main():
    pass


if __name__ == "__main__":
    main()
