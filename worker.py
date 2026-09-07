import json
import boto3
import tempfile
import os

import torch
from PIL import Image
from torchvision import models

import mysql.connector
from datetime import datetime, timezone


# =========================
# AWS configuration
# =========================

REGION = "us-east-1"

QUEUE_URL = (
    "https://sqs.us-east-1.amazonaws.com/967618590980/dog-image-processing"
)

s3_client = boto3.client(
    "s3",
    region_name=REGION
)

sqs_client = boto3.client(
    "sqs",
    region_name=REGION
)


# Load model

weights = models.ResNet50_Weights.DEFAULT
model = models.resnet50(
    weights=weights
)
model.eval()
preprocess = weights.transforms()
labels = weights.meta["categories"]

# RDS configuration

DB_HOST = os.environ["DB_HOST"]              
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_NAME = os.environ.get("DB_NAME", "dog_classifier")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ["DB_PASSWORD"]

CREATE_TABLE_QUERY = """
    CREATE TABLE IF NOT EXISTS predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        image_key VARCHAR(500) NOT NULL,
        predicted_label VARCHAR(255) NOT NULL,
        confidence FLOAT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

INSERT_QUERY = """
    INSERT INTO predictions (image_key, predicted_label, confidence, timestamp)
    VALUES (%s, %s, %s, %s)
"""

db_conn = None

def get_db_connection():
    global db_conn
 
    if db_conn is not None:
        try:
            with db_conn.cursor() as cur:
                cur.execute("SELECT 1;")
            return db_conn
        except Exception:
            print("Existing DB connection is stale, reconnecting...")
            try:
                db_conn.close()
            except Exception:
                pass
            db_conn = None
 
    print("Connecting to RDS...")
    db_conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10,
    )
    db_conn.autocommit = True
 
    with db_conn.cursor() as cur:
        cur.execute(CREATE_TABLE_QUERY)
 
    print("Connected to RDS")
    return db_conn

def save_prediction(image_key, label, confidence):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            INSERT_QUERY,
            (
                image_key,
                label,
                confidence,
                datetime.now(timezone.utc),
            ),
        )
    print(f"Saved prediction to RDS: {image_key} -> {label} ({confidence:.4f})")

def check_db_entry():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM predictions;")
        count = cur.fetchone()[0]
        print(f"Total entries in predictions table: {count}")

        cur.execute(
            "SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 5;"
        )
        rows = cur.fetchall()
        for row in rows:
            print(row)  
# =========================
# Run inference
# =========================

def run_inference(image_path):
    image = Image.open(image_path).convert("RGB")
    input_tensor = preprocess(image)
    input_batch = input_tensor.unsqueeze(0)
    with torch.no_grad():
        output = model(input_batch)

    probabilities = torch.nn.functional.softmax(
        output[0],
        dim=0
    )

    top_probabilities, top_indices = torch.topk(
        probabilities,
        3
    )

    predictions = []

    for probability, index in zip(
        top_probabilities,
        top_indices
    ):
        predictions.append({
            "label": labels[index.item()],
            "probability": probability.item()
        })

    return predictions


# Process SQS message

def process_message(message):

    print("Received SQS message")

    print("Raw message:")
    print(message["Body"])

    body = json.loads(message["Body"])

    if body.get("Event") == "s3:TestEvent":
        print("Ignoring S3 test event")

        sqs_client.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=message["ReceiptHandle"]
        )
        return

    if "Records" not in body:
        print("Unknown SQS message format. Skipping.")
        return

    record = body["Records"][0]

    bucket = record["s3"]["bucket"]["name"]

    key = record["s3"]["object"]["key"]

    print(f"S3 bucket: {bucket}")
    print(f"S3 key: {key}")

    # Download image

    with tempfile.NamedTemporaryFile(
        suffix=".jpg",
        delete=False
    ) as temp_file:
        image_path = temp_file.name

    try:

        print("Downloading image...")

        s3_client.download_file(
            bucket,
            key,
            image_path
        )

        print("Download complete")

        # Run inference
     
        print("Running inference...")

        predictions = run_inference(
            image_path
        )

        print("Predictions:")

        for prediction in predictions:
            print(
                f"{prediction['label']}: "
                f"{prediction['probability']:.4f}"
            )

        # Save to RDS
        print("Saving top prediction to RDS...")
        top_prediction = predictions[0]
        print(
            f"key: {key}, label: {top_prediction['label']}, confidence: {top_prediction['probability']:.4f}"
        )
        save_prediction(
            key,
            top_prediction["label"],
            top_prediction["probability"],
        )

        # Delete SQS message

        sqs_client.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=message["ReceiptHandle"]
        )
        print("Message deleted from SQS")

        print("Processing complete")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

# Worker loop

def poll_queue():
    print("Worker started...", flush=True)
    while True:
        print("Polling SQS queue...", flush=True)
        response = sqs_client.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        messages = response.get(
            "Messages",
            []
        )

        print(f"Received {len(messages)} messages from SQS")
        if not messages:
            continue

        for message in messages:
            try:
                process_message(message)
            except Exception as e:
                print(
                    f"Error processing message: {e}"
                )

# Start worker

if __name__ == "__main__":
    check_db_entry()
    #poll_queue()