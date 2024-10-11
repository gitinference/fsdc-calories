from pathlib import Path

import pandas as pd

from jp_imports.data_process import DataProcess

from utils.converter_utils import ConverterUtils


def proccess_price_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Get i/e price data
    df: pd.DataFrame = DataProcess("data/").process_price().collect().to_pandas()

    imports = df[["hs4", "year", "price_imports", "imports_qty"]]
    exports = df[["hs4", "year", "price_exports", "exports_qty"]]

    imports["total_spent_imports"] = imports["price_imports"] * imports["imports_qty"]
    exports["total_spent_exports"] = exports["price_exports"] * exports["exports_qty"]

    imports = imports[["hs4", "year", "total_spent_imports", "price_imports"]]
    exports = exports[["hs4", "year", "total_spent_exports", "price_exports"]]

    imports = (
        imports.groupby(by=["hs4", "year"])
        .agg({"total_spent_imports": "sum", "price_imports": "mean"})
        .sort_values(by="price_imports", ascending=False)
        .reset_index()
    )

    exports = (
        exports.groupby(by=["hs4", "year"])
        .agg({"total_spent_exports": "sum", "price_exports": "mean"})
        .sort_values(by="price_exports", ascending=False)
        .reset_index()
    )

    return imports, exports


def get_top_ranking_products_by_year(
    year: int, n: int = None
) -> tuple[pd.DataFrame, pd.DataFrame]:

    imports, exports = proccess_price_data()
    imports = imports[imports["year"] == year]
    exports = exports[exports["year"] == year]
    if n:
        imports = imports.head(n)
        exports = exports.head(n)

    return imports, exports


if __name__ == "__main__":
    df1, df2 = get_top_ranking_products_by_year(2024, 10)
    print(df1)
    print(df2)
