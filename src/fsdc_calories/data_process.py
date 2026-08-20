import importlib.resources as resources
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Literal
import plotly.graph_objects as go
import plotly.express as px

from plotly.subplots import make_subplots
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

    def gen_graphs_nuti_data(self) -> go.Figure:
        """Generates an interactive Plotly line chart tracking imported nutritional metrics over time."""
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

        fig = go.Figure()

        if data.empty:
            fig.update_layout(
                title="No data available",
                template="plotly_white",
                font=dict(family="Inter, sans-serif", size=12, color="#2C3E50"),
            )
            return fig

        metrics = list(column_label_map.keys())
        default_metric = metrics[0]
        default_metric_label = column_label_map[default_metric]

        # 1. Add traces for each metric (only the first visible by default)
        for i, metric in enumerate(metrics):
            metric_label = column_label_map[metric]
            fig.add_trace(
                go.Scatter(
                    x=data["datetime"],
                    y=data[metric],
                    mode="lines+markers",
                    name=metric_label,
                    line=dict(color="#1f77b4", width=2.5, shape="spline"),
                    marker=dict(size=6, color="#1f77b4"),
                    hovertemplate=(
                        "<b>Date:</b> %{x|%B %Y}<br>"
                        f"<b>{metric_label}:</b> %{{y:,.2f}}<br>"
                        "<extra></extra>"
                    ),
                    visible=(i == 0),
                )
            )

        # 2. Build dropdown menu buttons
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
                                    f"<b>Imported Nutritional Intake Over Time</b><br>"
                                    f"<sup>Showing {metric_label}. Select an imported nutrient from the dropdown menu above.</sup>"
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

        # 3. Configure layout standard matching price volatility structure
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
                    f"<b>Imported Nutritional Intake Over Time</b><br>"
                    f"<sup>Showing {default_metric_label}. Select an imported nutrient from the dropdown menu above.</sup>"
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
                bgcolor="#FFFFFF",
                bordercolor="#BDC3C7",
                font=dict(family="Inter, sans-serif", size=12, color="#2C3E50"),
            ),
            showlegend=False,
        )

        # 4. Configure Axes
        fig.update_xaxes(title_text="Date", showgrid=False, tickformat="%b %Y")

        fig.update_yaxes(
            title_text=default_metric_label,
            showgrid=True,
            gridcolor="#E0E0E0",
            griddash="dot",
            zeroline=True,
            zerolinecolor="#2C3E50",
            zerolinewidth=1,
        )

        return fig

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

    def gen_graphs_price_change(self) -> go.Figure:
        """Generates a bar chart showing the largest price changes

        (top 30 increases & bottom 50 decreases) for Imports,
        with dropdowns for Top/Bottom categories and the last 4 quarters.

        Returns:
            go.Figure: Plotly figure with multi-dropdown support.
        """
        df = self.process_price(agriculture_filter=True)
        path_data = str(
            resources.files("fsdc_calories").joinpath("data/hts4_walk.parquet")
        )

        desc_df = pl.read_parquet(path_data).rename(
            {"code_4": "hs4", "Description": "hts_desc"}
        )
        df = df.join(desc_df, on="hs4", how="inner", validate="m:1")

        # 1. Get the last 4 unique dates (quarters) sorted chronologically
        all_dates = df.select("date").unique().sort("date")["date"].to_list()
        last_4_dates = all_dates[-4:] if len(all_dates) >= 4 else all_dates

        fig = go.Figure()

        # Enhanced hover template
        hover_template = (
            "<b>Description:</b> %{y}<br>"
            "<b>HS4 Code:</b> %{customdata[0]}<br>"
            "<b>Price Imports YoY:</b> %{customdata[1]:.1f}%<br>"
            "<extra></extra>"
        )

        trace_counter = 0
        date_trace_indices = {} 

        for d_idx, target_date in enumerate(last_4_dates):
            # Filter data and shorten descriptions further for mobile screens (3 words max)
            quarter_data = (
                df.filter(pl.col("date") == target_date)
                .with_columns(
                    actual_yoy=pl.col("price_imports_yoy"),
                    plot_yoy=pl.col("price_imports_yoy").clip(-100, 100),
                    text_label=(
                        pl.col("price_imports_yoy").round(1).cast(pl.Utf8) + "%"
                    ).str.replace(r"^([0-9])", r"+$1"),
                    short_desc=(
                        pl.col("hts_desc").str.split(" ").list.head(3).list.join(" ")
                        + pl.when(pl.col("hts_desc").str.split(" ").list.len() > 3)
                        .then(pl.lit("..."))
                        .otherwise(pl.lit(""))
                    ),
                )
                .with_columns(
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

            top_data = (
                quarter_data.sort("actual_yoy", descending=True)
                .head(50)
                .to_pandas()
                .iloc[::-1]
            )

            bottom_data = (
                quarter_data.sort("actual_yoy", descending=False)
                .head(50)
                .to_pandas()
                .iloc[::-1]
            )

            # Top Trace
            fig.add_trace(
                go.Bar(
                    x=top_data["plot_yoy"],
                    y=top_data["short_desc"],
                    text=top_data["text_label"],
                    textposition="outside",
                    orientation="h",
                    customdata=list(zip(top_data["hs4"], top_data["actual_yoy"])),
                    hovertemplate=hover_template,
                    marker=dict(
                        color=top_data["plot_yoy"],
                        colorscale="Viridis",
                        showscale=False,
                        opacity=0.9,
                    ),
                    visible=(d_idx == len(last_4_dates) - 1), 
                )
            )
            top_idx = trace_counter
            trace_counter += 1

            # Bottom Trace
            fig.add_trace(
                go.Bar(
                    x=bottom_data["plot_yoy"],
                    y=bottom_data["short_desc"],
                    text=bottom_data["text_label"],
                    textposition="outside",
                    orientation="h",
                    customdata=list(zip(bottom_data["hs4"], bottom_data["actual_yoy"])),
                    hovertemplate=hover_template,
                    marker=dict(
                        color=bottom_data["plot_yoy"],
                        colorscale="Viridis_r",
                        showscale=False,
                        opacity=0.9,
                    ),
                    visible=False,
                )
            )
            bottom_idx = trace_counter
            trace_counter += 1

            date_trace_indices[target_date] = {"top": top_idx, "bottom": bottom_idx}

        total_traces = trace_counter
        top_btn_visibility = [False] * total_traces
        bottom_btn_visibility = [False] * total_traces

        latest_date = last_4_dates[-1]
        top_btn_visibility[date_trace_indices[latest_date]["top"]] = True
        bottom_btn_visibility[date_trace_indices[latest_date]["bottom"]] = True

        metric_buttons = [
            dict(
                label="Top 50 Categories",
                method="update",
                args=[
                    {"visible": top_btn_visibility},
                    {"xaxis.range": [0, 120], "xaxis.title_text": "YoY % Change"},
                ],
            ),
            dict(
                label="Bottom 50 Categories",
                method="update",
                args=[
                    {"visible": bottom_btn_visibility},
                    {"xaxis.range": [-120, 0], "xaxis.title_text": "YoY % Change"},
                ],
            ),
        ]

        quarter_buttons = []
        for target_date in last_4_dates:
            date_str = str(target_date)
            q_top_vis = [False] * total_traces
            q_bot_vis = [False] * total_traces
            
            q_top_vis[date_trace_indices[target_date]["top"]] = True
            q_bot_vis[date_trace_indices[target_date]["bottom"]] = True

            quarter_buttons.append(
                dict(
                    label=f"Quarter: {date_str}",
                    method="update",
                    args=[
                        {"visible": q_top_vis}, 
                        {"xaxis.range": [0, 120], "xaxis.title_text": "YoY % Change"},
                    ],
                )
            )

        # Mobile-Optimized Layout Settings
        fig.update_layout(
            updatemenus=[
                # Dropdown 1: Stacked cleanly at the top-left
                dict(
                    type="dropdown",
                    direction="down",
                    x=0.0,
                    xanchor="left",
                    y=1.35,
                    yanchor="top",
                    bgcolor="#F8F9F9",
                    bordercolor="#BDC3C7",
                    borderwidth=1,
                    font=dict(size=10, color="#2C3E50"),
                    buttons=metric_buttons,
                ),
                # Dropdown 2: Stacked directly below the first dropdown for mobile viewports
                dict(
                    type="dropdown",
                    direction="down",
                    x=0.0,
                    xanchor="left",
                    y=1.20,
                    yanchor="top",
                    bgcolor="#F8F9F9",
                    bordercolor="#BDC3C7",
                    borderwidth=1,
                    font=dict(size=10, color="#2C3E50"),
                    buttons=quarter_buttons,
                ),
            ],
            template="plotly_white",
            title=dict(
                text="<b>Import Price Volatility</b><br><sup>YoY Changes by Category</sup>",
                font=dict(size=14, color="#2C3E50"),
                x=0.5,
                xanchor="center",
                y=0.98,
                yanchor="top",
            ),
            font=dict(size=10, color="#34495E"),
            height=850,  # Reduced height to fit smaller screens better
            margin=dict(l=100, r=50, t=240, b=50), # Adjusted margins for mobile constraints
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )

        fig.update_xaxes(
            title_text="YoY % Change",
            range=[0, 120],
            showgrid=True,
            gridcolor="#E5E8E8",
            zeroline=True,
            zerolinecolor="#2C3E50",
        )

        fig.update_yaxes(showticklabels=True, tickfont=dict(size=8), showgrid=False)

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

    def gen_graphs_local_dist(self) -> go.Figure:
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

        # 3. Prepare unfiltered full datasets
        df_import_all = df_import.with_columns(source_type=pl.lit("Import")).drop(
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
        df_local_all = df_local.rename(rename_mapping).with_columns(
            source_type=pl.lit("Local")
        )

        source_df = pl.concat([df_import_all, df_local_all])

        # Add HTS prefix column for filtering
        source_df = source_df.with_columns(
            pl.col("hts_code").cast(pl.String).str.slice(0, 2).alias("hts_prefix")
        )

        unique_prefixes = sorted(
            list(source_df.select("hts_prefix").unique().to_series())
        )
        if not unique_prefixes:
            unique_prefixes = ["00"]

        min_year = int(source_df["fiscal_year"].min())
        max_year = int(source_df["fiscal_year"].max())
        years = sorted(list(source_df["fiscal_year"].unique()))

        # 4. Initialize Plotly Subplots
        # Row 1: Pie Chart (specs type domain)
        # Row 2: 3 columns (Import Bar, HTS Labels, Local Bar)
        fig = make_subplots(
            rows=2,
            cols=3,
            specs=[
                [{"type": "domain", "colspan": 3}, None, None],
                [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
            ],
            row_heights=[0.35, 0.65],
            subplot_titles=(
                "Total Market Share Breakdown",
                "Imported Calories",
                "",
                "Local Calories",
            ),
            vertical_spacing=0.15,
            horizontal_spacing=0.05,
        )

        # Color mapping
        colors = {"Import": "#1f4e79", "Local": "#2d8a81"}

        # We will build traces dynamically per Year & HTS Chapter combination to support interactive dropdowns/sliders
        # Or create frames/visibility arrays. Given standard Plotly setups for dropdowns over dataframes,
        # filtering data beforehand or building multi-trace visibility combinations works best.

        # For a clean implementation, let's pre-aggregate or setup default view (e.g., max_year and first hts_prefix)
        default_year = max_year
        default_chapter = unique_prefixes[0]

        # Helper function to filter and aggregate data for a given year & chapter
        def get_filtered_data(year, chapter):
            f_df = source_df.filter(
                (pl.col("fiscal_year") == year) & (pl.col("hts_prefix") == chapter)
            )
            return f_df

        # Let's generate traces for combinations or use interactive dropdown buttons that update data.
        # To keep code clean and performant, we'll build frames or predefined traces for the dropdown filters.

        # For demonstration with current state matching your logic:
        initial_pie_df = (
            source_df.filter(pl.col("fiscal_year") == default_year)
            .group_by("source_type")
            .agg(pl.col("total_calories").sum().alias("source_total"))
        )

        # 5. Add default Pie Chart trace (Row 1)
        fig.add_trace(
            go.Pie(
                labels=initial_pie_df["source_type"].to_list(),
                values=initial_pie_df["source_total"].to_list(),
                marker=dict(
                    colors=[
                        colors.get(x, "#333") for x in initial_pie_df["source_type"]
                    ]
                ),
                name="Market Share",
                domain=dict(row=0, column=0),
            ),
            row=1,
            col=1,
        )

        # 6. Process Bottom Row data (Import, Labels, Local) for default view
        bottom_data = get_filtered_data(default_year, default_chapter)

        # Aggregate to find total per hts_code and source type
        agg_bottom = bottom_data.group_by(["hts_code", "source_type"]).agg(
            pl.col("total_calories").sum()
        )

        # Pivot or split into Import and Local for side-by-side
        import_sub = agg_bottom.filter(pl.col("source_type") == "Import").sort(
            "total_calories"
        )
        local_sub = agg_bottom.filter(pl.col("source_type") == "Local").sort(
            "total_calories"
        )

        # Import Bar Chart (Row 2, Col 1 - Right-aligned / pointing left or standard horizontal bar)
        fig.add_trace(
            go.Bar(
                x=import_sub["total_calories"].to_list(),
                y=import_sub["hts_code"].cast(pl.String).to_list(),
                orientation="h",
                marker=dict(color=colors["Import"]),
                name="Import",
            ),
            row=2,
            col=1,
        )

        # Middle HTS Labels (Row 2, Col 2)
        unique_hts = sorted(list(agg_bottom["hts_code"].unique().to_list()))
        fig.add_trace(
            go.Scatter(
                x=[0] * len(unique_hts),
                y=unique_hts,
                mode="text",
                text=unique_hts,
                textfont=dict(size=10, color="#555555"),
                showlegend=False,
            ),
            row=2,
            col=2,
        )

        # Local Bar Chart (Row 2, Col 3)
        fig.add_trace(
            go.Bar(
                x=local_sub["total_calories"].to_list(),
                y=local_sub["hts_code"].cast(pl.String).to_list(),
                orientation="h",
                marker=dict(color=colors["Local"]),
                name="Local",
            ),
            row=2,
            col=3,
        )

        # 7. Layout and Theme Configuration
        fig.update_layout(
            title=dict(
                text="<b>Caloric Distribution Analysis</b><br><sup>Overall combined distribution compared with localized and imported breakdowns.</sup>",
                x=0.5,
                xanchor="center",
                font=dict(family="Arial", size=16, color="#333333"),
            ),
            template="plotly_white",
            height=700,
            margin=dict(l=80, r=80, t=120, b=80),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        )

        # Axis cleanups
        fig.update_xaxes(showgrid=True, gridcolor="#E5E8E8")
        fig.update_yaxes(showgrid=False, showticklabels=False, row=2, col=1)
        fig.update_yaxes(showgrid=False, showticklabels=False, row=2, col=2)
        fig.update_yaxes(
            showgrid=False, showticklabels=True, row=2, col=3, side="right"
        )

        return fig

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
