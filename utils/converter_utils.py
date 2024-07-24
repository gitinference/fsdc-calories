import pandas as pd
import numpy as np
from utils.constants import Constants


def get_macronutrients():
    return [
        'calories',
        'total_fat_g',
        'protein_g',
        'saturated_fat_g',
        'cholesterol_mg',
        'sodium_mg',
        'carbohydrate_g',
        'fiber_g',
        'sugar_g',
        'vitamin_d_iu',
        'calcium_mg',
        'potassium_mg',
        'iron_mg'
    ]


class ConverterUtils:

    def __init__(self, filename: str):
        self.data = pd.read_excel(filename)
        self.data = self.data.replace('.', np.nan)  # Replace "." with NaN value
        # Drop all rows that contain NaN values after first 2 columns
        self.data = self.data.dropna(how='all', subset=self.data.columns[2:])
        self.data = self.data[self.data.columns[:-7]]

    # Returns a dictionary of schedule_b -> my_plate_category
    def schedule_b_to_category(self):

        schedule_b_data = pd.DataFrame(self.data)

        code_to_category = dict()
        row: pd.Series
        for index, row in schedule_b_data.iterrows():
            current_category = row[row == 1].index[0]
            if current_category in Constants.get_food_categories():
                code_to_category[row["schedule_b"]] = current_category

        return code_to_category

    def get_valid_schedule_b_codes(self):
        return [int(code) for code in self.data["schedule_b"].to_list()]

    def get_schedule_b_macronutrient_data(self, schedule_b_code: int):
        index = self.data["schedule_b"] == schedule_b_code
        data = self.data[index]

        return {
            i: float(data[i].values[0]) for i in get_macronutrients()
        }

    def get_schedule_b_macronutrient_data_list(self, schedule_b_code_list: list[int]):
        # Returns a dictionary with each code and the associated macronutrient data
        return {
            code: self.get_schedule_b_macronutrient_data(code) for code in schedule_b_code_list
        }


def main():
    utils = ConverterUtils('../data/schedule_b_reference.xlsx')
    # print(utils.get_schedule_b_macronutrient_data(701))
    print(utils.get_schedule_b_macronutrient_data_list([307, 2209]))


if __name__ == '__main__':
    main()
