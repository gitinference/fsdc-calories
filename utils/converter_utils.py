import pandas as pd
import numpy as np
from utils.constants import Constants


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


def main():
    utils = ConverterUtils('../schedule_b_reference.xlsx')
    print(utils.schedule_b_to_category())


if __name__ == '__main__':
    main()
