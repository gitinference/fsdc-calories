from flask import Blueprint, jsonify, send_file, abort, current_app
from werkzeug.security import safe_join

routes = Blueprint('my_routes', __name__)


@routes.route('/nutrient_distribution/<year>', methods=['GET'])
def nutrient_distribution(year):

    current_app.logger.info(f'nutrient distribution for {year}')

    # Define the directory containing the files
    directory = 'charts/plate'

    try:
        # Securely join the directory and filename
        file_path = safe_join(directory, str(year) + ".png")

        # Send the file to the client
        return send_file(file_path, as_attachment=True)
    except FileNotFoundError:
        abort(404)  # Return a 404 error if the file is not found


@routes.route('/route2', methods=['GET'])
def route2():
    return jsonify({"message": "This is route 2"})
