from process_hts_data import generate_net_macronutrients_data, process_hts_data
from process_plate_data import process_plate_data
from scraper import get_hts_dataframe
from pathlib import Path


def update_data():
    raw_import, raw_export = get_hts_dataframe()
    process_plate_data(raw_import)
    processed_import = process_hts_data(raw_import)
    processed_export = process_hts_data(raw_export)

    net_data = generate_net_macronutrients_data(processed_import, processed_export)
    out_dir = str(Path(__file__).parent.absolute() / "data" / "macronutrients" / "net_macronutrients.csv")
    net_data.to_csv(out_dir)


if __name__ == '__main__':
    update_data()
