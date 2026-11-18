# USDT Señales · developer

## Mapa del código

```text
usdt-senales/
├── app.py               # Flask + hilo de muestreo
├── templates/index.html # tablero en vivo
├── requirements.txt
├── run.sh
├── docs/                # página, datasheet y developer
└── README.md
```

## Flujo de datos

1. `Binance` — API pública
2. `Sampler` — hilo Python
3. `Flask` — /api/state
4. `Tablero` — JS + libro

## Decisiones de diseño

- **Sin credenciales** (A): Solo endpoints públicos. No hay API key ni firma.
- **Tres sensibilidades** (B): Relajada, moderada y estricta cambian el umbral del score.
- **Enfriamiento** (C): 15 minutos para evitar alertas repetidas por la misma condición.

## Stack

Python, Flask, Binance Spot, JavaScript, WebSocket.

Flask sirve la página y el estado; un hilo de muestreo mantiene las métricas. La interfaz usa JavaScript y WebSocket para el libro. No hay base de datos: el estado vive en memoria y se reinicia con el proceso.

## Cómo extenderlo

- Separá la lógica de dominio de la interfaz: el motor debe poder probarse sin navegador.
- Mantené los datos de demo fuera de la lógica y documentá su origen.
- Si agregás una integración externa, poné las credenciales en variables de entorno y un `.env.example` con `x`.
- Agregá una prueba de humo por cada flujo crítico antes de publicar.

## Puesta en marcha

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
# Abrir http://127.0.0.1:8790
```

## Seguridad

No usa API keys: lee datos públicos de Binance Spot. No opera, no firma y no custodia fondos. Las señales son experimentales y no constituyen asesoría financiera.

## Límites conocidos

- **No opera**: No hay órdenes, claves ni custodia. Es un tablero de observación.
- **Datos públicos**: Binance puede limitar tasa o cambiar endpoints; el sampler debe adaptarse.
- **Sin persistencia**: El estado se pierde al reiniciar. No hay histórico ni base de datos.
- **Riesgo**: Una señal técnica no garantiza rentabilidad. No es asesoría financiera.

## Enlaces

- [README](../README.md)
- [Datasheet](datasheet.md)
- [Repositorio](https://github.com/jmadasme/usdt-senales)
