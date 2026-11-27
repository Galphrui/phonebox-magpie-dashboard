#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("PHONEBOX_URL", "http://127.0.0.1:8765").rstrip("/")


def request(path, data=None, version=None):
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if version:
        headers["X-Config-Version"] = version
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method="PUT" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=10) as response:
        body = response.read()
        return response.headers.get("X-Config-Version"), json.loads(body) if body else {}


def main():
    spec = json.loads((ROOT / "pages.json").read_text(encoding="utf-8"))
    version, config = request("/api/settings")
    pages = config.setdefault("pages", [])
    for page_id, details in spec["pages"].items():
        page = next((item for item in pages if item.get("id") == page_id), None)
        if page is None:
            page = {"id": page_id, "enabled": True}
            pages.append(page)
        page.update({"title": details["title"], "icon": details["icon"], "idleSec": details["idleSec"]})
        html = (ROOT / details["widget"]).read_text(encoding="utf-8")
        page["widgets"] = [{
            "id": details["widgetId"],
            "type": "html",
            "x": 0,
            "y": 0,
            "w": 12,
            "h": 6,
            "appearance": None,
            "options": {"html": html, "transparent": False},
        }]
    config.setdefault("display", {})["idleReturnSec"] = spec["idleReturnSec"]
    body = json.dumps(config, ensure_ascii=False).encode("utf-8")
    _, result = request("/api/settings", body, version)
    print("Updated PhoneBox pages: magpie, 路由; automatic return disabled.")
    if result.get("version"):
        print("Config version:", result["version"])


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as error:
        print("PhoneBox settings are unavailable at", BASE_URL, "- start PhoneBox and retry.", file=sys.stderr)
        raise SystemExit(1) from error
