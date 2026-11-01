import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class Connection:
    """HTTP-обработчик с потоками в памяти, без сокетов и реальных данных."""
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = io.BytesIO()

    def makefile(self, mode, *args):
        return self.input if mode == "rb" else self.output

    def sendall(self, data):
        self.output.write(data)


class LocalServerTests(unittest.TestCase):
    def request(self, method, path, body=None):
        payload = json.dumps(body).encode() if body is not None else b""
        request = f"{method} {path} HTTP/1.0\r\nContent-Length: {len(payload)}\r\n\r\n".encode() + payload
        connection = Connection(request)
        with patch.object(server.Handler, "log_message"):
            server.Handler(connection, ("127.0.0.1", 12345), None)
        headers, data = connection.output.getvalue().split(b"\r\n\r\n", 1)
        return int(headers.split()[1]), data

    def test_storage_roundtrip_and_diary_isolation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(server, "DATA", Path(directory)):
            entry = {"date": "2026-11-01", "weight": 86.4, "meals": []}
            self.assertEqual(self.request("PUT", "/api/db/rodion/days/2026-11-01", entry)[0], 200)
            status, body = self.request("GET", "/api/db/rodion/days")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["docs"][0]["data"], entry)
            self.assertEqual(json.loads(self.request("GET", "/api/db/anna/days")[1])["docs"], [])
            self.assertEqual(self.request("DELETE", "/api/db/rodion/days/2026-11-01")[0], 200)
            self.assertEqual(json.loads(self.request("GET", "/api/db/rodion/days")[1])["docs"], [])

    def test_static_pages_and_private_files(self):
        from urllib.parse import quote
        for path in ["/", "/local-entry.js", "/local-claude.js", "/Дневник Анны.html", "/Дневник Родион.html"]:
            self.assertEqual(self.request("GET", quote(path))[0], 200)
        for path in ["/.env", "/.git/config", "/data/rodion/days.json", "/server.py"]:
            self.assertEqual(self.request("GET", path)[0], 404)


if __name__ == "__main__":
    unittest.main()
