import os
from datetime import date, datetime, timedelta
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import polars as pl

from .jp_imports.src.data.data_process import DataTrade

from .utils.constants import Constants
from .utils.converter_utils import ConverterUtils


class DataCal(DataTrade):
    def __init__(
        self,
        saving_dir: str = "data/",
        database_file: str = "data.ddb",
        log_file: str = "data_process.log",
    ):
        super().__init__(saving_dir, database_file, log_file)

    def gen_nuti_data(self) -> pl.DataFrame:
        if not os.path.exists(f"{self.saving_dir}external/nutri_matrix.parquet"):
            self.pull_file(
                url="https://github.com/EconLabs/fsdc-calories/raw/refs/heads/master/data/external/nutri_matrix.parquet",
                filename=f"{self.saving_dir}external/nutri_matrix.parquet",
            )
        nutri_df = pl.read_parquet(f"{self.saving_dir}external/nutri_matrix.parquet")
        df = self.process_int_org(time_frame="monthly", level="hts")
        nutri_df = nutri_df.rename({"schedule_b": "hts_code"}).drop("description")
        df = df.with_columns(hts_code=pl.col("hts_code").str.slice(0, 4))

        df = df.join(nutri_df, on="hts_code", how="inner")
        df = df.with_columns(
            total_calories=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("calories"),
            total_fats=(pl.col("imports_qty") - pl.col("exports_qty")) * pl.col("fats"),
            total_sugars=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("sugars"),
            total_protein=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("protein"),
            total_saturated_fat_g=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("saturated_fat_g"),
            total_cholesterol_mg=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("cholesterol_mg"),
            total_sodium_mg=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("sodium_mg"),
            total_carbohydrate_g=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("carbohydrate_g"),
            total_fiber_g=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("fiber_g"),
            total_sugar_g=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("sugar_g"),
            total_vitamin_d_iu=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("vitamin_d_iu"),
            total_calcium_mg=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("calcium_mg"),
            total_potassium_mg=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("potassium_mg"),
            total_iron_mg=(pl.col("imports_qty") - pl.col("exports_qty"))
            * pl.col("iron_mg"),
        )
        cols = [
            "total_calories",
            "total_fats",
            "total_sugars",
            "total_protein",
            "total_saturated_fat_g",
            "total_cholesterol_mg",
            "total_sodium_mg",
            "total_carbohydrate_g",
            "total_fiber_g",
            "total_sugar_g",
            "total_vitamin_d_iu",
            "total_calcium_mg",
            "total_potassium_mg",
            "total_iron_mg",
        ]
        df = df.with_columns(
            **{
                f"{x}_ecdf": pl.int_range(1, pl.len() + 1).sort_by(pl.arg_sort_by(x))
                / pl.len()
                for x in cols  # change df.columns to list of columns for subset only
            }
        )
        df = df.filter(pl.col("total_fats_ecdf") < 0.9999)
        df = df.filter(pl.col("total_sugars_ecdf") < 0.9999)
        df = df.filter(pl.col("total_protein_ecdf") < 0.9999)
        df = df.filter(pl.col("total_saturated_fat_g_ecdf") < 0.9999)
        df = df.filter(pl.col("total_sodium_mg_ecdf") < 0.9999)
        df = df.filter(pl.col("total_cholesterol_mg_ecdf") < 0.9999)
        df = df.filter(pl.col("total_carbohydrate_g_ecdf") < 0.9999)
        df = df.filter(pl.col("total_fiber_g_ecdf") < 0.9999)
        df = df.filter(pl.col("total_sugar_g_ecdf") < 0.9999)
        df = df.filter(pl.col("total_vitamin_d_iu_ecdf") < 0.9999)
        df = df.filter(pl.col("total_calcium_mg_ecdf") < 0.9999)
        df = df.filter(pl.col("total_potassium_mg_ecdf") < 0.9999)
        df = df.filter(pl.col("total_iron_mg_ecdf") < 0.9999)
        df = df.group_by(["year", "month"]).agg(pl.all().sum())
        df = df.with_columns(datetime=pl.datetime(pl.col("year"), pl.col("month"), 1))

        return df

    def gen_price_rankings(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        df: pd.DataFrame = self.process_price(agriculture_filter=True).to_pandas()

        import_pct_col = "pct_change_imports_year_over_year"
        export_pct_col = "pct_change_exports_year_over_year"

        # Fix: remove infs from the dataframe (somehow we have infinite percent change???)
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna(subset=[import_pct_col, export_pct_col])

        # Get date object of 1st day of last month
        today = date.today()
        first = today.replace(day=1)
        last_month = first - timedelta(days=1)
        last_month = last_month.replace(day=1)

        # # Handle case where latest available data is older than last month
        last_month = min(pd.Timestamp(last_month), df["date"].max())

        # Apply last month filter
        filter = df["date"] >= last_month
        df = df[filter]

        # Put pct_change in terms of decimals
        df[import_pct_col] /= 100
        df[export_pct_col] /= 100

        rename_map = {
            import_pct_col: "pct_change",
            export_pct_col: "pct_change",
        }

        # Seperate imports and exports to different dataframes
        imports = (
            df[["hs4", import_pct_col]]
            .rename(columns=rename_map)
            .sort_values(by="pct_change", ascending=False)
        )
        exports = (
            df[["hs4", export_pct_col]]
            .rename(columns=rename_map)
            .sort_values(by="pct_change", ascending=False)
        )

        return imports, exports

    def gen_plate_data(self) -> pd.DataFrame:

        # Data paths
        script_dir = Path(__file__).resolve().parent

        schedule_b_reference_path = (
            script_dir / ".." / "data" / "schedule_b_reference.xlsx"
        )
        hts_data = (
            DataTrade()
            .process_int_org(time_frame="monthly", level="hts", agriculture_filter=True)
            .to_pandas()
        )

        hts_data["hts_code"] = hts_data["hts_code"].astype(str)

        utils = ConverterUtils(schedule_b_reference_path)
        code_to_category = utils.schedule_b_to_category()

        nutrient_distribution_yearly = {}

        min_year, max_year = hts_data["year"].min(), hts_data["year"].max()
        for year in range(min_year, max_year + 1):
            plate_distribution = {cat: 0 for cat in Constants.get_food_categories()}
            data_current_year = hts_data[hts_data["year"] == year]
            for index, row in data_current_year.iterrows():
                current_code = row["hts_code"][:4].ljust(10, "0")
                if current_code in code_to_category:
                    plate_distribution[code_to_category[current_code]] += 1
            # BANDAID: MOVE ICECREAM COUNT TO OTHER

            plate_distribution["other"] += plate_distribution["ice_cream"]
            plate_distribution.pop("ice_cream")

            # Sort plate distribution by category
            plate_distribution = dict(sorted(plate_distribution.items()))

            nutrient_distribution_yearly[year] = plate_distribution

        df = (
            pd.DataFrame(nutrient_distribution_yearly)
            .reset_index()
            .rename(columns={"index": "category"})
        )
        df_long = pd.melt(df, id_vars=["category"], var_name="year", value_name="value")
        return df_long

    def gen_graphs_nuti_data(self):
        column_label_map = {
            "total_calories": "Calories",
            "total_fats": "Fats",
            "total_sugars": "Sugars",
            "total_protein": "Proteins",
            "total_saturated_fat_g": "Saturated Fats (g)",
            "total_cholesterol_mg": "Cholesterol (mg)",
            "total_sodium_mg": "Sodium (mg)",
            "total_carbohydrate_g": "Carbohydrates (g)",
            "total_fiber_g": "Fibers (g)",
            "total_sugar_g": "Sugars (g)",
            "total_vitamin_d_iu": "Vitam D (iu)",
            "total_calcium_mg": "Calcium (mg)",
            "total_potassium_mg": "Potassium (mg)",
            "total_iron_mg": "Iron (mg)",
        }

        dropdown = alt.binding_select(
            options=column_label_map.keys(),
            name="Y-axis column",
            labels=column_label_map.values(),
        )
        ycol_param = alt.param(value="total_iron_mg", bind=dropdown)
        chart = (
            alt.Chart(self.gen_nuti_data().sort(pl.col("datetime")))
            .mark_line()
            .encode(x="datetime:T", y=alt.Y("y:Q").title(""))
            .transform_calculate(y=f"datum[{ycol_param.name}]")
            .add_params(ycol_param)
            .properties(width="container")
        )

        return chart

    def gen_graphs_price_change(self) -> alt.HConcatChart:
        imports, exports = self.gen_price_rankings()

        # Limit to top 10 for each dataframe
        imports, exports = imports.head(10), exports.head(10)

        imports_chart = (
            alt.Chart(imports)
            .mark_bar()
            .encode(
                x=alt.X("pct_change").axis(format="%", title="Change in price"),
                y=alt.Y("hs4").sort("-x").axis(title="HS4"),
            )
            .properties(width="container", title="Imports")
        )

        # exports_chart = (
        #     alt.Chart(exports)
        #     .mark_bar()
        #     .encode(x="hs4", y="pct_change")
        #     .properties(width="container", title="Exports")
        # )

        return imports_chart

    def gen_graphs_plate(self) -> alt.Chart:
        plate_data: pd.DataFrame = self.gen_plate_data()

        # Calculate percent of category for each year
        plate_data["pct"] = (
            plate_data["value"]
            / plate_data.groupby(by="year")["value"].transform("sum")
            * 100
        ).round(1)

        # Bandaid: Prefix each pct value with % for chart display
        plate_data["pct_text"] = plate_data["pct"].astype(str) + "%"

        valid_years = [
            year
            for year in range(plate_data["year"].min(), plate_data["year"].max() + 1)
        ]
        valid_years.reverse()

        max_year = max(valid_years)
        year_dropdown = alt.binding_select(options=valid_years, name="Year")
        year_select = alt.selection_point(
            fields=["year"], bind=year_dropdown, value=max_year - 1
        )

        base = (
            alt.Chart(plate_data)
            .encode(
                theta=alt.Theta("pct:Q").stack(True),
                color=alt.Color("category"),
            )
            .add_params(year_select)
            .transform_filter(year_select)
            .properties(title="Yearly MyPlate Nutrient Distribution")
        )

        c1 = base.mark_arc(outerRadius=100, innerRadius=20, stroke="#fff")

        c2 = base.mark_text(radius=100, radiusOffset=15, size=10).encode(
            text="pct_text:N"
        )

        return c1 + c2
