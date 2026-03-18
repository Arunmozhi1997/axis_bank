from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Axis Bank ML Recommendation API Running"}