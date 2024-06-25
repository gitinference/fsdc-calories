import pandas as pd
from utils.converter_utils import ConverterUtils
from utils.constants import Constants
import json


def hts_processor():
    print("Processing HTS data...")

    hts_data = pd.read_csv('latest_hts.csv')

    # Cleans HTS code to n figures, removes apostrophe at start of code (ex. clean('010287, 4) => 0102)
    def clean_hts_value(hts_value, figures=4):
        return int(hts_value[1:figures + 1])

    hts_data["HTS"] = hts_data["HTS"].apply(clean_hts_value)

    utils = ConverterUtils('schedule_b_reference.xlsx')
    code_to_category = utils.schedule_b_to_category()

    nutrient_distribution_yearly = {}

    for year in range(2002, 2025):
        print("Processing year {}".format(year))
        plate_distribution = {cat: 0 for cat in Constants.get_food_categories()}
        data_current_year = hts_data[hts_data["year"] == year]
        for index, row in data_current_year.iterrows():
            if row["HTS"] in code_to_category:
                plate_distribution[code_to_category[row['HTS']]] += 1

        # BANDAID: MOVE ICECREAM COUNT TO OTHER
        plate_distribution["other"] += plate_distribution["ice_cream"]
        plate_distribution.pop("ice_cream")

        nutrient_distribution_yearly[year] = plate_distribution

    with open('nutrition_data/nutrient_distribution_yearly.json', 'w') as fp:
        json.dump(nutrient_distribution_yearly, fp)

    print('Done, extracted data is available in nutrition_data/plate_distribution.json')


if __name__ == '__main__':
    hts_processor()
