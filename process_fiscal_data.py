from pathlib import Path
from typing import List, Any

import pandas as pd

# Read fiscal data pickle file
CUR_DIR = Path(__file__).parent.resolve()
PICKLE_PATH = CUR_DIR / "data" / "jp_gdp_data" / "fiscal.pkl"
DATAFRAME = pd.read_pickle(PICKLE_PATH)


def get_net_value_country(country: str) -> list[list[Any]]:
    # If country does not exist in data, raise KeyError
    if country not in get_country_list():
        raise KeyError(f'Country {country} is not a valid country')

    # Get selected country data
    selected_country_data = DATAFRAME[DATAFRAME["country"] == country]

    # Format into a list: [[Year1, Net Value1], [Year2, Net Value2], ...]
    selected_country_data = [
        [str(row["Fiscal Year"]), row["net_value"]] for _, row in selected_country_data.iterrows()
    ]

    return selected_country_data


def get_country_list() -> list[str]:
    return DATAFRAME["country"].unique().tolist()
