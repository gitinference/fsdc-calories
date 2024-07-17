import atexit

from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from routes.routes import routes
from update_data import update_data

from logging.config import dictConfig

# dictConfig({
#     'version': 1,
#     'formatters': {'default': {
#         'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
#     }},
#     'handlers': {'wsgi': {
#         'class': 'logging.StreamHandler',
#         'stream': 'ext://flask.logging.wsgi_errors_stream',
#         'formatter': 'default'
#     }},
#     'root': {
#         'level': 'INFO',
#         'handlers': ['wsgi']
#     }
# })

app = Flask(__name__)
app.register_blueprint(routes)
# CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:5500"}})

# cron = BackgroundScheduler(daemon=True)
# cron.add_job(update_data, 'interval', seconds=5)
# cron.start()

# atexit.register(lambda: cron.shutdown(wait=False))

if __name__ == '__main__':
    app.run()
