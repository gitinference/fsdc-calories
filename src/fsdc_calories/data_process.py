from datetime import date, timedelta
from pathlib import Path

import altair as alt
import numpy as np
import importlib.resources as resources
import pandas as pd
import polars as pl

from jp_imports import JPTrade


from .utils.constants import Constants
from .utils.converter_utils import ConverterUtils

TIME_GROUPS = {
    "yearly": ["year"],
    "fiscal": ["fiscal_year"],
    "qtr": ["year", "qtr"],
    "monthly": ["year", "month"],
}


class DataCal(JPTrade):
    def __init__(
        self,
        saving_dir: str = "data/",
        database_file: str = "data.ddb",
    ):
        super().__init__(saving_dir, database_file)

    def gen_nuti_data(self, time_frame: str = "fiscal") -> pl.DataFrame:
        """
        Generate nutrition data dynamically aggregated across different timeframes.
        """
        # 1. Load nutrition matrix
        nutri_df = pl.read_parquet(
            str(resources.files("fsdc_calories").joinpath("data/nutri_matrix.parquet"))
        )
        nutri_df = nutri_df.rename({"schedule_b": "hts_code"}).drop("description")
        nutri_df = nutri_df.unique(subset="hts_code", keep="first")

        # 2. Pull trade data using the dynamic timeframe
        df = self.process_int_jp(time_frame=time_frame, level="hts")

        # 3. Match HTS lengths (slicing down to 4 digits to match nutri matrix)
        df = df.with_columns(hts_code=pl.col("hts_code").str.slice(0, 4))
        df = df.join(nutri_df, on="hts_code", how="inner", validate="m:1")

        # 4. Compute metrics using a list comprehension to avoid repetitive code
        df = df.with_columns(net_qty=pl.col("imports_qty") - pl.col("exports_qty"))

        base_nutri_cols = [
            "calories",
            "fats",
            "sugars",
            "protein",
            "saturated_fat_g",
            "cholesterol_mg",
            "sodium_mg",
            "carbohydrate_g",
            "fiber_g",
            "sugar_g",
            "vitamin_d_iu",
            "calcium_mg",
            "potassium_mg",
            "iron_mg",
        ]

        # Calculate totals for all nutritional columns simultaneously
        df = df.with_columns(
            [
                (pl.col(col) * pl.col("net_qty")).alias(f"total_{col}")
                for col in base_nutri_cols
            ]
        )

        # 5. Apply Empirical Cumulative Distribution Function (ECDF) filters
        # (Excluding total_calories as per your original logic)
        filter_cols = [f"total_{col}" for col in base_nutri_cols if col != "calories"]

        df = df.with_columns(
            [
                (pl.col(col).rank("ordinal") / pl.len()).alias(f"{col}_ecdf")
                for col in filter_cols
            ]
        )

        # Combine all filters into a single call (Polars evaluates commas as AND)
        df = df.filter([pl.col(f"{col}_ecdf") < 0.9999 for col in filter_cols])

        # 6. Dynamically resolve group-by columns based on time_frame
        # Note: Make sure TIME_GROUPS is imported into this package file
        time_cols = TIME_GROUPS.get(time_frame, ["fiscal_year"])
        group_keys = time_cols + ["hts_code"]

        # 7. Final aggregation
        total_cols = [f"total_{col}" for col in base_nutri_cols]
        df = df.group_by(group_keys).agg([pl.col(col).sum() for col in total_cols])

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
        top = imports.head(10)
        bottom = imports.tail(10)
        imports = pd.concat([top, bottom], ignore_index=True, sort=False)

        df = self.conn.sql("SELECT DISTINCT hts_code,hts_desc FROM 'inttradedata'").df()
        df["hts_desc"] = df["hts_desc"].str.slice(stop=30)
        df["hs4"] = df["hts_code"].str.slice(stop=4)
        df = df.drop_duplicates(subset=["hs4"]).reset_index(drop=True)
        df = df[["hs4", "hts_desc"]]

        df = imports.join(df.set_index("hs4"), on="hs4")

        imports_chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("pct_change").axis(format="%", title="Change in price"),
                y=alt.Y("hts_desc").sort("-x").axis(title="HS4"),
            )
            .properties(width="container", title="Imports")
        )

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

        c1 = base.mark_arc(outerRadius=100, stroke="#fff")

        c2 = base.mark_text(radius=100, radiusOffset=15, size=10).encode(
            text="pct_text:N"
        )

        return c1 + c2
