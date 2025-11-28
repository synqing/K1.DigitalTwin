import sys
import os
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.core import TwinEngine

engine = TwinEngine()
engine.load_assets()

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path == "/health":
            self._send_json({"status": "ok"})
            return
        if self.path == "/state":
            self._send_json(engine.state())
            return
        self._send_json({"error": "not found"}, 404)


def main(host="0.0.0.0", port=8000):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Server listening at http://{host}:{port}/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
