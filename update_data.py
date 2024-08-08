from scraper import get_hts_dataframe
from process_plate_data import process_plate_data
from process_hts_data import generate_net_macronutrients_data, process_hts_data


def update_data():
    raw_import, raw_export = get_hts_dataframe()
    process_plate_data(raw_import)
    processed_import = process_hts_data(raw_import)
    processed_export = process_hts_data(raw_export)

    net_data = generate_net_macronutrients_data(processed_import, processed_export)


if __name__ == '__main__':
    update_data()
