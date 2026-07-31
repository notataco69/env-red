"""
Local backend for the env-red ops board.

Serves the static dashboard and proxies two read-only calls to the existing
env-red-lambda-3 (the only thing allowed to read the DynamoDB table / S3
summary directly). Uses whatever AWS credentials are already configured
locally (aws configure / env vars / SSO) -- nothing is hardcoded here.

Binds to 127.0.0.1 only: not reachable from other machines on the network.

Run:
    python3 server.py
Then open http://127.0.0.1:8787/
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import boto3

HOST = "127.0.0.1"
PORT = 8787
FUNCTION_NAME = os.environ.get("ENV_RED_LAMBDA3_NAME", "env-red-lambda-3")
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def invoke_lambda3(query_payload):
    resp = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(query_payload).encode(),
    )
    raw = resp["Payload"].read()
    if resp.get("FunctionError"):
        raise RuntimeError(f"lambda error: {raw.decode()}")
    result = json.loads(raw)
    body = result.get("body")
    status_code = result.get("statusCode", 200)
    return status_code, json.loads(body) if isinstance(body, str) else body


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[dashboard] {self.address_string()} - {fmt % args}")

    def _send_json(self, status, obj):
        payload = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, path, content_type):
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/shipments":
            try:
                status, data = invoke_lambda3({"query": "list_shipments"})
                self._send_json(status, data)
            except Exception as e:
                self._send_json(502, {"error": str(e)})
            return

        if self.path == "/api/feedback-summary":
            try:
                status, data = invoke_lambda3({"query": "feedback_summary"})
                self._send_json(status, data)
            except Exception as e:
                self._send_json(502, {"error": str(e)})
            return

        if self.path in ("/", "/index.html"):
            self._send_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
            return

        self._send_json(404, {"error": "not found"})


if __name__ == "__main__":
    print(f"env-red ops board: http://{HOST}:{PORT}/  (Ctrl+C to stop)")
    HTTPServer((HOST, PORT), Handler).serve_forever()
