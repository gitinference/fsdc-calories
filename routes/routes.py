from pathlib import Path

from flask import abort, Blueprint, current_app, json, jsonify, render_template, request

from src.charts import (
    get_energy_timeseries_chart_div,
    get_fiscal_timeseries_chart_div,
    get_macronutrient_timeseries_chart_div,
    get_product_price_ranking_timeseries_div,
)
from src.process_energy_data import get_energy_category_map
from src.process_fiscal_data import get_country_list, get_net_value_country
from utils.converter_utils import ConverterUtils

routes = Blueprint("my_routes", __name__)

# Create ConverterUtils
cur_dir = Path(__file__).parent.resolve()
reference_file_path = str(cur_dir / ".." / "data" / "schedule_b_reference.xlsx")
utils = ConverterUtils(reference_file_path)

""" MY PLATE ROUTES """


@routes.route("/nutrient_distribution", methods=["GET"])
def nutrient_distribution():
    current_dir = Path(__file__).parent.resolve()
    fp = current_dir / ".." / "data/plate/nutrient_distribution_yearly.json"
    try:
        with open(fp, "r") as f:
            data = json.load(f)
            return jsonify(data)
    except FileNotFoundError:
        current_app.logger.error("Nutrient data not found")
        current_app.logger.error(str(Path(fp).resolve()))
        abort(404)  # Return a 404 error if the file is not found


""" FISCAL ROUTES """


@routes.route("/get_fiscal_chart", methods=["GET"])
def get_fiscal_chart():
    country = request.args.get("country", default="United States", type=str)
    try:
        div = get_fiscal_timeseries_chart_div(country)
    except KeyError as err:
        return jsonify({"error": str(err)}), 400
    return div


@routes.route("/get_fiscal_country_list", methods=["GET"])
def get_fiscal_country_list():
    return jsonify(get_country_list())


""" MACRONUTRIENT ROUTES """


@routes.route("/get_macronutrient_chart")
def get_macronutrient_chart():
    category = request.args.get("category", default="calories", type=str)
    try:
        div = get_macronutrient_timeseries_chart_div(category)
    except KeyError as err:
        return jsonify({"error": str(err)}), 400
    return div


@routes.route("/get_macronutrient_list", methods=["GET"])
def get_macronutrient_list():
    return jsonify(utils.get_macronutrients())


""" ENERGY ROUTES """


@routes.route("/get_energy_chart", methods=["GET"])
def get_energy_chart():
    try:
        selected_category = request.args.get("category", type=str)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid category."}), 400

    if not selected_category:
        return jsonify({"error": "Please provide a selected category"}), 400

    try:
        div = get_energy_timeseries_chart_div(selected_category)
    except KeyError:
        return jsonify({"error": "Invalid category."}), 400

    return div


@routes.route("/get_energy_categories", methods=["GET"])
def get_energy_categories():
    return jsonify(get_energy_category_map())


""" PRICE ROUTES """


@routes.route("/get_price_chart", methods=["GET"])
def get_price_chart():
    div = get_product_price_ranking_timeseries_div()
    return div


""" CHART ROUTES """


@routes.route("/charts", methods=["GET"])
def get_all_charts_render_template():
    return render_template("charts.html")


@routes.route("/charts/macronutrients", methods=["GET"])
def get_macronutrient_chart_render_template():
    return render_template("macronutrient_chart.html")


@routes.route("/charts/price_ranking", methods=["GET"])
def get_price_ranking_chart_render_template():
    return render_template("product_prices.html")


@routes.route("/charts/energy", methods=["GET"])
def get_energy_indices_chart_render_template():
    return render_template("energy_chart.html")


@routes.route("/charts/plate", methods=["GET"])
def get_plate_chart_render_template():
    return render_template("my_plate.html")
