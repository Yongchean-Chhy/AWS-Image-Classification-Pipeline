from fastapi import FastAPI
from pydantic import BaseModel

from predict_dog_breed import process_data

app = FastAPI(title="Dog Breed Prediction API")

class ProcessRequest(BaseModel):
    image_path: str
    top_k: int = 3

@app.get("/")
def home():
    return {"message": "API is running!"}

@app.post("/run-script")
def run_script(payload: ProcessRequest):
    output = process_data(image_path=payload.image_path, top_k=payload.top_k)
    return output

