from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "It's working!"}

# FOR FASTAPI: -k uvicorn.workers.UvicornWorker

# from flask_app import app