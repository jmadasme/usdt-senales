#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera el manual de usuario en Word (.docx) del proyecto usdt-senales."""

import os
import shutil

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(BASE, "Explicacion-usdt-senales.docx")
ESCRITORIO = os.path.expanduser("~/Desktop")


def h(doc, texto, nivel=1):
    doc.add_heading(texto, level=nivel)


def p(doc, texto, negrita=False):
    par = doc.add_paragraph()
    run = par.add_run(texto)
    run.bold = negrita
    return par


def b(doc, texto):
    doc.add_paragraph(texto, style="List Bullet")


def tabla(doc, filas, encabezados):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    for i, enc in enumerate(encabezados):
        cel = t.rows[0].cells[i]
        cel.text = enc
        for par in cel.paragraphs:
            for run in par.runs:
                run.bold = True
    for fila in filas:
        celdas = t.add_row().cells
        for i, valor in enumerate(fila):
            celdas[i].text = valor
    doc.add_paragraph()
    return t


def main():
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(10.5)

    titulo = doc.add_heading("Señales Spot — Explicación y manual de uso", level=0)
    sub = doc.add_paragraph()
    r = sub.add_run("Proyecto: usdt-senales · Datos: Binance Spot (público) · Solo avisa: NO opera")
    r.italic = True
    r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    h(doc, "1. ¿Qué es esta herramienta?", 1)
    p(doc, "Es un panel local que corre en tu computadora (se abre en http://127.0.0.1:8790) y vigila "
           "el mercado Spot de Binance. Mide minuto a minuto la presión real de compradores y vendedores "
           "y avisa con un banner verde grande (y sonido) cuando detecta una situación que suele anticipar "
           "una subida de corto plazo en el precio. No compra, no vende, no coloca órdenes: solo muestra "
           "datos y avisa. La decisión siempre es tuya.")

    h(doc, "2. La tesis: el cruce de tendencias", 1)
    p(doc, "El precio cae cuando hay mucha oferta de venta (vendedores fuertes). Si en un momento la presión "
           "de VENTA se desploma (los vendedores desaparecen) y al mismo tiempo la presión de COMPRA sube "
           "explosivamente, lo más probable es que el precio suba: la oferta se seca y la demanda empuja.")
    p(doc, "La herramienta mide el volumen real ejecutado ('taker volume': las órdenes que se cruzan contra "
           "el libro) y dibuja dos líneas:")
    b(doc, "EMA de compras — verde, iluminada (la que importa).")
    b(doc, "EMA de ventas — roja, tenue.")
    p(doc, "Cuando la línea de compras cruza POR ENCIMA de la de ventas, se produce el evento central del "
           "sistema: el cruce. Sin cruce, nunca hay alerta.")

    h(doc, "3. Qué muestra la página", 1)
    b(doc, "Order Book: libro de órdenes estilo Binance: 20 niveles por lado con Precio, Monto y Total, "
           "precio grande con flecha al medio, spread, ratio B/V y la suma total del libro. Se actualiza "
           "en tiempo real vía WebSocket.")
    b(doc, "Gráfico: las líneas de compras (verde iluminada) y ventas (roja tenue). Botón «Precio: ON/OFF» "
           "para mostrar u ocultar las velas de precio y sus medias MA(7/25/99). Selector «Presión 20/35/50/70%» "
           "para elegir el alto del área de las líneas cuando el precio está visible.")
    b(doc, "Panel de métricas: Score, Ventas/min, Compras/min, Libro, Ratio B/V, Subida 3 min y Cruce.")
    b(doc, "Configuración: sensibilidad, umbrales y espera entre avisos.")
    b(doc, "Alertas: historial de los avisos dados en la sesión (hora, precio y razones).")

    h(doc, "4. Los indicadores, uno por uno", 1)
    tabla(doc, [
        ("Score", "0 a 4", "Cuántas de las 4 condiciones se cumplen: cruce, ventas cayendo, compras subiendo y libro comprador. Los números se ponen verdes cuando superan tu umbral."),
        ("Ventas /min", "−8% por defecto", "Cuánto cambia por minuto la presión vendedora. Para contar como «en picada» debe caer al menos el % que configures (negativo)."),
        ("Compras /min", "+15% por defecto", "Cuánto cambia por minuto la presión compradora. Para contar como «explosiva» debe subir al menos el % que configures."),
        ("Libro (bids−asks)", "5% por defecto", "Desbalance del libro: cuánta más plata hay en compra que en venta (en %). Positivo = libro comprador. Es contexto: nunca dispara alerta solo."),
        ("Ratio B/V", "—", "Bids ÷ Asks de los niveles visibles. Mayor a 1 = más compradores en el libro; menor a 1 = más vendedores. Es volátil: mirá la tendencia, no un dato aislado."),
        ("Subida 3 min", "—", "Cuánto subió el precio en los últimos 3 minutos. Sirve de aviso: si al alertar ya subió mucho (>0.4%), puede que llegues tarde."),
        ("Cruce", "sí / no", "LA condición imprescindible: la EMA de compras cruzó al alza a la de ventas. Sin cruce no hay alerta, jamás."),
    ], ["Indicador", "Umbral", "Qué significa"])

    h(doc, "5. Los ajustes, uno por uno", 1)
    tabla(doc, [
        ("Sensibilidad", "Moderada", "Cuánto se exige alrededor del cruce. Relajada: solo el cruce. Moderada: cruce + ventas cayendo O compras subiendo. Estricta: cruce + ventas cayendo Y compras subiendo (el escenario ideal)."),
        ("Subida compras ≥", "15 %/min", "Qué tan explosiva debe ser la subida de compras. Más bajo = detecta más (señales más débiles); más alto = solo explosiones fuertes."),
        ("Caída ventas ≤", "−8 %/min", "Qué tan pronunciada debe ser la caída de ventas. Más cerca de 0 = más fácil que cuente; más negativo = más exigente."),
        ("Desbalance libro ≥", "5 %", "Ventaja mínima de compradores en el libro para sumar un punto al Score."),
        ("Espera entre avisos", "15 min", "Enfriamiento: después de una alerta no vuelve a sonar hasta que pase este tiempo. Evita spam de banners."),
        ("Aplicar", "—", "Guarda los cambios y limpia el historial de alertas para empezar de cero con la nueva configuración."),
    ], ["Ajuste", "Valor por defecto", "Qué hace"])

    h(doc, "6. Cómo usarlo (paso a paso)", 1)
    b(doc, "Abrir una terminal y ejecutar:  cd /home/jma/Documents/Proyect/usdt-senales && ./run.sh")
    b(doc, "Se abre solo el navegador en http://127.0.0.1:8790 (si no, entrá a mano en Chrome).")
    b(doc, "Dejar la terminal abierta mientras lo usás. Para detenerlo: Ctrl+C en esa terminal.")
    b(doc, "Dejarlo vigilando: la página se actualiza sola cada 3 segundos y el libro va en tiempo real.")
    b(doc, "Cuando suene la alerta: aparece el banner verde «OPORTUNO COMPRAR» con las razones y suena un pitido.")
    b(doc, "Para estudiar el comportamiento: probá Sensibilidad Relajada (avisos frecuentes) vs Estricta "
           "(solo el escenario ideal) y compará qué pasa con el precio en los minutos siguientes.")

    h(doc, "7. Cómo funciona por dentro", 1)
    b(doc, "Datos (API pública de Binance, sin claves): velas de 1 minuto con volumen comprador/vendedor "
           "(taker), libro de órdenes de 100 niveles y último precio.")
    b(doc, "Cálculo: se suavizan los volúmenes con medias exponenciales (EMA). Se mide la pendiente de "
           "compra y de venta (% por minuto) y se detecta el cruce de la EMA de compras por encima de la de ventas.")
    b(doc, "Regla de alerta: el cruce es obligatorio. Según la sensibilidad se exigen además una o ambas "
           "caídas/subidas. El libro comprador suma como contexto.")
    b(doc, "Enfriamiento y registro: tras cada aviso hay una espera configurable, y cada alerta queda en la "
           "lista «Alertas» de la página.")
    b(doc, "El libro de órdenes se actualiza por WebSocket (depth20) y el resto se refresca cada 3 segundos; "
           "la señal siempre se calcula con datos de 1 minuto, sin importar la temporalidad que elijas para mirar.")

    h(doc, "8. Consejos de interpretación", 1)
    b(doc, "El ratio B/V y el desbalance del libro se calculan sobre los 20 niveles visibles: son volátiles, "
           "leelos como tendencia y no como verdad absoluta.")
    b(doc, "Si el precio ya subió más de ~0.4% al momento de la alerta, el banner te lo advierte: puede que "
           "estés llegando tarde.")
    b(doc, "Antes de sacar conclusiones, observá varias señales completas (cruce → qué hizo el precio después).")
    b(doc, "Esta herramienta es de observación y aprendizaje. No es consejo de inversión.")

    h(doc, "9. Problemas comunes", 1)
    tabla(doc, [
        ("La página dice «sin conexión con el servidor local»", "El servidor no está corriendo. Ejecutá de nuevo: cd /home/jma/Documents/Proyect/usdt-senales && ./run.sh  (la página se reconecta sola)."),
        ("La página quedó vieja o no cambia", "Probá F5. Si sigue igual, revisá la terminal del servidor."),
        ("«Address already in use» al arrancar", "Ya hay otra instancia corriendo. Cerrá la anterior con Ctrl+C o pkill -f \"[a]pp.py\" y volvé a iniciar."),
        ("Nunca suena la alerta", "Es normal si no hay cruce: la alerta exige el cruce. Para probar, poné Sensibilidad Relajada o bajá los umbrales."),
        ("No se ve el libro o los gráficos", "Revisá la conexión a internet: los datos vienen de Binance en vivo."),
    ], ["Problema", "Solución"])

    h(doc, "10. Aviso", 1)
    p(doc, "Herramienta de observación. Las señales pueden fallar: el mercado no es determinístico. "
           "Usala como apoyo y nunca como única razón para operar.")

    doc.save(DESTINO)
    try:
        shutil.copy(DESTINO, os.path.join(ESCRITORIO, os.path.basename(DESTINO)))
        print("Copia en el Escritorio:", os.path.join(ESCRITORIO, os.path.basename(DESTINO)))
    except Exception as e:
        print("(no se pudo copiar al Escritorio:", e, ")")
    print("Documento generado:", DESTINO)


if __name__ == "__main__":
    main()
