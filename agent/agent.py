#!/usr/bin/env python3
"""HomePulse agent: zbiera metryki i wysyla je do serwera."""
import json
import os
import platform
import socket
import time
import urllib.request

import psutil

SERVER = os.environ.get("HOMEPULSE_SERVER", "http://127.0.0.1:9090").rstrip("/")
TOKEN = os.environ.get("HOMEPULSE_TOKEN", "")
INTERVAL = int(os.environ.get("HOMEPULSE_INTERVAL", "5"))
NAME = os.environ.get("HOMEPULSE_NAME", socket.gethostname())

_prev_net = None


def read_temps():
    temps = {}
    try:
        for chip, entries in (psutil.sensors_temperatures() or {}).items():
            for e in entries:
                if e.current is not None:
                    temps[f"{chip}:{e.label or 'temp'}"] = round(e.current, 1)
    except Exception:
        pass
    if not temps:  # fallback, np. Raspberry Pi
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                temps["cpu"] = round(int(f.read().strip()) / 1000, 1)
        except Exception:
            pass
    return temps


def read_disks():
    out = []
    seen = set()
    for p in psutil.disk_partitions(all=False):
        if p.mountpoint in seen:
            continue
        seen.add(p.mountpoint)
        try:
            u = psutil.disk_usage(p.mountpoint)
            out.append({"mount": p.mountpoint, "total": u.total, "used": u.used, "percent": u.percent})
        except Exception:
            pass
    return out


def read_net():
    global _prev_net
    c = psutil.net_io_counters()
    now = time.time()
    rx = tx = 0.0
    if _prev_net:
        dt = max(now - _prev_net[0], 0.001)
        rx = (c.bytes_recv - _prev_net[1]) / dt
        tx = (c.bytes_sent - _prev_net[2]) / dt
    _prev_net = (now, c.bytes_recv, c.bytes_sent)
    return {"rx_bps": round(rx), "tx_bps": round(tx)}


def top_processes(n=5):
    procs = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            procs.append({
                "name": p.info["name"],
                "cpu": round(p.info["cpu_percent"] or 0, 1),
                "mem": round(p.info["memory_percent"] or 0, 1),
            })
        except Exception:
            pass
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return procs[:n]


def collect():
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    try:
        load = list(os.getloadavg())
    except OSError:
        load = [0, 0, 0]
    return {
        "hostname": NAME,
        "os": f"{platform.system()} {platform.release()}",
        "uptime": int(time.time() - psutil.boot_time()),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_cores": psutil.cpu_percent(interval=None, percpu=True),
        "cpu_count": psutil.cpu_count(),
        "load": load,
        "mem": {"total": vm.total, "used": vm.used, "percent": vm.percent},
        "swap": {"total": sw.total, "used": sw.used, "percent": sw.percent},
        "temps": read_temps(),
        "disks": read_disks(),
        "net": read_net(),
        "procs": top_processes(),
    }


def send(data):
    req = urllib.request.Request(
        SERVER + "/api/report",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json", "X-Token": TOKEN},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5).read()


def main():
    print(f"HomePulse agent: {NAME} -> {SERVER}")
    psutil.cpu_percent(interval=None)  # rozgrzewka
    read_net()
    time.sleep(1)
    while True:
        try:
            send(collect())
        except Exception as e:
            print("blad wysylania:", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
