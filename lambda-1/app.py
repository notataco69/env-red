import json
import boto3
import os
import uuid
from datetime import datetime, timezone

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET_NAME"]

def handler(event, context):
    # event is expected to look like:
    # { "type": "shipment", "package_id": "PKG123", "location": "Denver Hub", "status": "in_transit" }
    # or
    # { "type": "feedback", "package_id": "PKG123", "text": "package was 3 days late" }

    record_type = event.get("type", "unknown")
    record_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    event["received_at"] = timestamp

    key = f"raw/{record_type}/{record_id}.json"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(event),
        ContentType="application/json"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"saved_to": key})
    }
