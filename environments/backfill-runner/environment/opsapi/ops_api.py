"""Ops scheduler API stub (own container): records the job-run events scripts/run_job.sh reports.

The task container shares 127.0.0.1 with this service but cannot see its files or memory.
POST /v1/runs           record a run event (from run_job.sh)
GET  /v1/health         liveness
GET  /__grader/runs     every recorded event (token-protected; grader only)
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TOKEN = "grd-3b8e61d0-94c2-4f7a-a1e5-6d0c2b97f418"
LOG_FILE = Path("/var/log/opsapi/runs.jsonl")
events, lock = [], threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8", "replace")
        if urlparse(self.path).path != "/v1/runs":
            return self.reply(404, {"error": "not found"})
        try:
            event = json.loads(raw)
        except ValueError:
            return self.reply(400, {"error": "invalid json"})
        if not isinstance(event, dict):
            return self.reply(400, {"error": "expected an object"})
        event["received_at"] = time.time()
        with lock:
            events.append(event)
            with LOG_FILE.open("a") as f:
                f.write(json.dumps(event) + "\n")
        self.reply(201, {"ok": True})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/v1/health":
            return self.reply(200, {"ok": True})
        if url.path == "/__grader/runs" and parse_qs(url.query).get("token", [""])[0] == TOKEN:
            with lock:
                return self.reply(200, {"events": list(events)})
        self.reply(404, {"error": "not found"})


if __name__ == "__main__":
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", 9300), Handler).serve_forever()
