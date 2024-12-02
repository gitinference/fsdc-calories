import os

import pandas as pd
import requests

from process_hts_data import process_hts_data
from process_plate_data import process_plate_data
from process_price_data import save_top_ranking_products


def main():
    update_data()


def update_data():

    # Pull macronutrient data from API and process

    response = requests.get(
        "https://api.econlabs.net/data/trade/org/?time=qrt&types=hts&agr=true&group=false"
    )
    df = pd.DataFrame(response.json())
    df = df[["hts_code", "year", "qrt", "qty_imports", "qty_exports"]]
    df.to_csv("data/macronutrients/raw_macro.csv")
    process_hts_data()

    # Pull plate data

    response = requests.get(
        "https://api.econlabs.net/data/trade/org/?time=monthly&types=hts&agr=true&group=false"
    )
    df = pd.DataFrame(response.json())
    df.to_csv("data/plate/raw_plate.csv")
    process_plate_data()

    # Pull price data

    response = requests.get("https://api.econlabs.net/data/trade/moving")
    if not response:
        raise Exception("Could not get data from econlabs.")
    df = pd.DataFrame(response.json())
    df.to_csv("data/prices/raw_prices.csv")
    save_top_ranking_products()
    
    


if __name__ == "__main__":
    main()
