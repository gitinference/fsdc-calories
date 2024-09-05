from flask import Flask
from flask_cors import CORS

from routes.routes import routes
from update_data import update_data

app = Flask(__name__)
app.register_blueprint(routes)
CORS(app, resources={r"/*": {
    "origins": [
        "http://127.0.0.1:5000",  # Werkzeug WSGI Development Server
        "http://localhost:5000",  # Werkzeug WSGI Development Server
        "http://localhost:63342",  # PyCharm HTML Live Server
        "https://www.uprm.edu"
    ]
}})
