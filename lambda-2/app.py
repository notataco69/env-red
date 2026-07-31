import json
import boto3
import os
from decimal import Decimal
from datetime import datetime, timezone
from urllib.parse import unquote_plus

s3 = boto3.client("s3")
comprehend = boto3.client("comprehend")
dynamodb = boto3.resource("dynamodb")
BUCKET = os.environ["BUCKET_NAME"]
SLA_HOURS = float(os.environ.get("SLA_HOURS", 48))
TABLE_NAME = os.environ.get("TABLE_NAME", "env-red-shipments")
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    record = event["Records"][0]
    key = unquote_plus(record["s3"]["object"]["key"])

    obj = s3.get_object(Bucket=BUCKET, Key=key)
    data = json.loads(obj["Body"].read())

    if key.startswith("raw/shipment/"):
        process_shipment(data)
    elif key.startswith("raw/feedback/"):
        process_feedback(data)

    return {"statusCode": 200, "processed": key}


def process_shipment(data):
    received_at = datetime.fromisoformat(data["received_at"])
    hours_elapsed = (datetime.now(timezone.utc) - received_at).total_seconds() / 3600
    data["delayed"] = data.get("status") != "delivered" and hours_elapsed > SLA_HOURS
    data["hours_since_received"] = Decimal(str(round(hours_elapsed, 2)))

    table.put_item(Item=data)


def process_feedback(data):
    text = data["text"]
    sentiment = comprehend.detect_sentiment(Text=text, LanguageCode="en")
    phrases = comprehend.detect_key_phrases(Text=text, LanguageCode="en")

    data["sentiment"] = sentiment["Sentiment"]
    data["key_phrases"] = [p["Text"] for p in phrases["KeyPhrases"]]

    s3.put_object(
        Bucket=BUCKET,
        Key=f"processed/feedback/{data['received_at']}.json",
        Body=json.dumps(data),
        ContentType="application/json"
    )

    summary_key = "processed/feedback-summary.json"
    try:
        existing = json.loads(s3.get_object(Bucket=BUCKET, Key=summary_key)["Body"].read())
    except s3.exceptions.NoSuchKey:
        existing = {"total": 0, "POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0, "MIXED": 0}

    existing["total"] += 1
    existing[data["sentiment"]] += 1

    s3.put_object(Bucket=BUCKET, Key=summary_key, Body=json.dumps(existing), ContentType="application/json")
