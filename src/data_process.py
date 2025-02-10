from .jp_imports.src.jp_imports.data_process import DataTrade
import polars as pl
import pandas as pd
import os


class DataCal(DataTrade):
    def __init__(
        self, saving_dir: str = "data/", database_url: str = "duckdb:///data.ddb"
    ):
        super().__init__(saving_dir, database_url)

    def gen_calaries(self):
        if not os.path.exists(f"{self.saving_dir}external/nutrition.parquet"):
            self.pull_file(
                url="", filename=f"{self.saving_dir}external/nutrition.parquet"
            )
        nutri_df = pl.read_parquet("")
        df = self.process_int_org(types="hts", agg="monthly")

        return self.process_price()
