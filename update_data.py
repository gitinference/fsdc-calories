from scraper import download_latest_hts_imports, download_latest_hts_exports
from generate_plate_data import generate_plate_data


def update_data():
    download_latest_hts_imports()
    download_latest_hts_exports()
    generate_plate_data()


if __name__ == '__main__':
    update_data()
