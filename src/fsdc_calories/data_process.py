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

    def gen_plate_data(self) -> pl.DataFrame:
        # 1. Setup paths
        script_dir = Path(__file__).resolve().parent
        schedule_b_reference_path = (
            script_dir / ".." / "data" / "schedule_b_reference.xlsx"
        )

        # 2. Extract initial data as Polars DataFrame
        hts_data = self.process_int_jp(time_frame="monthly", level="hts")

        utils = ConverterUtils(schedule_b_reference_path)
        code_to_category = utils.schedule_b_to_category()

        # Create a lookup DataFrame from your category dictionary
        category_lookup = pl.DataFrame(
            {
                "lookup_code": list(code_to_category.keys()),
                "category": list(code_to_category.values()),
            }
        )

        # 3. Vectorized string manipulation, join, and shape transformations
        df_long = (
            hts_data.with_columns(
                pl.col("hts_code")
                .cast(pl.String)
                .str.slice(0, 4)
                .str.pad_end(10, "0")
                .alias("lookup_code")
            )
            .join(category_lookup, on="lookup_code", how="left")
            # Compute value counts per year and category
            .group_by(["year", "category"])
            .agg(pl.len().alias("value"))
            # Drop rows where category didn't match the dictionary lookup
            .drop_nulls(subset=["category"])
        )

        # 4. Handle "ice_cream" band-aid via Polars expressions
        # If ice_cream exists, map its value over to 'other'
        df_long = (
            df_long.with_columns(
                pl.when(pl.col("category") == "ice_cream")
                .then(pl.lit("other"))
                .otherwise(pl.col("category"))
                .alias("category")
            )
            .group_by(["year", "category"])
            .agg(pl.col("value").sum())
        )

        # Ensure all constant food categories exist (replaces reindex logic)
        all_cats = pl.DataFrame({"category": sorted(Constants.get_food_categories())})
        if "ice_cream" in all_cats["category"]:
            all_cats = all_cats.filter(pl.col("category") != "ice_cream")

        unique_years = df_long.select("year").unique()
        grid = unique_years.join(all_cats, how="cross")

        df_final = grid.join(df_long, on=["year", "category"], how="left").with_columns(
            pl.col("value").fill_null(0)
        )

        return df_final

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
            options=list(column_label_map.keys()),
            labels=list(column_label_map.values()),
            name="Y-axis column",
        )
        ycol_param = alt.param(value="total_iron_mg", bind=dropdown)

        # gen_nuti_data() is sorted directly via Polars native expressions
        return (
            alt.Chart(self.gen_nuti_data().sort("datetime"))
            .mark_line()
            .encode(x="datetime:T", y=alt.Y("y:Q").title(""))
            .transform_calculate(y=f"datum[{ycol_param.name}]")
            .add_params(ycol_param)
            .properties(width="container")
        )

    def gen_graphs_price_change(self) -> alt.HConcatChart:
        imports, _ = self.gen_price_rankings()

        # Slice top 10 and bottom 10 cleanly using Polars explicit head/tail concat
        imports = pl.concat([imports.head(10), imports.tail(10)])

        # Query DuckDB or your SQL connection directly into a Polars DataFrame
        df_lookup = pl.from_dataframe(
            self.conn.sql("SELECT DISTINCT hts_code, hts_desc FROM 'inttradedata'").df()
        )

        # Isolate hs4 substring, drop duplicate records, and trim text column
        df_lookup = (
            df_lookup.with_columns(pl.col("hts_code").str.slice(0, 4).alias("hs4"))
            .unique(subset=["hs4"])
            .with_columns(pl.col("hts_desc").str.slice(0, 30))
        )

        # Standard left-join
        df = imports.join(df_lookup.select(["hs4", "hts_desc"]), on="hs4", how="left")

        return (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("pct_change").axis(format="%", title="Change in price"),
                y=alt.Y("hts_desc").sort("-x").axis(title="HS4"),
            )
            .properties(width="container", title="Imports")
        )

    def gen_graphs_plate(self) -> alt.Chart:
        """
        Generates a production-grade, interactive donut chart showing the
        yearly food category distribution.

        Returns:
            alt.Chart: An interactive Altair chart configuration.
        """
        # ---------------------------------------------------------
        # 1. Data Ingestion & Validation
        # ---------------------------------------------------------
        try:
            hts_data = self.process_int_jp(time_frame="monthly", level="hts")
        except Exception as e:
            logger.error(f"Failed to process internal JP data: {e}")
            return alt.Chart()

        parquet_path = Path("data/external/schedule_b_reference")
        if not parquet_path.exists():
            logger.error(f"Reference file not found at path: {parquet_path}")
            return alt.Chart()

        ref_df = pl.read_parquet(parquet_path)

        # ---------------------------------------------------------
        # 2. Extract Categories & Build Lookup Map
        # ---------------------------------------------------------
        available_cats = [
            c for c in Constants.get_food_categories() if c in ref_df.columns
        ]

        if not available_cats:
            logger.warning("No food categories found matching the reference schema.")
            return alt.Chart()

        category_expr = pl.coalesce(
            [
                pl.when(pl.col(c).cast(pl.String) == "1").then(pl.lit(c))
                for c in available_cats
            ]
        ).fill_null("other")

        lookup_map = (
            ref_df.with_columns(
                pl.col("schedule_b").cast(pl.String).str.pad_end(10, "0")
            )
            .select(["schedule_b", category_expr.alias("category")])
            .drop_nulls()
        )

        # ---------------------------------------------------------
        # 3. Join, Aggregate, and Compute Percentages
        # ---------------------------------------------------------
        # Process core metrics completely inside Polars
        processed_data = (
            hts_data.with_columns(
                pl.col("hts_code")
                .cast(pl.String)
                .str.slice(0, 4)
                .str.pad_end(10, "0")
                .alias("schedule_b")
            )
            .join(lookup_map, on="schedule_b", how="left")
            .with_columns(pl.col("category").fill_null("other"))
            # Consolidate 'ice_cream' and strip out 'other'
            .with_columns(
                pl.when(pl.col("category") == "ice_cream")
                .then(pl.lit("other"))
                .otherwise(pl.col("category"))
            )
            .filter(pl.col("category") != "other")
            .group_by(["year", "category"])
            .agg(pl.len().alias("value"))
            # Calculate localized window percentage
            .with_columns(
                (pl.col("value") / pl.col("value").sum().over("year") * 100)
                .round(1)
                .alias("pct")
            )
            .with_columns(
                (pl.col("pct").cast(pl.String) + "%").alias("pct_text"),
                pl.col("category").str.to_titlecase().alias("category_clean"),
            )
        )

        # ---------------------------------------------------------
        # 4. Interactive Parameters Setup
        # ---------------------------------------------------------
        # Safely extract unique years for dropdown tracking
        valid_years = (
            processed_data.select("year")
            .unique()
            .sort("year", descending=True)["year"]
            .to_list()
        )

        if not valid_years:
            logger.warning("Processed dataset yielded zero usable records.")
            return alt.Chart()

        max_year = valid_years[0]
        default_year = valid_years[1] if len(valid_years) > 1 else max_year

        year_dropdown = alt.binding_select(options=valid_years, name="Select Year: ")
        year_select = alt.selection_point(
            fields=["year"], bind=year_dropdown, value=default_year
        )

        # Convert the slim, finalized dataframe to pandas for Altair compatibility
        chart_df = processed_data.to_pandas()

        # ---------------------------------------------------------
        # 5. Professional Visualization Assembly
        # ---------------------------------------------------------
        base = (
            alt.Chart(chart_df)
            .encode(
                theta=alt.Theta("pct:Q").stack(True),
                color=alt.Color(
                    "category_clean:N",
                    scale=alt.Scale(scheme="tableau10"),
                    legend=alt.Legend(title="Food Category", orient="right"),
                ),
                tooltip=[
                    alt.Tooltip("category_clean:N", title="Category"),
                    alt.Tooltip("year:O", title="Year"),
                    alt.Tooltip("value:Q", title="Count", format=","),
                    alt.Tooltip("pct_text:N", title="Share"),
                ],
            )
            .add_params(year_select)
            .transform_filter(year_select)
        )

        # Convert pie chart to a modern, crisp donut chart layout
        chart_arc = base.mark_arc(
            innerRadius=60, outerRadius=110, stroke="#fff", strokeWidth=2
        )

        # Clean text placement avoiding visual overlaps
        chart_text = base.mark_text(
            radius=130, size=11, font="Sans-Serif", fontWeight="bold"
        ).encode(text="pct_text:N")

        # Layer, style, and global configuration definitions
        return (
            (chart_arc + chart_text)
            .properties(
                title=alt.TitleParams(
                    text="Yearly Food Category Distribution",
                    subtitle=[
                        "Structural macro-nutrient trends (Excluding 'Other' classifications)"
                    ],
                    fontSize=16,
                    subtitleFontSize=12,
                    anchor="start",
                    color="#2c3e50",
                ),
                width=400,
                height=350,
            )
            .configure_view(strokeWidth=0)  # Removes ugly bounding chart boxes
        )
