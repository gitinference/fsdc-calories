from flask import Blueprint, jsonify, send_file, abort, current_app, request, json, render_template
from pathlib import Path
from werkzeug.security import safe_join
from charts import generate_timeseries_chart

routes = Blueprint('my_routes', __name__)


@routes.route('/')
def home():
    return render_template('index.html')


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


@routes.route('/get_timeseries_chart', methods=['GET'])
def get_timeseries_chart():
    try:
        tseries_start = int(request.args.get('start_year'))
        tseries_end = int(request.args.get('end_year'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Please provide valid start and end years'}), 400

    macronutrient = request.args.get('macronutrient')

    if not macronutrient:
        return jsonify({'error': 'Please provide a valid macronutrient'}), 400

    # TODO Refactor to offload graph generation to frontend
    plot = generate_timeseries_chart(tseries_start, tseries_end, macronutrient)
    return send_file(plot, mimetype='image/png', as_attachment=True, download_name='timeseries_chart.png')
