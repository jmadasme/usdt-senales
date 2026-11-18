#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Señales de presión compradora/vendedora en Binance Spot (solo lectura).

Tesis de la herramienta: cuando la presión de VENTA (volumen taker vendedor)
viene cayendo y al mismo tiempo la de COMPRA (volumen taker comprador) sube
de golpe, con el delta compra/venta cruzando al alza y el libro cargado de
bids → hay alta probabilidad de un movimiento al alza en el corto plazo.
La página avisa con un banner grande. NO opera: solo avisa.

Uso:
    ./run.sh          # o: venv/bin/python app.py
    → http://127.0.0.1:8790
"""

from __future__ import annotations

import threading
import time
import webbrowser
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

API = "https://api.binance.com"
HOST, PORT = "127.0.0.1", 8790
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]
INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"]
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
SESSION = requests.Session()
LOCK = threading.Lock()

CONFIG = {
    "symbol": "BTCUSDT",
    "interval": "1m",   # temporalidad del gráfico (la señal siempre usa 1m)
    "t_buy": 15.0,      # subida mínima de compras (%/min relativo a la media)
    "t_sell": -8.0,     # caída mínima de ventas (%/min; negativo)
    "imb_min": 0.05,    # desequilibrio mínimo del libro a favor de bids
    "sens": 2,          # score mínimo (1 relajada · 2 moderada · 3 estricta)
    "cooldown_min": 15, # no repetir alerta antes de X minutos
}

STATE = {
    "config": dict(CONFIG),
    "updated": None,
    "error": None,
    "precio": None,
    "series": None,
    "metrics": None,
    "book": None,
    "score": 0,
    "estado": "iniciando",
    "alert": None,
    "alerts": [],
    "last_alert_ts": 0.0,
    "cruce": False,
}


# --------------------------------------------------------------------------
# Datos de Binance (público, sin claves)
# --------------------------------------------------------------------------
def traer_klines(symbol: str, interval: str = "1m", limit: int = 120) -> list:
    r = SESSION.get(f"{API}/api/v3/klines",
                    params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=10)
    r.raise_for_status()
    return r.json()


def traer_depth(symbol: str, limit: int = 100) -> dict:
    r = SESSION.get(f"{API}/api/v3/depth", params={"symbol": symbol, "limit": limit}, timeout=10)
    r.raise_for_status()
    return r.json()


def traer_precio(symbol: str) -> float:
    r = SESSION.get(f"{API}/api/v3/ticker/price", params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    return float(r.json()["price"])


def ema(vals: list[float], n: int) -> list[float]:
    k = 2 / (n + 1)
    out, prev = [], None
    for v in vals:
        prev = v if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out


def pendiente_pct(ys: list[float], k: int = 10) -> float:
    """Pendiente por minuto de los últimos k puntos, normalizada (%) sobre la media."""
    if len(ys) < k + 1:
        return 0.0
    ventana = ys[-k:]
    n = len(ventana)
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(ventana) / n
    den = sum((x - mx) ** 2 for x in xs) or 1
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ventana)) / den
    media = (sum(ventana) / n) or 1
    return slope / media * 100.0


# --------------------------------------------------------------------------
# Análisis
# --------------------------------------------------------------------------
def analizar() -> None:
    with LOCK:
        cfg = dict(CONFIG)

    symbol = cfg["symbol"]
    kl = traer_klines(symbol)
    vol = [float(k[5]) for k in kl]
    buyv = [float(k[9]) for k in kl]
    sellv = [max(v - b, 0.0) for v, b in zip(vol, buyv)]
    precios = [float(k[4]) for k in kl]
    tiempos = [int(k[0]) for k in kl]

    be5, se5 = ema(buyv, 5), ema(sellv, 5)
    be20, se20 = ema(buyv, 20), ema(sellv, 20)
    slope_b = pendiente_pct(be20, 10)
    slope_s = pendiente_pct(se20, 10)
    delta = [b - s for b, s in zip(be5, se5)]
    cruce = any(delta[i - 1] <= 0 < delta[i] for i in range(max(1, len(delta) - 3), len(delta)))

    d = traer_depth(symbol, 100)
    bids = [(float(p), float(q)) for p, q in d["bids"]]
    asks = [(float(p), float(q)) for p, q in d["asks"]]
    bid_vol = sum(q for _, q in bids)
    ask_vol = sum(q for _, q in asks)
    imb = (bid_vol - ask_vol) / (bid_vol + ask_vol or 1)
    precio = traer_precio(symbol)

    subida_3m = (precio / precios[-4] - 1) * 100 if len(precios) >= 4 and precios[-4] else 0.0

    cae_venta = slope_s <= cfg["t_sell"]
    sube_compra = slope_b >= cfg["t_buy"]
    libro_comprador = imb >= cfg["imb_min"]

    razones = []
    if cae_venta:
        razones.append(f"ventas cayendo ({slope_s:+.1f}%/min)")
    if sube_compra:
        razones.append(f"compras subiendo ({slope_b:+.1f}%/min)")
    if cruce:
        razones.append("cruce del delta compra/venta")
    if libro_comprador:
        razones.append(f"libro comprador ({imb * 100:+.1f}%)")
    score = (1 if cruce else 0) + (1 if cae_venta else 0) + (1 if sube_compra else 0) + (1 if libro_comprador else 0)

    # La alerta SIEMPRE nace del cruce. La sensibilidad define qué más se exige:
    #   1 = solo el cruce · 2 = cruce + ventas cayendo o compras subiendo
    #   3 = cruce + ventas cayendo + compras subiendo (escenario exacto)
    if cfg["sens"] >= 3:
        alertable = cruce and cae_venta and sube_compra
    elif cfg["sens"] == 2:
        alertable = cruce and (cae_venta or sube_compra)
    else:
        alertable = cruce

    ahora = time.time()
    with LOCK:
        last_ts = STATE["last_alert_ts"]
        cooldown = cfg["cooldown_min"] * 60

    alerta = None
    if alertable:
        nueva = (ahora - last_ts) > cooldown
        alerta = {
            "ts": datetime.now().strftime("%H:%M:%S"),
            "precio": precio,
            "score": score,
            "razones": razones,
            "nueva": nueva,
            "subida_3m": round(subida_3m, 3),
        }
        if nueva:
            with LOCK:
                STATE["last_alert_ts"] = ahora
                STATE["alerts"].append({"ts": alerta["ts"], "precio": precio,
                                        "score": score, "razones": razones})
                del STATE["alerts"][:-30]
    estado = "OPORTUNO" if alertable else "vigilando"

    interval = cfg.get("interval", "1m")
    klc = kl if interval == "1m" else traer_klines(symbol, interval, 180)
    series = {
        "candles": [
            {"t": int(k[0] // 1000), "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
             "c": float(k[4]), "v": float(k[5]), "b": float(k[9])}
            for k in klc
        ]
    }
    metrics = {
        "slope_buy": round(slope_b, 2),
        "slope_sell": round(slope_s, 2),
        "imb": round(imb * 100, 2),
        "ratio": round(be5[-1] / se5[-1], 3) if se5[-1] else None,
        "subida_3m": round(subida_3m, 3),
    }
    book = {
        "bids": [[p, q] for p, q in bids[:20]],
        "asks": [[p, q] for p, q in asks[:20]],
        "bid_vol": round(bid_vol, 2),
        "ask_vol": round(ask_vol, 2),
    }

    with LOCK:
        STATE.update({
            "config": cfg,
            "symbol": symbol,
            "updated": datetime.now().strftime("%H:%M:%S"),
            "precio": precio,
            "series": series,
            "metrics": metrics,
            "book": book,
            "score": score,
            "cruce": cruce,
            "estado": estado,
            "alert": alerta,
            "error": None,
        })


def poll_loop() -> None:
    while True:
        try:
            analizar()
        except Exception as e:  # noqa: BLE001
            with LOCK:
                STATE["error"] = str(e)
        time.sleep(3)


# --------------------------------------------------------------------------
# Web
# --------------------------------------------------------------------------
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    with LOCK:
        return jsonify({**STATE, "symbols": SYMBOLS, "intervals": INTERVALS})


@app.post("/api/config")
def api_config():
    p = request.get_json(silent=True) or {}
    with LOCK:
        if p.get("symbol"):
            CONFIG["symbol"] = str(p["symbol"]).upper().strip()
        if p.get("interval") in INTERVALS:
            CONFIG["interval"] = p["interval"]
        for k in ("t_buy", "t_sell", "imb_min", "cooldown_min"):
            if k in p:
                try:
                    CONFIG[k] = float(p[k])
                except (TypeError, ValueError):
                    pass
        if "sens" in p:
            try:
                CONFIG["sens"] = max(1, min(3, int(p["sens"])))
            except (TypeError, ValueError):
                pass
        STATE["config"] = dict(CONFIG)
        STATE["alerts"] = []
        STATE["alert"] = None
        STATE["last_alert_ts"] = 0.0
    return jsonify({"ok": True})


def main() -> int:
    threading.Thread(target=poll_loop, daemon=True).start()
    url = f"http://{HOST}:{PORT}/"
    print(f"Señales Binance Spot → {url}   (Ctrl+C para cerrar)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
