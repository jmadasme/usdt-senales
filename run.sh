#!/usr/bin/env bash
# Arranca el panel de señales con su entorno virtual propio.
cd "$(dirname "$0")"
exec ./venv/bin/python app.py
