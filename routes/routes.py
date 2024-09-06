from pathlib import Path

from flask import Blueprint, abort, current_app, json, jsonify, render_template, request

from charts import get_energy_timeseries_chart_div
from fetch_timeseries_data import fetch_timeseries_data
from process_energy_data import get_energy_category_map
from process_fiscal_data import get_country_list, get_net_value_country
from utils.converter_utils import get_macronutrients

routes = Blueprint('my_routes', __name__)


@routes.route('/nutrient_distribution', methods=['GET'])
def nutrient_distribution():
    current_dir = Path(__file__).parent.resolve()
    fp = current_dir / ".." / "data/plate/nutrient_distribution_yearly.json"
    try:
        with open(fp, 'r') as f:
            data = json.load(f)
            return jsonify(data)
    except FileNotFoundError:
        current_app.logger.error('Nutrient data not found')
        current_app.logger.error(str(Path(fp).resolve()))
        abort(404)  # Return a 404 error if the file is not found


@routes.route('/get_fiscal_data_country', methods=['GET'])
def get_fiscal_data_country():
    country = request.args.get('country', default="United States", type=str)

    try:
        data = get_net_value_country(country)
    except KeyError as err:
        return jsonify({'error': str(err)}), 400

    return jsonify(data)


@routes.route('/get_fiscal_country_list', methods=['GET'])
def get_fiscal_country_list():
    return jsonify(get_country_list())


@routes.route('/get_macronutrient_list', methods=['GET'])
def get_macronutrient_list():
    return jsonify(get_macronutrients())


@routes.route('/get_energy_chart', methods=['GET'])
def get_energy_chart():
    try:
        selected_category = request.args.get("category", type=str)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid category.'}), 400

    if not selected_category:
        return jsonify({'error': 'Please provide a selected category'}), 400

    try:
        div = get_energy_timeseries_chart_div(selected_category)
    except KeyError:
        return jsonify({'error': 'Invalid category.'}), 400

    return div


@routes.route('/get_energy_categories', methods=['GET'])
def get_energy_categories():
    return jsonify(get_energy_category_map())
