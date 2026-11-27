#!/usr/bin/env python3
"""PhoneBox ← magpie bridge.

Reads magpie's local app API (http://127.0.0.1:3430, key from
~/.config/magpie/web-page.json) and pushes a compact snapshot to the PhoneBox
agent (http://127.0.0.1:8765/api/push/magpie), where the Custom HTML widget on
the "AI" page renders it live.

Runs from launchd every few seconds. Never raises: a magpie that is down or
restarting just produces an "offline" snapshot, so the widget can say so.
"""

import http.client
import json
import os
import time
import urllib.parse
import urllib.request
import fcntl

MAGPIE_HOST, MAGPIE_PORT = "127.0.0.1", 3430
PHONEBOX_PUSH = "http://127.0.0.1:8765/api/push/magpie"
KEY_FILE = os.path.expanduser("~/.config/magpie/web-page.json")
LOCK_FILE = os.path.expanduser("~/Library/Application Support/PhoneBox/bridge/.magpie-bridge.lock")
TIMEOUT = 4.0


def read_key():
    try:
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return (cfg.get("mode") or ""), (cfg.get("key") or "")
    except Exception:
        return "", ""


class Magpie:
    """One connection per run; the app page's 303 hands out the cookie."""

    def __init__(self, key):
        self.key = key
        self.cookie = None
        self.conn = None

    def _connect(self):
        self.conn = http.client.HTTPConnection(MAGPIE_HOST, MAGPIE_PORT, timeout=TIMEOUT)
        self.conn.request("GET", "/?k=" + urllib.parse.quote(self.key))
        resp = self.conn.getresponse()
        raw = resp.getheader("Set-Cookie") or ""
        resp.read()
        if raw:
            self.cookie = raw.split(";", 1)[0]

    def get(self, path):
        if self.conn is None:
            self._connect()
        headers = {"Accept": "application/json"}
        if self.cookie:
            headers["Cookie"] = self.cookie
        try:
            self.conn.request("GET", path, headers=headers)
            resp = self.conn.getresponse()
            body = resp.read()
        except Exception:
            # a reused keep-alive connection can be stale: retry once on a fresh one
            self.conn = None
            self._connect()
            headers = {"Accept": "application/json"}
            if self.cookie:
                headers["Cookie"] = self.cookie
            self.conn.request("GET", path, headers=headers)
            resp = self.conn.getresponse()
            body = resp.read()
        if resp.status != 200:
            raise RuntimeError("magpie %s -> %s" % (path, resp.status))
        return json.loads(body.decode("utf-8"))

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None


def num(v, default=0):
    return v if isinstance(v, (int, float)) else default


