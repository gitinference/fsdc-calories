from flask import Blueprint, jsonify

routes = Blueprint('my_routes', __name__)


@routes.route('/route1', methods=['GET'])
def route1():
    return jsonify({"message": "This is route 1"})


@routes.route('/route2', methods=['GET'])
def route2():
    return jsonify({"message": "This is route 2"})
