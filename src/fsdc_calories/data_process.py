import importlib.resources as resources
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Literal
import plotly.graph_objects as go
import plotly.express as px

import altair as alt
import numpy as np
import pandas as pd
import polars as pl
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
        nutri_df = nutri_df.with_columns(
            calories=pl.col("calories") * 10
        )  # add due to original matrix in Kcal per 100gm

        # 2. Pull trade data using the dynamic timeframe
        df = self.process_int_jp(
            time_frame=time_frame, level="hts", source="org", corrections=True
        )
        df = df.with_columns(
            net_qty=pl.when(pl.col("net_imports_qty") < 0)
            .then(pl.lit(0))
            .otherwise(pl.col("net_imports_qty"))
        )

        # 3. Match HTS lengths (slicing down to 4 digits to match nutri matrix)
        df = df.with_columns(hts_code=pl.col("hts_code").str.slice(0, 4))
        df = df.join(nutri_df, on="hts_code", how="inner", validate="m:1")

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
                    else (self.standardize_to_kg(col) * pl.col("net_qty")).alias(
                        self.get_kg_col_name(col)
                    )
                )
                for col in base_nutri_cols
            ]
        )

        # Update target metric keys for downstream pipeline steps
        total_cols = [self.get_kg_col_name(col) for col in base_nutri_cols] + [
            "net_qty",
            "protein",
            "vegetable",
            "dairy",
            "fruits",
            "grains",
            "ice_cream",
            "fats",
            "sugars",
            "other",
        ]

        df = df.with_columns(
            protein=pl.col("total_calories") * pl.col("protein"),
            vegetable=pl.col("total_calories") * pl.col("protein"),
            dairy=pl.col("total_calories") * pl.col("dairy"),
            fruits=pl.col("total_calories") * pl.col("fruits"),
            grains=pl.col("total_calories") * pl.col("grains"),
            ice_cream=pl.col("total_calories") * pl.col("ice_cream"),
            fats=pl.col("total_calories") * pl.col("fats"),
            sugars=pl.col("total_calories") * pl.col("sugars"),
            other=pl.col("total_calories") * pl.col("other"),
        )

        time_cols = TIME_GROUPS.get(time_frame, ["fiscal_year"])
        group_keys = time_cols + ["hts_code"]

        # 7. Final aggregation
        df = df.group_by(group_keys).agg([pl.col(col).sum() for col in total_cols])

        if time_frame == "monthly":
            df = df.with_columns(
                datetime=pl.datetime(pl.col("year"), pl.col("month"), 1)
            )

        return df

    def gen_nuti_data_local(self) -> pl.DataFrame:
        df_local = pl.read_parquet(
            str(
                resources.files("fsdc_calories").joinpath(
                    "data/local_nutri_data.parquet"
                )
            )
        )
        df_local = df_local.with_columns(
            hts_code=pl.col("hts").cast(pl.String).str.zfill(4),
            net_qty=pl.col("produccion_kg"),
            fiscal_year=pl.col("fiscal_year").cast(pl.Int32),
        )
        df_local = df_local.select(pl.col("fiscal_year", "hts_code", "net_qty"))

        nutri_df = pl.read_parquet(
            str(resources.files("fsdc_calories").joinpath("data/nutri_matrix.parquet"))
        )
        nutri_df = nutri_df.rename({"schedule_b": "hts_code"}).drop("description")
        nutri_df = nutri_df.unique(subset="hts_code", keep="first")
        nutri_df = nutri_df.with_columns(
            calories=pl.col("calories") * 10
        )  # add due to original matrix in Kcal per 100gm

        df_local = df_local.with_columns(hts_code=pl.col("hts_code").str.slice(0, 4))
        df_local = df_local.join(nutri_df, on="hts_code", how="inner", validate="m:1")

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
        df_local = df_local.with_columns(
            [
                (
                    (pl.col(col) * pl.col("net_qty")).alias(self.get_kg_col_name(col))
                    if col == "calories"
                    else (self.standardize_to_kg(col) * pl.col("net_qty")).alias(
                        self.get_kg_col_name(col)
                    )
                )
                for col in base_nutri_cols
            ]
        )

        # Update target metric keys for downstream pipeline steps
        total_cols = [self.get_kg_col_name(col) for col in base_nutri_cols]

        df_local = df_local.group_by(["fiscal_year", "hts_code"]).agg(
            [pl.col(col).sum() for col in total_cols]
        )

        return df_local

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
        """Generates an interactive line chart tracking imported nutritional metrics over time."""
        column_label_map = {
            "total_calories": "Imported Calories (kcal)",
            "total_fats_kg": "Imported Fats (kg)",
            "total_sugars_kg": "Imported Sugars (kg)",
            "total_protein_kg": "Imported Proteins (kg)",
            "total_saturated_fat_kg": "Imported Saturated Fats (kg)",
            "total_cholesterol_kg": "Imported Cholesterol (kg)",
            "total_sodium_kg": "Imported Sodium (kg)",
            "total_carbohydrate_kg": "Imported Carbohydrates (kg)",
            "total_fiber_kg": "Imported Fibers (kg)",
            "total_sugar_kg": "Imported Sugars (kg)",
            "total_vitamin_d_kg": "Imported Vitamin D (kg)",
            "total_calcium_kg": "Imported Calcium (kg)",
            "total_potassium_kg": "Imported Potassium (kg)",
            "total_iron_kg": "Imported Iron (kg)",
        }

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
            name="Imported Nutrient: ",
        )
        ycol_param = alt.param(
            name="selected_metric", value="total_calories", bind=dropdown
        )

        # 3. Selection parameter for interactive hover tooltips
        hover_select = alt.selection_point(on="pointerover", nearest=True, empty=False)

        # Define standard tooltips for reusable encoding
        tooltip_config = [
            alt.Tooltip("datetime:T", title="Date", format="%B %Y"),
            alt.Tooltip("selected_value:Q", title="Imported Value", format=",.2f"),
        ]

        # 4. Base chart with calculated field
        base = (
            alt.Chart(data)
            .transform_calculate(selected_value=f"datum[{ycol_param.name}]")
            .add_params(ycol_param)
        )

        # 5. Primary line chart
        # Using labelExpr to replace 'G' with 'B' in the rendered axis label text
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
                    labelExpr="replace(datum.label, 'G', 'B')",
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
            tooltip=tooltip_config,
        )

        # Transparent rule selector for seamless hover snapping across the x-axis
        selectors = (
            base.mark_rule(strokeWidth=20, opacity=0)
            .encode(
                x="datetime:T",
                tooltip=tooltip_config,  # Direct tooltip attached to hover area
            )
            .add_params(hover_select)
        )

        # 7. Combine layers & apply production styling
        final_chart = (
            alt.layer(line, points, selectors)
            .properties(
                width="container",
                height=380,
                title=alt.TitleParams(
                    text="Imported Nutritional Intake Over Time",
                    subtitle="Select an imported nutrient from the dropdown menu below to update the view.",
                    fontSize=16,
                    subtitleFontSize=12,
                    anchor="start",
                ),
            )
            .configure_view(strokeWidth=0)
            .configure_axis(labelFontSize=11, titleFontSize=12)
        )

        return final_chart

    def gen_graphs_nuti_data_fiscal(
        self, source: Literal["imported", "local", "both"] = "both"
    ) -> go.Figure:
        """Generates an interactive Plotly line chart tracking nutritional metrics over fiscal years,
        styled to match the template standard.

        :param source: Data source to display - 'imported', 'local', or 'both'
            (sum of imported + local).
        """
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

        # Fetch data based on selected source option
        if source == "imported":
            data = self.gen_nuti_data(time_frame="fiscal")
        elif source == "local":
            data = self.gen_nuti_data_local()
        elif source == "both":
            df_imports = self.gen_nuti_data(time_frame="fiscal").drop(
                "net_qty",
                "protein",
                "vegetable",
                "dairy",
                "fruits",
                "grains",
                "ice_cream",
                "fats",
                "sugars",
                "other",
            )
            df_local = self.gen_nuti_data_local()
            df_local = df_local.filter(pl.col("fiscal_year") > 2002)
            data = pl.concat([df_imports, df_local], how="diagonal")
        else:
            raise ValueError(
                f"Invalid source '{source}'. Expected 'imported', 'local', or 'both'."
            )

        # Process and aggregate Polars DataFrame
        df_pd = (
            data.group_by("fiscal_year")
            .agg([pl.col(c).sum() for c in column_label_map.keys()])
            .sort("fiscal_year")
            .to_pandas()
        )

        if df_pd.empty:
            fig = go.Figure()
            fig.update_layout(
                title="No data available",
                template="plotly_white",
                font=dict(family="Inter, sans-serif", size=12, color="#2C3E50"),
            )
            return fig

        source_label = "Combined" if source == "both" else source.capitalize()
        subtitle_map = {
            "imported": "Showing imported nutritional intake data.",
            "local": "Showing local nutritional intake data.",
            "both": "Showing combined imported + local nutritional intake data.",
        }

        # 1. Create figure
        fig = go.Figure()

        # 2. Add traces for each nutrient metric using dropdown visibility flags
        metrics = list(column_label_map.keys())
        for i, metric in enumerate(metrics):
            metric_label = column_label_map[metric]

            fig.add_trace(
                go.Scatter(
                    x=df_pd["fiscal_year"],
                    y=df_pd[metric],
                    mode="lines+markers",
                    name=metric_label,
                    line=dict(color="#2980B9", width=2.5, shape="spline"),
                    marker=dict(size=6, color="#2980B9"),
                    hovertemplate=(
                        f"<b>Fiscal Year:</b> %{{x}}<br>"
                        f"<b>{metric_label}:</b> %{{y:,.2f}}<br>"
                        "<extra></extra>"
                    ),
                    visible=(i == 0),  # Show the first metric by default
                )
            )

        # 3. Create dropdown buttons to switch metrics dynamically
        buttons = []
        for i, metric in enumerate(metrics):
            metric_label = column_label_map[metric]
            visibility = [j == i for j in range(len(metrics))]

            buttons.append(
                dict(
                    label=metric_label,
                    method="update",
                    args=[
                        {"visible": visibility},
                        {
                            "title": dict(
                                text=(
                                    f"<b>{source_label} {metric_label} by Fiscal Year</b><br>"
                                    f"<sup>{subtitle_map.get(source, '')} Select a metric from the dropdown menu above.</sup>"
                                ),
                                font=dict(
                                    size=16, family="Inter, sans-serif", color="#2C3E50"
                                ),
                                x=0.0,
                                xanchor="left",
                                y=0.98,
                                yanchor="top",
                            ),
                            "yaxis.title_text": metric_label,
                        },
                    ],
                )
            )

        default_metric_label = column_label_map[metrics[0]]

        # 4. Configure layout styling matching the reference template
        fig.update_layout(
            updatemenus=[
                dict(
                    type="dropdown",
                    direction="down",
                    active=0,
                    x=0.0,
                    xanchor="left",
                    y=1.18,
                    yanchor="top",
                    bgcolor="#FFFFFF",
                    bordercolor="#BDC3C7",
                    borderwidth=1,
                    font=dict(family="Inter, sans-serif", size=12, color="#2C3E50"),
                    buttons=buttons,
                )
            ],
            template="plotly_white",
            title=dict(
                text=(
                    f"<b>{source_label} {default_metric_label} by Fiscal Year</b><br>"
                    f"<sup>{subtitle_map.get(source, '')} Select a metric from the dropdown menu above.</sup>"
                ),
                font=dict(size=16, family="Inter, sans-serif", color="#2C3E50"),
                x=0.0,
                xanchor="left",
                y=0.98,
                yanchor="top",
            ),
            font=dict(family="Inter, sans-serif", size=11, color="#34495E"),
            height=480,
            margin=dict(l=80, r=40, t=140, b=60),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="#FFFFFF",  # Solid white background for the hover tooltip box
                bordercolor="#BDC3C7",  # Matching border color
                font=dict(family="Inter, sans-serif", size=12, color="#2C3E50"),
            ),
            showlegend=False,
        )

        # 5. Configure Axes
        fig.update_xaxes(
            title_text="Fiscal Year", showgrid=False, tickformat="d", dtick=1
        )

        fig.update_yaxes(
            title_text=default_metric_label,
            showgrid=True,
            gridcolor="#E5E8E8",
            zeroline=True,
            zerolinecolor="#2C3E50",
            zerolinewidth=1,
        )

        return fig

    def gen_graphs_price_change(self) -> alt.HConcatChart:
        """Generates a side-by-side bar chart showing the largest price changes

        (top 10 increases & bottom 10 decreases) for both Imports and Exports.

        Returns:
            alt.HConcatChart: Horizontally concatenated Altair chart.
        """
        df = self.process_price(agriculture_filter=True)
        path_data = str(
            resources.files("fsdc_calories").joinpath("data/hts4_walk.parquet")
        )

        desc_df = pl.read_parquet(path_data).rename(
            {"code_4": "hs4", "Description": "hts_desc"}
        )
        desc_df.with_columns(pl.col("hs4") == "1516")

        df = df.join(desc_df, on="hs4", how="inner", validate="m:1")

        # 1. Filter for the latest date & prepare columns (with word-based truncation)
        latest_data = (
            df.filter(pl.col("date") == pl.col("date").max())
            .with_columns(
                actual_yoy=pl.col("price_imports_yoy"),
                plot_yoy=pl.col("price_imports_yoy").clip(-100, 100),
                # Format the text label (+15.2% or -5.4%)
                text_label=(
                    pl.col("price_imports_yoy").round(1).cast(pl.Utf8) + "%"
                ).str.replace(r"^([0-9])", r"+$1"),
                # Split by whitespace, take first 4 words, join back, and append "..." if longer
                short_desc=(
                    pl.col("hts_desc").str.split(" ").list.head(4).list.join(" ")
                    + pl.when(pl.col("hts_desc").str.split(" ").list.len() > 4)
                    .then(pl.lit("..."))
                    .otherwise(pl.lit(""))
                ),
            )
            .with_columns(
                # Check for duplicates of short_desc and append a differentiator (e.g., " (2)", " (3)")
                short_desc=pl.when(
                    pl.col("short_desc").is_duplicated().over("short_desc")
                )
                .then(
                    pl.col("short_desc")
                    + " ("
                    + (pl.cum_count("short_desc").over("short_desc").cast(pl.Utf8))
                    + ")"
                )
                .otherwise(pl.col("short_desc"))
            )
        )

        # 2. Extract Top 50 and Bottom 50
        # Top 50: Sort ascending so the largest positive value is last (at the top of the chart)
        top_50_data = (
            latest_data.sort("actual_yoy", descending=True)
            .head(30)
            .to_pandas()
            .iloc[::-1]
        )

        # Bottom 50: We want the biggest drop (most negative) at the top.
        # Sorting ascending with .head(50) gives the most negative values first,
        # so we reverse it (.iloc[::-1]) so the absolute largest drop lands at the very top.
        bottom_50_data = (
            latest_data.sort("actual_yoy", descending=False)
            .head(50)
            .to_pandas()
            .iloc[::-1]
        )

        # 3. Create a single figure (no subplots needed)
        fig = go.Figure()

        # Enhanced hover template
        hover_template = (
            "<b>Description:</b> %{y}<br>"
            "<b>HS4 Code:</b> %{customdata[0]}<br>"
            "<b>Price Imports YoY:</b> %{customdata[1]:.1f}%<br>"
            "<extra></extra>"
        )

        # 4. Add Top 50 Trace (Index 0 - Shown by default)
        fig.add_trace(
            go.Bar(
                x=top_50_data["plot_yoy"],
                y=top_50_data["short_desc"],
                text=top_50_data["text_label"],
                textposition="outside",
                orientation="h",
                customdata=list(zip(top_50_data["hs4"], top_50_data["actual_yoy"])),
                hovertemplate=hover_template,
                marker=dict(
                    color=top_50_data["plot_yoy"],
                    colorscale="Viridis",
                    showscale=False,
                    opacity=0.9,
                    line=dict(color="rgba(0,0,0,0.1)", width=0.5),
                ),
                visible=True,
            )
        )

        # 5. Add Bottom 50 Trace (Index 1 - Hidden by default)
        fig.add_trace(
            go.Bar(
                x=bottom_50_data["plot_yoy"],
                y=bottom_50_data["short_desc"],
                text=bottom_50_data["text_label"],
                textposition="outside",
                orientation="h",
                customdata=list(
                    zip(bottom_50_data["hs4"], bottom_50_data["actual_yoy"])
                ),
                hovertemplate=hover_template,
                marker=dict(
                    color=bottom_50_data["plot_yoy"],
                    colorscale="Viridis_r",
                    showscale=False,
                    opacity=0.9,
                    line=dict(color="rgba(0,0,0,0.1)", width=0.5),
                ),
                visible=False,
            )
        )

        # 6. Configure Tab-Style Buttons (Updatemenus)
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    active=0,
                    x=0.5,
                    xanchor="center",
                    y=1.12,
                    yanchor="top",
                    bgcolor="#F8F9F9",
                    bordercolor="#BDC3C7",
                    borderwidth=1,
                    font=dict(family="Inter, sans-serif", size=12, color="#2C3E50"),
                    buttons=[
                        dict(
                            label="Top 50 Categories (YoY % Increase)",
                            method="update",
                            args=[
                                {"visible": [True, False]},
                                {
                                    "xaxis.range": [0, 120],
                                    "xaxis.title_text": "YoY % Change",
                                },
                            ],
                        ),
                        dict(
                            label="Bottom 50 Categories (YoY % Decrease)",
                            method="update",
                            args=[
                                {"visible": [False, True]},
                                {
                                    "xaxis.range": [-120, 0],
                                    "xaxis.title_text": "YoY % Change",
                                },
                            ],
                        ),
                    ],
                )
            ],
            template="plotly_white",
            title=dict(
                text="<b>Import Price Volatility: Extreme YoY Changes</b><br><sup>Switch between top positive and negative HS4 category movements</sup>",
                font=dict(size=18, family="Inter, sans-serif", color="#2C3E50"),
                x=0.5,
                xanchor="center",
                y=0.98,
                yanchor="top",
            ),
            font=dict(family="Inter, sans-serif", size=11, color="#34495E"),
            height=1200,
            margin=dict(l=120, r=100, t=160, b=80),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )

        # 7. Configure X and Y Axes
        fig.update_xaxes(
            title_text="YoY % Change",
            range=[0, 120],
            showgrid=True,
            gridcolor="#E5E8E8",
            zeroline=True,
            zerolinecolor="#2C3E50",
            zerolinewidth=1.5,
        )

        fig.update_yaxes(showticklabels=True, tickfont=dict(size=9), showgrid=False)

        return fig

    def gen_graphs_plate(self):
        df = self.gen_nuti_data()
        df = df.group_by(["fiscal_year"]).agg(
            pl.col(
                "total_calories",
                "protein",
                "vegetable",
                "dairy",
                "fruits",
                "grains",
                "ice_cream",
                "fats",
                "sugars",
                "other",
            ).sum()
        )
        df = df.with_columns(
            protein=pl.col("protein") / pl.col("total_calories"),
            vegetable=pl.col("protein") / pl.col("total_calories"),
            dairy=pl.col("dairy") / pl.col("total_calories"),
            fruits=pl.col("fruits") / pl.col("total_calories"),
            grains=pl.col("grains") / pl.col("total_calories"),
            ice_cream=pl.col("ice_cream") / pl.col("total_calories"),
            fats=pl.col("fats") / pl.col("total_calories"),
            sugars=pl.col("sugars") / pl.col("total_calories"),
            other=pl.col("other") / pl.col("total_calories"),
        )

        df = df.with_columns(
            others=pl.col("other")
            + pl.col("ice_cream")
            + pl.col("fats")
            + pl.col("sugars")
        ).drop("ice_cream", "fats", "sugars")

        # Convert Polars DataFrame to Pandas for Plotly processing
        pdf = df.to_pandas()

        # Define categories to plot and clean them up for presentation (Title Case)
        categories = ["protein", "vegetable", "dairy", "fruits", "grains", "other"]
        category_labels = [cat.capitalize() for cat in categories]

        # Sort the fiscal years in descending order (inverted sort)
        fiscal_years = sorted(pdf["fiscal_year"].unique().tolist(), reverse=True)

        # Generate a professional color-blind friendly Viridis color palette mapped to categories
        viridis_colors = px.colors.sample_colorscale("Viridis", len(categories))

        fig = go.Figure()

        # Add traces for each fiscal year
        for i, year in enumerate(fiscal_years):
            row = pdf[pdf["fiscal_year"] == year]
            values = [row[cat].values[0] for cat in categories]

            fig.add_trace(
                go.Pie(
                    labels=category_labels,
                    values=values,
                    name=str(year),
                    visible=(i == 0),  # Show only the first year by default
                    textinfo="label+percent",
                    hoverinfo="label+percent+value",
                    hovertemplate="<b>%{label}</b><br>Share: %{percent}<extra></extra>",
                    marker=dict(
                        colors=viridis_colors,
                        line=dict(color="#FFFFFF", width=2),  # Crisp separation borders
                    ),
                    pull=[
                        0.03 if j == values.index(max(values)) else 0
                        for j in range(len(values))
                    ],
                )
            )

        # Create robust dropdown buttons matching reference style
        buttons = []
        for i, year in enumerate(fiscal_years):
            visibility = [False] * len(fiscal_years)
            visibility[i] = True

            buttons.append(
                dict(
                    label=str(year),
                    method="update",
                    args=[
                        {"visible": visibility},
                        {
                            "title": dict(
                                text=(
                                    f"<b>Puerto Rico Food Plate Proportion Breakdown — Fiscal Year {year}</b><br>"
                                    f"<sup>Comparative annual distribution across major food groups from imported data</sup>"
                                ),
                                font=dict(
                                    size=16, family="Inter, sans-serif", color="#2C3E50"
                                ),
                                x=0.0,
                                xanchor="left",
                                y=0.98,
                                yanchor="top",
                            )
                        },
                    ],
                )
            )

        # Update layout to match reference template styling standards
        fig.update_layout(
            updatemenus=[
                dict(
                    type="dropdown",
                    direction="down",
                    active=0,
                    x=0.0,
                    xanchor="left",
                    y=1.18,
                    yanchor="top",
                    bgcolor="#F8F9F9",
                    bordercolor="#BDC3C7",
                    borderwidth=1,
                    font=dict(family="Inter, sans-serif", size=12, color="#2C3E50"),
                    buttons=buttons,
                )
            ],
            template="plotly_white",
            title=dict(
                text=(
                    f"<b>Puerto Rico Food Plate Proportion Breakdown — Fiscal Year {fiscal_years[0]}</b><br>"
                    f"<sup>Comparative annual distribution across major food groups from imported data</sup>"
                ),
                font=dict(size=16, family="Inter, sans-serif", color="#2C3E50"),
                x=0.0,
                xanchor="left",
                y=0.98,
                yanchor="top",
            ),
            font=dict(family="Inter, sans-serif", size=11, color="#34495E"),
            legend=dict(
                title=dict(text="<b>Food Categories</b>"),
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#E5E8E8",
                borderwidth=1,
                font=dict(family="Inter, sans-serif", size=11, color="#34495E"),
            ),
            height=520,
            margin=dict(l=40, r=150, t=140, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(
                bgcolor="white", font_size=12, font_family="Inter, sans-serif"
            ),
        )

        return fig

    def gen_graphs_local_dist(self) -> alt.VConcatChart:
        # 1. Load dataframes
        df_local = self.gen_nuti_data_local().filter(pl.col("fiscal_year") > 2002)
        df_import = self.gen_nuti_data().drop("net_qty")

        # A robust renaming map that strips out _g, _mg, _iu before adding _kg
        rename_mapping = {}
        for col in df_local.columns:
            if (
                col.startswith("total_")
                and col != "total_calories"
                and not col.endswith("_kg")
            ):
                clean_name = col
                for suffix in ["_g", "_mg", "_iu"]:
                    if clean_name.endswith(suffix):
                        clean_name = clean_name[: -len(suffix)]
                        break
                rename_mapping[col] = f"{clean_name}_kg"

        # 3. Prepare unfiltered full datasets for both top and bottom charts
        df_import_all = df_import.with_columns(pl.lit("Import").alias("source_type"))
        df_local_all = df_local.rename(rename_mapping).with_columns(
            pl.lit("Local").alias("source_type")
        )

        source_df = pl.concat([df_import_all, df_local_all])
        pie_source_df = source_df

        # Extract unique 2-digit HTS prefixes sorted alphabetically/numerically for the dropdown selector
        unique_prefixes = sorted(
            list(
                source_df.select(pl.col("hts_code").cast(pl.String).str.slice(0, 2))
                .unique()
                .to_series()
            )
        )

        if not unique_prefixes:
            unique_prefixes = ["00"]

        # 4. Dynamically find the min and max fiscal years for the slider
        min_year = int(pie_source_df["fiscal_year"].min())
        max_year = int(pie_source_df["fiscal_year"].max())

        # 5. Create bindings: Year slider and HTS 2-digit Chapter dropdown selector
        slider = alt.binding_range(
            min=min_year, max=max_year, step=1, name="Select Year: "
        )
        select_year = alt.selection_point(
            name="fiscal_year", fields=["fiscal_year"], bind=slider, value=max_year
        )

        # Dropdown selection widget for the first 2 digits of HTS code
        hts_dropdown = alt.binding_select(
            options=unique_prefixes, name="HTS Chapter (First 2 Digits): "
        )
        select_chapter = alt.selection_point(
            name="hts_chapter",
            fields=["hts_prefix"],
            bind=hts_dropdown,
            value=[{"hts_prefix": unique_prefixes[0]}],
        )

        # 6. Define a cohesive, professional color palette
        color_scale = alt.Scale(
            domain=["Import", "Local"], range=["#1f4e79", "#2d8a81"]
        )

        # 7. Define the base chart configuration (Shared by bottom charts with 0-imputation)
        base = (
            alt.Chart(source_df)
            .transform_filter(select_year)
            .transform_calculate(
                hts_prefix=alt.expr.slice(alt.expr.toString(alt.datum.hts_code), 0, 2)
            )
            .transform_filter(select_chapter)
            .transform_impute(
                "total_calories",
                key="source_type",
                keyvals=["Import", "Local"],
                value=0,
                groupby=["hts_code", "fiscal_year"],
            )
            .transform_calculate(
                is_local_cal=alt.expr.if_(
                    alt.datum.source_type == "Local", alt.datum.total_calories, 0
                )
            )
            .transform_joinaggregate(
                global_local_calories="sum(is_local_cal)",
                hts_total="sum(total_calories)",
                groupby=["hts_code", "fiscal_year"],
            )
            .transform_joinaggregate(
                source_hts_total="sum(total_calories)",
                groupby=["hts_code", "source_type", "fiscal_year"],
            )
            .transform_calculate(
                pct=alt.expr.if_(
                    alt.datum.hts_total > 0,
                    alt.datum.source_hts_total / alt.datum.hts_total,
                    0,
                )
            )
        )

        # Shared sorting logic for bottom breakdown
        y_sort_axis = alt.Y("hts_code:O").sort(
            field="global_local_calories", op="max", order="descending"
        )

        # ==========================================
        # TOP CHART (Pie Chart with 0-fill logic)
        # ==========================================
        top_base = (
            alt.Chart(pie_source_df)
            .transform_filter(select_year)
            .transform_aggregate(
                source_total_calories="sum(total_calories)",
                groupby=["fiscal_year", "source_type"],
            )
            .transform_impute(
                "source_total_calories",
                key="source_type",
                keyvals=["Import", "Local"],
                value=0,
                groupby=["fiscal_year"],
            )
            .transform_joinaggregate(
                grand_total_calories="sum(source_total_calories)",
                groupby=["fiscal_year"],
            )
            .transform_calculate(
                pie_pct=alt.expr.if_(
                    alt.datum.grand_total_calories > 0,
                    alt.datum.source_total_calories / alt.datum.grand_total_calories,
                    0,
                )
            )
            .encode(
                theta=alt.Theta("source_total_calories:Q").stack(True),
                color=alt.Color("source_type:N")
                .scale(color_scale)
                .legend(orient="top", title="Source Type"),
            )
        )

        top_pie = top_base.mark_arc(outerRadius=80).encode(
            tooltip=[
                alt.Tooltip("source_type:N", title="Source"),
                alt.Tooltip(
                    "source_total_calories:Q", title="Total Calories", format="~s"
                ),
                alt.Tooltip("pie_pct:Q", title="Market Share", format=".1%"),
            ]
        )

        top_labels = top_base.mark_text(
            radius=110,
            font="Arial",
            fontSize=11,
            fontWeight="bold",
            color="#333333",
        ).encode(text=alt.Text("pie_pct:Q", format=".1%"))

        top_chart = alt.layer(top_pie, top_labels).properties(
            width=640,
            height=240,
            title=alt.TitleParams(
                "Total Market Share Breakdown (All Data Sources Combined)",
                anchor="start",
                font="Arial",
                fontSize=13,
                color="#333333",
            ),
        )

        # ==========================================
        # BOTTOM ROW: Side-by-Side Split Charts
        # ==========================================
        scrollable_height = alt.Step(20)

        # Left Chart: Import data
        left_base = base.transform_filter(alt.datum.source_type == "Import").properties(
            width=280, height=scrollable_height
        )

        left_bars = left_base.encode(
            y=y_sort_axis.axis(None),
            x=alt.X("sum(total_calories):Q")
            .title("Total Calories")
            .sort("descending")
            .axis(format="~s", grid=True, labelExpr="replace(datum.label, 'G', 'B')"),
            color=alt.Color("source_type:N").scale(color_scale).legend(None),
        ).mark_bar()

        left_text = left_base.encode(
            y=y_sort_axis.axis(None),
            x=alt.X("sum(total_calories):Q").sort("descending"),
            text=alt.Text("max(pct):Q", format=".1%"),
        ).mark_text(
            dx=-8,
            align="right",
            baseline="middle",
            font="Arial",
            fontSize=10,
            fontWeight="bold",
            color="#333333",
        )

        left = alt.layer(left_bars, left_text).properties(
            title=alt.TitleParams(
                "Imported Calories Contribution",
                anchor="end",
                font="Arial",
                fontSize=13,
                color="#333333",
            ),
            height=400,
        )

        # Middle Chart: Centralized HTS Code Text Labels
        middle = (
            base.transform_aggregate(
                global_local_calories="max(global_local_calories)",
                groupby=["hts_code"],
            )
            .encode(
                y=y_sort_axis.axis(None),
                text=alt.Text("hts_code:O"),
            )
            .mark_text(font="Arial", fontSize=11, color="#555555")
            .properties(width=60, height=scrollable_height)
        )

        middle_container = alt.layer(middle).properties(height=400)

        # Right Chart: Local data
        right_base = base.transform_filter(alt.datum.source_type == "Local").properties(
            width=280, height=scrollable_height
        )

        right_bars = right_base.encode(
            y=y_sort_axis.axis(None),
            x=alt.X("sum(total_calories):Q")
            .title("Total Calories")
            .axis(format="~s", grid=True, labelExpr="replace(datum.label, 'G', 'B')"),
            color=alt.Color("source_type:N").scale(color_scale).legend(None),
        ).mark_bar()

        right_text = right_base.encode(
            y=y_sort_axis.axis(None),
            x=alt.X("sum(total_calories):Q"),
            text=alt.Text("max(pct):Q", format=".1%"),
        ).mark_text(
            dx=8,
            align="left",
            baseline="middle",
            font="Arial",
            fontSize=10,
            fontWeight="bold",
            color="#333333",
        )

        right = alt.layer(right_bars, right_text).properties(
            title=alt.TitleParams(
                "Local Calories Contribution",
                anchor="start",
                font="Arial",
                fontSize=13,
                color="#333333",
            ),
            height=400,
        )

        bottom_row = alt.hconcat(left, middle_container, right, spacing=10)

        # ==========================================
        # FINAL CONCATENATION & STYLING
        # ==========================================
        chart = (
            alt.vconcat(top_chart, bottom_row, spacing=30)
            .add_params(select_year, select_chapter)
            .properties(
                title=alt.TitleParams(
                    text="Caloric Distribution Analysis",
                    subtitle=[
                        "Overall combined distribution (top) compared with localized and imported breakdowns (bottom).",
                        "Use the scroll wheel on the bottom charts to explore extensive HTS code chapters.",
                    ],
                    fontSize=16,
                    anchor="middle",
                    font="Arial",
                    subtitleColor="#666666",
                )
            )
            .configure_view(stroke=None)
            .configure_axis(
                domain=False,
                ticks=False,
                labelFont="Arial",
                titleFont="Arial",
                titleColor="#444444",
            )
        )

        return chart

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
