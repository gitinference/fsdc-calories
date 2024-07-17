from flask import Blueprint, jsonify, send_file, abort, current_app, request, json, render_template
from werkzeug.security import safe_join
from charts import generate_timeseries_chart

routes = Blueprint('my_routes', __name__)


@routes.route('/')
def home():
    return render_template('index.html')


@routes.route('/nutrient_distribution', methods=['GET'])
def nutrient_distribution():
    try:
        with open('data/plate/nutrient_distribution_yearly.json', 'r') as f:
            data = json.load(f)
            return jsonify(data)
    except FileNotFoundError:
        current_app.logger.error('Nutrient data not found')
        abort(404)  # Return a 404 error if the file is not found


@routes.route('/get_timeseries_chart', methods=['GET'])
def get_timeseries_chart():
    tseries_start = int(request.args.get('start_year'))
    tseries_end = int(request.args.get('end_year'))
    macronutrient = request.args.get('macronutrient')

    if not tseries_start or not tseries_end:
        return jsonify({'error': 'Please provide start and end years'}), 400

    plot = generate_timeseries_chart(tseries_start, tseries_end, macronutrient)

    return send_file(plot, mimetype='image/png', as_attachment=True, download_name='timeseries_chart.png')
