# FOR FASTAPI: -k uvicorn.workers.UvicornWorker

from flask_app import app

if __name__ == '__main__':
    app.run()