def snapshot(mp):
    today = mp.get("/api/usage?period=today")
    week = mp.get("/api/usage?period=7d")
    traffic = mp.get("/api/usage/traffic")
    quotas = mp.get("/api/usage/quotas")
    recent = mp.get("/api/usage/requests?period=today&limit=6")
    trace = mp.get("/api/gateway/trace")

    timed = num(today.get("timed"))
    decode_ms = num(today.get("decode_ms"))
    series = []
    for bucket in (recent.get("series") or [])[:24]:
        by_agent = (bucket.get("by") or {}).get("agent") or {}
        series.append({
            "h": bucket.get("label") or "",
            "calls": num(bucket.get("calls")),
            "tokens": num(bucket.get("input")) + num(bucket.get("output")),
            "cost": round(num(bucket.get("cost")), 4),
            "agents": {k: num(v.get("calls")) for k, v in by_agent.items()},
        })

    rows = []
    for r in (recent.get("rows") or [])[:6]:
        t = r.get("t") or ""
        rows.append({
            "t": t[11:16] if len(t) > 16 else t,
            "agent": r.get("agent") or "",
            "model": r.get("served") or r.get("model") or "",
            "ms": num(r.get("ms")),
            "status": num(r.get("status")),
            "in": num(r.get("in")),
            "out": num(r.get("out")),
        })

    by_agent = {}
    for bucket in (recent.get("series") or []):
        for k, v in ((bucket.get("by") or {}).get("agent") or {}).items():
            a = by_agent.setdefault(k, {"calls": 0, "tokens": 0, "cost": 0.0, "tps": 0.0})
            a["calls"] += num(v.get("calls"))
            a["tokens"] += num(v.get("tokens"))
            a["cost"] += num(v.get("cost"))
            a["tps"] = max(a["tps"], num(v.get("tps")))

    routes = []
    for r in (trace.get("routes") or [])[-12:]:
        order = []
        for item in (r.get("order") or [])[:8]:
            order.append({
                "provider": item.get("name") or item.get("provider") or "",
                "account": item.get("who") or "",
                "model": item.get("model") or "",
                "rank": item.get("rank"),
                "used": num(item.get("used")),
                "barred": bool(item.get("barred")),
                "unlisted": bool(item.get("unlisted")),
                "eligible": True,
            })
        for item in (r.get("left") or [])[:8]:
            order.append({
                "provider": item.get("name") or item.get("provider") or "",
                "account": item.get("who") or "",
                "model": item.get("model") or "",
                "rank": None,
                "used": num(item.get("used")),
                "barred": bool(item.get("barred")),
                "unlisted": bool(item.get("unlisted")),
                "eligible": False,
            })
        tries = []
        for item in (r.get("tries") or [])[:8]:
            tries.append({
                "model": item.get("served") or item.get("model") or "",
                "status": num(item.get("status")),
                "ms": num(item.get("ms")),
                "ttft": num(item.get("ttft")),
                "done": bool(item.get("done")),
            })
        at = r.get("time") or ""
        routes.append({
            "at": at[11:16] if len(at) >= 16 else at,
            "agent": r.get("agent") or "",
            "model": r.get("served") or r.get("model") or "",
            "provider": r.get("provider") or "",
            "effort": r.get("effort") or "",
            "status": num(r.get("status")),
            "ms": num(r.get("ms")),
            "ttft": num(r.get("ttft")),
            "tokens": num(r.get("tokens")),
            "out": num(r.get("out")),
            "done": bool(r.get("done")),
            "active": not bool(r.get("done")),
            "affinity": {
                "kept": bool((r.get("affinity") or {}).get("kept")),
                "why": (r.get("affinity") or {}).get("why") or "",
                "turn": num((r.get("affinity") or {}).get("turn")),
            },
            "order": order,
            "tries": tries,
        })

    return {
        "ok": True,
        "ts": int(time.time() * 1000),
        "today": {
            "calls": num(today.get("calls")),
            "errors": num(today.get("errors")),
            "retried": num(today.get("retried")),
            "cost": round(num(today.get("cost")), 4),
            "unpriced": num(today.get("unpriced")),
            "in": num(today.get("input")),
            "out": num(today.get("output")),
            "cache": num(today.get("cache_read")),
            "ttft": round(num(today.get("ttft_ms")) / timed, 0) if timed else None,
            "tps": round(num(today.get("decode_out")) / (decode_ms / 1000.0), 1) if decode_ms else None,
        },
        "week": {
            "calls": num(week.get("calls")),
            "cost": round(num(week.get("cost")), 2),
            "errors": num(week.get("errors")),
        },
        "traffic": {
            "up": num(traffic.get("up")),
            "down": num(traffic.get("down")),
            "requests": num(traffic.get("requests")),
        },
        "quotas": [
            {
                "name": q.get("name") or q.get("provider") or "",
                "user": q.get("user") or "",
                "balance": q.get("balance"),
                "windows": [
                    {"label": w.get("label") or w.get("name") or "", "left": w.get("leftPct") or w.get("percent")}
                    for w in (q.get("windows") or [])[:2]
                ],
            }
            for q in (quotas or [])[:6]
        ],
        "recent": rows,
        "byAgent": by_agent,
        "series": series,
        "routing": {
            "requests": num((trace.get("totals") or {}).get("requests")),
            "rerouted": num((trace.get("totals") or {}).get("rerouted")),
            "errors": num((trace.get("totals") or {}).get("errors")),
            "routes": routes,
        },
    }


def push(payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        PHONEBOX_PUSH, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        r.read()


def main():
    # launchd starts a run every few seconds whether or not the last one finished; a slow magpie
    # must not pile runs up, so a second run just leaves the work to the one in flight.
    lock = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0

    mode, key = read_key()
    payload = {"ok": False, "ts": int(time.time() * 1000)}
    if mode == "off" or not key:
        payload["err"] = "magpie 浏览器访问已关闭"
    else:
        mp = Magpie(key)
        try:
            payload = snapshot(mp)
        except Exception as e:  # magpie restarting, port busy, ...
            payload["err"] = str(e)[:200]
        finally:
            mp.close()
    if payload.get("ok"):
        t = payload["today"]
        payload["value"] = str(t["calls"])
        payload["sub"] = "magpie · 今日调用"
    else:
        payload["value"] = "—"
        payload["sub"] = "magpie 离线"
    try:
        push(payload)
    except Exception as e:
        print("push failed:", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
