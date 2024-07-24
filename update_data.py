from scraper import get_hts_dataframe
from generate_plate_data import generate_plate_data
from generate_hts_macronutrients_data import generate_net_macronutrients_data


def update_data():
    raw_import, raw_export = get_hts_dataframe()
    generate_plate_data(raw_import)
    generate_net_macronutrients_data(raw_import, raw_export)


if __name__ == '__main__':
    update_data()
