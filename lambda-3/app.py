import json
import boto3
import os

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET_NAME"]

def handler(event, context):
    query = event.get("query")

    if query == "shipment":
        package_id = event.get("package_id")
        key = f"processed/shipment/{package_id}.json"
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            return {"statusCode": 200, "body": obj["Body"].read().decode()}
        except s3.exceptions.NoSuchKey:
            return {"statusCode": 404, "body": json.dumps({"error": f"no data for {package_id}"})}

    elif query == "feedback_summary":
        key = "processed/feedback-summary.json"
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            return {"statusCode": 200, "body": obj["Body"].read().decode()}
        except s3.exceptions.NoSuchKey:
            return {"statusCode": 200, "body": json.dumps({"total": 0})}

    else:
        return {"statusCode": 400, "body": json.dumps({"error": "unknown query type"})}
