from scraper import download_latest_hts
from generate_plate_data import generate_plate_data
from charts import update_plate_charts


def update_data():
    download_latest_hts()
    generate_plate_data()
    update_plate_charts()


if __name__ == '__main__':
    update_data()
