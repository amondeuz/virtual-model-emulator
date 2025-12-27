"""Simple static file server with CORS support."""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 8765
DIRECTORY = Path(__file__).parent / "public"

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("127.0.0.1", PORT), CORSRequestHandler) as httpd:
        print(f"http://localhost:{PORT}/config.html")
        httpd.serve_forever()
