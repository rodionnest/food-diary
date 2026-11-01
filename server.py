"""Локальный сервер дневников без внешних сервисов и зависимостей.

Запуск: python3 server.py --host 127.0.0.1 --port 8000.
Данные: data/<дневник>/<коллекция>.json. Разбор ввода выполняется в браузере.
"""
import argparse
import json
import os
import re
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
DIARIES = [("Дневник Родион.html", "Дневник Родиона"), ("Дневник Анны.html", "Дневник Анны")]
lock = threading.Lock()


def coll_path(diary, coll):
    return DATA / diary / f"{coll}.json"


def read_coll(diary, coll):
    p = coll_path(diary, coll)
    if not p.exists():
        return {}, 0
    return json.loads(p.read_text(encoding="utf-8")), p.stat().st_mtime_ns


def write_coll(diary, coll, docs):
    p = coll_path(diary, coll)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def index_html():
    links = "".join(
        f'<a href="/{n}">{title}</a>' for n, title in DIARIES if (ROOT / n).exists()
    )
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Дневники</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>:root{{color-scheme:light dark}}body{{font:18px system-ui,sans-serif;margin:0;min-height:100vh;display:grid;place-content:center;gap:14px;background:Canvas}}
a{{display:block;padding:16px 28px;border:1px solid #8884;border-radius:14px;text-decoration:none;color:inherit;text-align:center}}a:hover{{background:#8881}}</style>
</head><body>{links}</body></html>"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def send_json(self, obj, status=HTTPStatus.OK):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"null")

    def db_route(self):
        """/api/db/<дневник>/<коллекция>[/<id>] → (diary, coll, id) или None."""
        parts = urlparse(self.path).path.split("/")[3:]
        if len(parts) not in (2, 3) or not all(NAME_RE.match(p) for p in parts):
            self.send_json({"code": "invalid_argument"}, HTTPStatus.BAD_REQUEST)
            return None
        return parts + [None] * (3 - len(parts))

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/":
            body = index_html().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path.startswith("/api/db/"):
            r = self.db_route()
            if r:
                diary, coll, _ = r
                with lock:
                    docs, rev = read_coll(diary, coll)
                self.send_json({"rev": rev, "docs": [{"id": k, "data": v} for k, v in docs.items()]})
        elif any(part.startswith(".") for part in Path(path).parts) or path.startswith("/data/") or path.endswith((".py", ".sh")):
            self.send_error(HTTPStatus.NOT_FOUND)
        else:
            super().do_GET()

    def do_PUT(self):
        r = self.db_route() if self.path.startswith("/api/db/") else self.send_error(HTTPStatus.NOT_FOUND)
        if not r:
            return
        diary, coll, doc_id = r
        data = self.read_body()
        if not doc_id or not isinstance(data, dict):
            return self.send_json({"code": "invalid_argument"}, HTTPStatus.BAD_REQUEST)
        with lock:
            docs, _ = read_coll(diary, coll)
            docs[doc_id] = data
            write_coll(diary, coll, docs)
        self.send_json({"ok": True})

    def do_DELETE(self):
        r = self.db_route() if self.path.startswith("/api/db/") else self.send_error(HTTPStatus.NOT_FOUND)
        if not r:
            return
        diary, coll, doc_id = r
        if not doc_id:
            return self.send_json({"code": "invalid_argument"}, HTTPStatus.BAD_REQUEST)
        with lock:
            docs, _ = read_coll(diary, coll)
            if docs.pop(doc_id, None) is not None:
                write_coll(diary, coll, docs)
        self.send_json({"ok": True})

    def log_message(self, fmt, *args):
        if not self.path.startswith("/api/db/") or self.command != "GET":
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description="Локальный сервер дневников")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Дневники: http://localhost:{args.port}/  (локальный режим, данные в {DATA})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
