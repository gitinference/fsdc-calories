from scraper import download_latest_hts
from hts_processor import hts_processor
from charts import update_plate_charts

def update_data():
    download_latest_hts()
    hts_processor()
    update_plate_charts()


if __name__ == '__main__':
    update_data()
