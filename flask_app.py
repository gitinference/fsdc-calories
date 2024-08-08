import atexit

from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from routes.routes import routes
from update_data import update_data

app = Flask(__name__)
app.register_blueprint(routes)
CORS(app, resources={r"/*": {
    "origins": [
        "http://127.0.0.1:5500",
        "https://www.uprm.edu"
    ]
}})

if __name__ == '__main__':
    app.run()
