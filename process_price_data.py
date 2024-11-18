from datetime import datetime
import os
import pandas as pd
import requests
from utils.converter_utils import ConverterUtils


def proccess_price_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Get i/e price data
    if not os.path.exists("data/prices/raw.csv"):
        res = requests.get("https://api.econlabs.net/data/trade/moving")
        if not res:
            raise Exception("Could not get data from econlabs.")
        df = pd.DataFrame(res.json())
    else:
        df: pd.DataFrame = pd.read_csv("data/prices/raw.csv")
    
    df["hs4"] = df["hs4"].astype(str)
    df["date"] = pd.to_datetime(df["date"])
    
    # Separate data for imports and exports
    imports = df[["hs4", "date", "prev_year_imports"]]
    exports = df[["hs4", "date", "prev_year_exports"]]

    # Drop rows that are not agricultural
    imports = imports[imports.hs4.isin(ConverterUtils.get_agriculture_codes())]
    exports = exports[exports.hs4.isin(ConverterUtils.get_agriculture_codes())]

    return imports, exports


def save_top_ranking_products() -> tuple[pd.DataFrame, pd.DataFrame]:
    imports, exports = proccess_price_data()

    # Get current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Calculate previous month and handle year wrap
    if current_month == 1:
        previous_month = 12
        previous_year = current_year - 1
    else:
        previous_month = current_month - 1
        previous_year = current_year
    
    # Handle case where latest available data is older than last month
    max_month_available = imports["date"].max().month
    previous_month = min(max_month_available, previous_month)

    month_year_filter_imports = (imports['date'].dt.month == previous_month) & (imports['date'].dt.year == previous_year)
    month_year_filter_exports = (exports['date'].dt.month == previous_month) & (exports['date'].dt.year == previous_year)

    imports = imports[month_year_filter_imports]
    exports = exports[month_year_filter_exports]

    imports = imports.sort_values(by="prev_year_imports", ascending=False)
    exports = exports.sort_values(by="prev_year_exports", ascending=False)
    
    rename_map = {"prev_year_imports": "pct_change_moving_price", "prev_year_exports": "pct_change_moving_price"}
    
    imports = imports.rename(columns=rename_map)
    exports = exports.rename(columns=rename_map)

    # Save results for debugging purposes
    imports.to_csv("data/prices/price_imports.csv", index=False)
    exports.to_csv("data/prices/price_exports.csv", index=False)

    return imports, exports


if __name__ == "__main__":
    save_top_ranking_products()
