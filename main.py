from fastapi import FastAPI
from pydantic import BaseModel

import boto3
from botocore.exceptions import NoCredentialsError

from predict_dog_breed import process_data

app = FastAPI(title="Dog Breed Prediction API")

s3_client = boto3.client('s3', region_name='us-east-1')
BUCKET_NAME = 'dog-img-bucket1'

class ProcessRequest(BaseModel):
    image_path: str
    top_k: int = 3

@app.get("/")
def home():
    return {"message": "API is running!"}

@app.post("/run-prediction")
def run_prediction(payload: ProcessRequest):
    output = process_data(image_path=payload.image_path, top_k=payload.top_k)
    return output

@app.post("/upload-image")
def upload_image(object_name: str):

    url = s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": object_name
        },
        ExpiresIn=300
    )

    return {
        "upload_url": url,
        "object_name": object_name
    }
