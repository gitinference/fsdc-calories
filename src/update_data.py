import os

import pandas as pd
import requests

from process_energy_data import fetch_energy_data
from process_hts_data import process_hts_data
from process_plate_data import process_plate_data
from process_price_data import save_top_ranking_products


def main():
    update_data()


def update_data():

    # Check for saving directories before calling dataframe save
    DIRS = ["macronutrients", "plate", "prices", "energy"]
    for dir in DIRS:
        if not os.path.exists(f"data/{dir}"):
            os.makedirs(f"data/{dir}")

    # Pull macronutrient data from API and process
    response = requests.get(
        "https://api.econlabs.net/data/trade/org/?agg=qrt&types=hts&agr=true"
    )
    df = pd.DataFrame(response.json())
    df = df[["hts_code", "year", "qrt", "qty_imports", "qty_exports"]]
    df.to_csv("data/macronutrients/raw_macro.csv")
    process_hts_data()

    # Pull plate data
    response = requests.get(
        "https://api.econlabs.net/data/trade/org/?agg=monthly&types=hts&agr=true"
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

    # Pull energy data
    df = fetch_energy_data()
    df.to_csv("data/energy/processed_energy_data.csv")


if __name__ == "__main__":
    main()
