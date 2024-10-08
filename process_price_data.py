from pathlib import Path

import pandas as pd

from jp_imports.data_process import DataProcess

from utils.converter_utils import ConverterUtils


def proccess_price_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Get i/e price data
    df: pd.DataFrame = DataProcess("data/").process_price().collect().to_pandas()

    print(df.columns)

    df1 = df[["hs4", "price_imports"]]
    df1 = (
        df1.groupby(by="hs4")
        .agg("sum")
        .sort_values(by="price_imports", ascending=False)
        .reset_index()
    )

    df2 = df[["hs4", "price_exports"]]
    df2 = (
        df2.groupby(by="hs4")
        .agg("sum")
        .sort_values(by="price_exports", ascending=False)
        .reset_index()
    )

    return df1, df2


if __name__ == "__main__":
    df1, df2 = proccess_price_data()
    print(df1, df2)
