import pandas as pd
from jp_imports.data_process import DataProcess
from utils.converter_utils import ConverterUtils


def proccess_price_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Get i/e price data
    df: pd.DataFrame = DataProcess("data/").process_price().collect().to_pandas()

    # Convert month to trimester
    df["trimester"] = ((df["month"] - 1) // 3) + 1

    # Separate data for imports and exports
    imports = df[["hs4", "year", "trimester", "price_imports", "imports_qty"]]
    exports = df[["hs4", "year", "trimester", "price_exports", "exports_qty"]]

    # Drop rows that are not agricultural
    imports = imports[imports.hs4.isin(ConverterUtils.get_agriculture_codes())]
    exports = exports[exports.hs4.isin(ConverterUtils.get_agriculture_codes())]

    # Calculate total spent
    imports["total_spent_imports"] = imports["price_imports"] * imports["imports_qty"]
    exports["total_spent_exports"] = exports["price_exports"] * exports["exports_qty"]

    # Group by hs4, year, trimester and calculate mean prices
    imports = (
        imports.groupby(by=["hs4", "year", "trimester"])
        .agg({"total_spent_imports": "sum", "price_imports": "mean"})
        .reset_index()
    )

    exports = (
        exports.groupby(by=["hs4", "year", "trimester"])
        .agg({"total_spent_exports": "sum", "price_exports": "mean"})
        .reset_index()
    )

    # Function to calculate rolling average and YoY change for each trimester
    def calculate_rolling_yoy(data, price_col, rolling_col_name, yoy_col_name):
        # Initialize the columns for rolling average and YoY percentage change
        data[rolling_col_name] = None
        data[yoy_col_name] = None

        # Apply rolling average for each trimester separately
        for trimester in [2, 3, 4]:
            trimester_data = data[data["trimester"] == trimester].copy()
            # Calculate rolling average with a 3-trimester window
            trimester_data[rolling_col_name] = trimester_data.groupby("hs4")[
                price_col
            ].transform(lambda x: x.rolling(window=3, min_periods=1).mean())
            # Shift by 4 trimesters to get the previous year's rolling average
            trimester_data[f"{yoy_col_name}_last_year"] = trimester_data.groupby("hs4")[
                rolling_col_name
            ].shift(4)
            # Calculate YoY percentage change
            trimester_data[yoy_col_name] = (
                (
                    trimester_data[rolling_col_name]
                    - trimester_data[f"{yoy_col_name}_last_year"]
                )
                / trimester_data[f"{yoy_col_name}_last_year"]
            ) * 100
            # Update the main DataFrame with the trimester data
            data.update(trimester_data[[rolling_col_name, yoy_col_name]])

    # Calculate rolling average and YoY change for imports and exports
    calculate_rolling_yoy(
        imports, "price_imports", "rolling_avg_price_imports", "yoy_pct_change_imports"
    )
    calculate_rolling_yoy(
        exports, "price_exports", "rolling_avg_price_exports", "yoy_pct_change_exports"
    )

    # Filter to keep only Trimesters 2, 3, and 4 for the final output
    imports = imports[imports["trimester"].isin([2, 3, 4])]
    exports = exports[exports["trimester"].isin([2, 3, 4])]

    return imports, exports


def save_top_ranking_products(n: int = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    imports, exports = proccess_price_data()

    if n:
        imports = imports.head(n)
        exports = exports.head(n)

    # Save results for debugging purposes
    imports.to_csv("data/prices/yearly_average_price_imports.csv", index=False)
    exports.to_csv("data/prices/yearly_average_price_exports.csv", index=False)

    return imports, exports


if __name__ == "__main__":
    save_top_ranking_products()
