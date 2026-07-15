import importlib.resources as resources
import logging
from pathlib import Path

import altair as alt
from datetime import date, timedelta
import numpy as np
import polars as pl
import pandas as pd
from jp_imports import JPTrade

from .utils.constants import Constants

# alt.data_transformers.enable("vegafusion")
logger = logging.getLogger(__name__)

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
        log_file: str = "data.log",
    ):
        super().__init__(saving_dir, log_file)

    def gen_nuti_data(self, time_frame: str = "fiscal") -> pl.DataFrame:
        """
        Generate nutrition data dynamically aggregated across different timeframes.
        All mass metrics are standardized and renamed to end with '_kg'.
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

        # 4. Compute metrics
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

        # Calculate totals and apply unit conversion simultaneously 
        df = df.with_columns(
            [
                (
                    (pl.col(col) * pl.col("net_qty")).alias(self.get_kg_col_name(col))
                    if col == "calories"
                    else (self.standardize_to_kg(col) * pl.col("net_qty")).alias(self.get_kg_col_name(col))
                )
                for col in base_nutri_cols
            ]
        )

        # Update target metric keys for downstream pipeline steps
        total_cols = [self.get_kg_col_name(col) for col in base_nutri_cols]

        # 5. Apply Empirical Cumulative Distribution Function (ECDF) filters
        filter_cols = [col for col in total_cols if col != "total_calories"]

        df = df.with_columns(
            [
                (pl.col(col).rank("ordinal") / pl.len()).alias(f"{col}_ecdf")
                for col in filter_cols
            ]
        )

        # Combine all filters into a single call
        df = df.filter([pl.col(f"{col}_ecdf") < 0.9999 for col in filter_cols])

        # 6. Dynamically resolve group-by columns based on time_frame
        time_cols = TIME_GROUPS.get(time_frame, ["fiscal_year"])
        group_keys = time_cols + ["hts_code"]

        # 7. Final aggregation
        df = df.group_by(group_keys).agg([pl.col(col).sum() for col in total_cols])

        if time_frame == "monthly":
            df = df.with_columns(
                datetime=pl.datetime(pl.col("year"), pl.col("month"), 1)
            )

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

    def gen_graphs_nuti_data(self) -> alt.Chart:
        """Generates an interactive line chart tracking nutritional metrics over time."""
        column_label_map = {
            "total_calories": "Calories (kcal)",
            "total_fats_kg": "Fats (kg)",
            "total_sugars_kg": "Sugars (kg)",
            "total_protein_kg": "Proteins (kg)",
            "total_saturated_fat_kg": "Saturated Fats (kg)",
            "total_cholesterol_kg": "Cholesterol (kg)",
            "total_sodium_kg": "Sodium (kg)",
            "total_carbohydrate_kg": "Carbohydrates (kg)",
            "total_fiber_kg": "Fibers (kg)",
            "total_sugar_kg": "Sugars (kg)",
            "total_vitamin_d_kg": "Vitamin D (kg)",
            "total_calcium_kg": "Calcium (kg)",
            "total_potassium_kg": "Potassium (kg)",
            "total_iron_kg": "Iron (kg)",
        }

        # 1. Pre-aggregate data using Polars
        data = (
            self.gen_nuti_data(time_frame="monthly")
            .group_by("datetime")
            .agg([pl.col(c).sum() for c in column_label_map.keys()])
            .sort("datetime")
            .to_pandas()
        )

        if data.empty:
            return alt.Chart(data).mark_text(text="No data available")

        # 2. Dropdown binding parameter
        dropdown = alt.binding_select(
            options=list(column_label_map.keys()),
            labels=list(column_label_map.values()),
            name="Nutrient: ",
        )
        ycol_param = alt.param(
            name="selected_metric", value="total_iron_kg", bind=dropdown
        )

        # 3. Selection parameter for interactive hover tooltips
        hover_select = alt.selection_point(on="pointerover", nearest=True, empty=False)

        # 4. Base chart with calculated field
        base = (
            alt.Chart(data)
            .transform_calculate(selected_value=f"datum[{ycol_param.name}]")
            .add_params(ycol_param)
        )

        # 5. Primary line chart
        line = base.mark_line(
            color="#1f77b4", strokeWidth=2.5, point=False, interpolate="monotone"
        ).encode(
            x=alt.X(
                "datetime:T", title="Date", axis=alt.Axis(format="%b %Y", grid=False)
            ),
            y=alt.Y(
                "selected_value:Q",
                title=None,
                axis=alt.Axis(
                    format="~s",
                    gridDash=[2, 2],
                    gridColor="#E0E0E0",
                ),
            ),
        )

        # 6. Interactive hover points & tooltips
        points = base.mark_point(size=60, filled=True, color="#1f77b4").encode(
            x="datetime:T",
            y="selected_value:Q",
            opacity=alt.condition(hover_select, alt.value(1), alt.value(0)),
            tooltip=[
                alt.Tooltip("datetime:T", title="Date", format="%B %Y"),
                alt.Tooltip(
                    "selected_value:Q",
                    title="Value",
                    format="~s",
                ),
            ],
        )

        # Invisible rule selector for better hover snapping
        selectors = (
            base.mark_rule(opacity=0).encode(x="datetime:T").add_params(hover_select)
        )

        # 7. Combine layers & apply production styling
        final_chart = (
            alt.layer(line, points, selectors)
            .properties(
                width="container",
                height=380,
                title=alt.TitleParams(
                    text="Nutritional Intake Over Time",
                    subtitle="Select a nutrient from the dropdown menu below to update the view.",
                    fontSize=16,
                    subtitleFontSize=12,
                    anchor="start",
                ),
            )
            .configure_view(strokeWidth=0)
            .configure_axis(labelFontSize=11, titleFontSize=12)
        )

        return final_chart

    def gen_graphs_price_change(self) -> alt.HConcatChart:
        """Generates a side-by-side bar chart showing the largest price changes

        (top 10 increases & bottom 10 decreases) for both Imports and Exports.

        Returns:
            alt.HConcatChart: Horizontally concatenated Altair chart.
        """
        # 1. Fetch ranking data
        imports_df, exports_df = self.gen_price_rankings()

        # 2. Query commodity descriptions from DuckDB safely
        query = f"""
            SELECT DISTINCT 
                SUBSTRING(hts_code, 1, 4) AS hs4,
                SUBSTRING(hts_desc, 1, 30) AS hts_desc
            FROM '{self.saving_dir}/raw/jp_data.parquet'
        """
        desc_df = self.conn.execute(query).df()
        desc_df = desc_df.drop_duplicates(subset=["hs4"])

        def process_and_build_chart(df: pd.DataFrame, title_text: str) -> alt.Chart:
            """Helper to deduplicate top/bottom records, join descriptions, and build chart."""
            if df.empty:
                return alt.Chart(pd.DataFrame()).mark_text(text=f"No {title_text} Data")

            # Select Top 10 and Bottom 10 without duplicate overlap if total rows < 20
            top = df.head(10)
            bottom = df.tail(10)
            combined = pd.concat([top, bottom], ignore_index=True).drop_duplicates()

            # Join descriptions on 'hs4'
            merged = combined.merge(desc_df, on="hs4", how="left")
            merged["hts_desc"] = merged["hts_desc"].fillna("Unknown Commodity")

            # Add visual helper column for color encoding (positive vs negative change)
            merged["change_type"] = merged["pct_change"].apply(
                lambda x: "Increase" if x >= 0 else "Decrease"
            )

            # Build chart layer
            chart = (
                alt.Chart(merged)
                .mark_bar(cornerRadiusEnd=3)
                .encode(
                    x=alt.X(
                        "pct_change:Q",
                        title="Price Change",
                        axis=alt.Axis(format="+.1%", grid=True, gridDash=[2, 2]),
                    ),
                    y=alt.Y(
                        "hts_desc:N",
                        title=None,
                        sort=alt.EncodingSortField(
                            field="pct_change", order="descending"
                        ),
                        axis=alt.Axis(labelLimit=200),
                    ),
                    color=alt.Color(
                        "change_type:N",
                        scale=alt.Scale(
                            domain=["Increase", "Decrease"],
                            range=[
                                "#4daf4a",
                                "#e41a1c",
                            ],  # Red for increase, Green for decrease
                        ),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("hs4:N", title="HS4 Code"),
                        alt.Tooltip("hts_desc:N", title="Description"),
                        alt.Tooltip("pct_change:Q", title="Change", format="+.2%"),
                    ],
                )
                .properties(
                    width=320,
                    height=350,
                    title=alt.TitleParams(
                        text=title_text,
                        fontSize=14,
                        anchor="start",
                    ),
                )
            )

            # Add reference zero-line for clear visual separation
            rule = (
                alt.Chart(pd.DataFrame({"x": [0]}))
                .mark_rule(color="#666666", strokeDash=[2, 2])
                .encode(x="x:Q")
            )

            return alt.layer(chart, rule)

        # 3. Process both Imports and Exports
        imports_chart = process_and_build_chart(imports_df, "Imports")
        exports_chart = process_and_build_chart(exports_df, "Exports")

        # 4. Concatenate side-by-side with shared configurations
        final_chart = (
            alt.hconcat(imports_chart, exports_chart)
            .resolve_scale(y="independent")  # Keep distinct category labels per chart
            .configure_view(strokeWidth=0)
            .configure_axis(labelFontSize=10, titleFontSize=11)
        )

        return final_chart

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
            .with_columns(
                pl.when(pl.col("category") == "ice_cream")
                .then(pl.lit("other"))
                .otherwise(pl.col("category"))
            )
            .filter(pl.col("category") != "other")
            .group_by(["year", "category"])
            .agg(pl.len().alias("value"))
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

        chart_arc = base.mark_arc(
            innerRadius=60, outerRadius=110, stroke="#fff", strokeWidth=2
        )

        chart_text = base.mark_text(
            radius=130, size=11, font="Sans-Serif", fontWeight="bold"
        ).encode(text="pct_text:N")

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
            .configure_view(strokeWidth=0)
        )

    def standardize_to_kg(self, col_name: str) -> pl.Expr:
        """
        Helper method to standardize raw nutritional inputs to kilograms (kg).
        """
        if col_name.endswith("_g") or col_name in ["fats", "sugars", "protein"]:
            # Grams to kg
            return pl.col(col_name) / 1_000
        elif col_name.endswith("_mg"):
            # Milligrams to kg
            return pl.col(col_name) / 1_000_000
        elif col_name.endswith("_iu"):
            # Vitamin D IU to kg: 1 IU = 0.025 mcg = 2.5e-11 kg
            return pl.col(col_name) * 2.5e-11
        else:
            # Fallback for unmatched columns (like calories)
            return pl.col(col_name)

    def get_kg_col_name(self, col_name: str) -> str:
        """
        Helper method to generate the target column name ending in '_kg'.
        Example: 'saturated_fat_g' -> 'total_saturated_fat_kg'
                 'fats'            -> 'total_fats_kg'
        """
        if col_name == "calories":
            return "total_calories"
        
        # Strip existing unit suffixes if present
        for suffix in ["_g", "_mg", "_iu"]:
            if col_name.endswith(suffix):
                return f"total_{col_name[:-len(suffix)]}_kg"
        
        # Otherwise append _kg directly (for fats, sugars, protein)
        return f"total_{col_name}_kg"
