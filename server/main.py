"""HomePulse server: odbiera dane od agentow i serwuje dashboard na porcie 9090."""
import os
import sqlite3
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse

BASE = Path(__file__).parent
TOKEN = os.environ.get("HOMEPULSE_TOKEN", "")
DB_PATH = os.environ.get("HOMEPULSE_DB", str(BASE / "data.db"))
OFFLINE_AFTER = 15          # sekundy bez kontaktu = offline
RETENTION_DAYS = 7

app = FastAPI(title="HomePulse")
latest = {}
lock = threading.Lock()
_counter = 0


def db():
    return sqlite3.connect(DB_PATH)


@app.on_event("startup")
def init():
    conn = db()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS metrics ("
        "server TEXT, ts REAL, cpu REAL, mem REAL, temp REAL, load1 REAL)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx ON metrics(server, ts)")
    conn.commit()
    conn.close()


def check_token(request: Request):
    if TOKEN and request.headers.get("x-token") != TOKEN:
        raise HTTPException(401, "zly token")


@app.post("/api/report")
async def report(request: Request):
    global _counter
    check_token(request)
    data = await request.json()
    name = str(data.get("hostname", "unknown"))[:64]
    now = time.time()
    data["last_seen"] = now
    data["ip"] = request.client.host
    with lock:
        latest[name] = data
    temps = data.get("temps") or {}
    temp = max(temps.values()) if temps else None
    conn = db()
    conn.execute(
        "INSERT INTO metrics VALUES (?,?,?,?,?,?)",
        (name, now, data.get("cpu_percent"), (data.get("mem") or {}).get("percent"),
         temp, (data.get("load") or [None])[0]),
    )
    _counter += 1
    if _counter % 500 == 0:
        conn.execute("DELETE FROM metrics WHERE ts < ?", (now - RETENTION_DAYS * 86400,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/servers")
def servers():
    now = time.time()
    with lock:
        items = list(latest.values())
    for s in items:
        s["online"] = now - s["last_seen"] < OFFLINE_AFTER
        s["age"] = round(now - s["last_seen"])
    items.sort(key=lambda s: s["hostname"])
    return items


@app.get("/api/history/{name}")
def history(name: str, minutes: int = 60):
    since = time.time() - minutes * 60
    conn = db()
    rows = conn.execute(
        "SELECT ts, cpu, mem, temp, load1 FROM metrics WHERE server=? AND ts>? ORDER BY ts",
        (name, since),
    ).fetchall()
    conn.close()
    step = max(1, len(rows) // 300)  # max ~300 punktow
    return [dict(ts=r[0], cpu=r[1], mem=r[2], temp=r[3], load=r[4]) for r in rows[::step]]


@app.get("/agent.py")
def agent_file():
    return FileResponse(BASE.parent / "agent" / "agent.py", media_type="text/plain")


@app.get("/install.sh")
def install(request: Request):
    if TOKEN and request.query_params.get("token") != TOKEN:
        raise HTTPException(401, "podaj ?token=...")
    tpl = (BASE / "install.sh.tpl").read_text()
    url = str(request.base_url).rstrip("/")
    return PlainTextResponse(tpl.replace("__URL__", url).replace("__TOKEN__", TOKEN))


@app.get("/")
def index():
    return FileResponse(BASE / "index.html")
