import json
import boto3
import os
from decimal import Decimal

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
BUCKET = os.environ["BUCKET_NAME"]
TABLE_NAME = os.environ.get("TABLE_NAME", "env-red-shipments")
table = dynamodb.Table(TABLE_NAME)

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    query = event.get("query")

    if query == "shipment":
        package_id = event.get("package_id")
        resp = table.get_item(Key={"package_id": package_id})
        if "Item" not in resp:
            return {"statusCode": 404, "body": json.dumps({"error": f"no data for {package_id}"})}
        return {"statusCode": 200, "body": json.dumps(resp["Item"], default=decimal_default)}

    elif query == "feedback_summary":
        key = "processed/feedback-summary.json"
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            return {"statusCode": 200, "body": obj["Body"].read().decode()}
        except s3.exceptions.NoSuchKey:
            return {"statusCode": 200, "body": json.dumps({"total": 0})}

    else:
        return {"statusCode": 400, "body": json.dumps({"error": "unknown query type"})}
