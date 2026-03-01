# =============================================================
# app.py — Intento 2  |  Flask + Plotly + SimpleCache
# =============================================================

import calendar
import json
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
from flask import Flask, jsonify, render_template, request
from flask_caching import Cache

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from services.pipeline import (
    init_cache,
    load_usuarios,
    load_kpis_mes,
    load_adherencia_historica,
    load_tomas_por_dia,
    load_eventos_dia,
    load_medicamentos_mes,
    load_medicamentos_dia,
)

# ── App & Caché ───────────────────────────────────────────────
app = Flask(__name__)
app.config["CACHE_TYPE"]             = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"]  = 300

cache = Cache(app)
init_cache(cache)

# ── Helpers ───────────────────────────────────────────────────
MESES_ES = {
    1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril",
    5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto",
    9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
}

def _color_dia(pct):
    """Retorna clase CSS según porcentaje de adherencia."""
    if pct is None:   return "sin-datos"
    if pct == 100.0:  return "excelente"
    if pct >= 80:     return "bueno"
    if pct >= 60:     return "regular"
    return "malo"

def _build_calendario(id_usuario, year, month):
    """Construye la estructura de semanas para el template HTML."""
    df = load_tomas_por_dia(id_usuario, year, month)

    # Pivot: fecha → {tomado: N, omitido: N, ...}
    pivot = {}
    for _, row in df.iterrows():
        f = str(row["fecha"])
        if f not in pivot:
            pivot[f] = {}
        pivot[f][row["estado"]] = int(row["total"])

    # Calcular porcentaje por día
    dias_data = {}
    for fecha_str, estados in pivot.items():
        tomados = estados.get("tomado", 0)
        total   = sum(estados.values())
        pct     = round(tomados / total * 100, 1) if total > 0 else None
        dias_data[fecha_str] = {"pct": pct, "tomados": tomados, "total": total}

    # Estructura semanas para el template (lun-dom)
    cal = calendar.monthcalendar(year, month)
    semanas = []
    for semana in cal:
        dias = []
        for dia_num in semana:
            if dia_num == 0:
                dias.append(None)
            else:
                fecha_str = f"{year}-{month:02d}-{dia_num:02d}"
                info = dias_data.get(fecha_str)
                dias.append({
                    "num":    dia_num,
                    "fecha":  fecha_str,
                    "pct":    info["pct"]    if info else None,
                    "label":  f"{info['pct']}%" if info and info["pct"] is not None else "—",
                    "clase":  _color_dia(info["pct"] if info else None),
                })
        semanas.append(dias)
    return semanas

def _build_grafica_medicamentos(df, titulo="Tomas por medicamento"):
    """
    Eje Y: C1-C6. Eje X: dosis absolutas.
    Rojo = tomadas (nombre medicamento dentro).
    Azul = omitidas (etiqueta tomadas/programadas dentro).
    """
    df = df.copy()
    df["casilla"]  = df["num"].apply(lambda n: f"C{n}")
    df["omitidas"] = (df["programadas"] - df["tomadas"]).clip(lower=0)
    max_val = int(df["programadas"].max()) if df["programadas"].max() > 0 else 5

    COLOR_TOMADAS  = "#C0392B"   # rojo
    COLOR_OMITIDAS = "#2E4BC6"   # azul

    fig = go.Figure()

    # Barra roja — tomadas, nombre del medicamento dentro
    fig.add_trace(go.Bar(
        x=df["tomadas"],
        y=df["casilla"],
        orientation="h",
        marker=dict(color=COLOR_TOMADAS),
        text=df["etiqueta"],
        textposition="inside",
        insidetextanchor="start",
        textfont=dict(color="rgba(255,255,255,0.9)", size=11,
                      family="DM Sans, sans-serif"),
        showlegend=False,
        hovertemplate="%{y} — %{text}: %{x} tomadas<extra></extra>",
        cliponaxis=False,
    ))

    # Barra azul — omitidas, etiqueta tomadas/programadas dentro
    fig.add_trace(go.Bar(
        x=df["omitidas"],
        y=df["casilla"],
        orientation="h",
        marker=dict(color=COLOR_OMITIDAS),
        text=[
            f"{int(r['tomadas'])}/{int(r['programadas'])}" if r["omitidas"] > 0 else ""
            for _, r in df.iterrows()
        ],
        textposition="inside",
        insidetextanchor="start",
        textfont=dict(color="rgba(255,255,255,0.9)", size=11,
                      family="Space Mono, monospace"),
        showlegend=False,
        hovertemplate="%{y}: %{x} omitidas<extra></extra>",
    ))

    # Si omitidas = 0 (100% adherencia), etiqueta fuera de barra roja
    for _, row in df.iterrows():
        if row["omitidas"] == 0 and row["programadas"] > 0:
            fig.add_annotation(
                x=int(row["tomadas"]) + max_val * 0.02,
                y=row["casilla"],
                text=f"{int(row['tomadas'])}/{int(row['programadas'])}",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(color="rgba(255,255,255,0.6)", size=11,
                          family="Space Mono, monospace"),
            )

    # Sin datos — figura vacía con mensaje centrado
    if max_val == 0 or df["programadas"].sum() == 0:
        fig_vacia = go.Figure()
        fig_vacia.add_annotation(
            x=0.5, y=0.5, xref="paper", yref="paper",
            text="<b>SIN DATOS</b>",
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.3)", size=18,
                      family="DM Sans, sans-serif"),
        )
        fig_vacia.update_layout(
            paper_bgcolor="#0C0C0F", plot_bgcolor="#13131A",
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            margin=dict(t=40, b=10, l=10, r=10),
            title=dict(text=titulo,
                       font=dict(color="#E8E8F0", size=14,
                                 family="DM Sans, sans-serif"),
                       x=0.5, xanchor="center"),
        )
        return json.loads(fig_vacia.to_json())

    # Escala dinámica: máximo programado + 15%
    x_max  = max_val * 1.15
    dtick  = max(1, round(max_val / 5))

    fig.update_layout(
        barmode="stack",
        title=dict(
            text=titulo,
            font=dict(color="#E8E8F0", size=14, family="DM Sans, sans-serif"),
            x=0.5, xanchor="center"
        ),
        xaxis=dict(
            visible=True,
            autorange=False,
            range=[0, x_max],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            tickfont=dict(color="rgba(255,255,255,0.35)", size=10,
                          family="Space Mono, monospace"),
            tickmode="linear",
            tick0=0,
            dtick=dtick,
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.1)",
        ),
        yaxis=dict(
            showticklabels=True,
            tickfont=dict(color="rgba(255,255,255,0.7)", size=12,
                          family="Space Mono, monospace"),
            automargin=True,
            categoryorder="array",
            categoryarray=["C1","C2","C3","C4","C5","C6"],
        ),
        paper_bgcolor="#0C0C0F",
        plot_bgcolor="#13131A",
        font=dict(color="#E8E8F0", family="DM Sans, sans-serif"),
        margin=dict(t=40, b=35, l=10, r=20),
        bargap=0.25,
    )
    return json.loads(fig.to_json())


def _build_grafica_mes(id_usuario, year, month):
    df = load_medicamentos_mes(id_usuario, year, month)
    return _build_grafica_medicamentos(df, "Tomas por medicamento")


def _build_grafica_dia_meds(id_usuario, fecha):
    df = load_medicamentos_dia(id_usuario, fecha)
    return _build_grafica_medicamentos(df, f"Tomas — {fecha}")

# ── Rutas ─────────────────────────────────────────────────────

@app.route("/")
def index():
    hoy       = date.today()
    usuarios  = load_usuarios().to_dict("records")
    return render_template("index.html",
        usuarios   = usuarios,
        year       = hoy.year,
        month      = hoy.month,
        id_usuario = 0,
    )


@app.route("/api/dashboard")
def api_dashboard():
    """Endpoint principal — devuelve todos los datos del dashboard en JSON."""
    id_usuario = int(request.args.get("id_usuario", 0))
    year       = int(request.args.get("year",       date.today().year))
    month      = int(request.args.get("month",      date.today().month))

    kpis        = load_kpis_mes(id_usuario, year, month)
    historica   = load_adherencia_historica(id_usuario)
    semanas     = _build_calendario(id_usuario, year, month)
    meds_df  = load_medicamentos_mes(id_usuario, year, month)
    meds_data = [
        {
            "casilla":     f"C{row['num']}",
            "medicamento": row["etiqueta"],
            "tomadas":     int(row["tomadas"]),
            "programadas": int(row["programadas"]),
        }
        for _, row in meds_df.iterrows()
    ]

    return jsonify({
        "kpis":       kpis,
        "historica":  historica,
        "titulo_mes": f"{MESES_ES[month]} {year}",
        "semanas":    semanas,
        "meds":       meds_data,
    })


@app.route("/api/dia")
def api_dia():
    """Vista de día — eventos individuales."""
    id_usuario = int(request.args.get("id_usuario", 0))
    fecha      = request.args.get("fecha")

    if not fecha:
        return jsonify({"error": "fecha requerida"}), 400

    df      = load_eventos_dia(id_usuario, fecha)
    eventos = []
    for _, row in df.iterrows():
        programada    = row["alarma_programada"]
        confirmacion  = row["alarma_confirmacion"]
        minutos       = None
        if pd.notna(confirmacion) and row["estado"] == "tomado":
            minutos = round((confirmacion - programada).total_seconds() / 60, 1)
        eventos.append({
            "hora":          programada.strftime("%H:%M") if pd.notna(programada) else "—",
            "estado":        row["estado"],
            "modo":          row["modo_operativo"],
            "casilla":       row["codigo_fisico"].replace("med_", ""),
            "minutos":       minutos,
        })

    tomados  = sum(1 for e in eventos if e["estado"] == "tomado")
    total    = len(eventos)
    pct      = round(tomados / total * 100, 1) if total > 0 else 0

    meds_df  = load_medicamentos_dia(id_usuario, fecha)
    meds_data = [
        {
            "casilla":     f"C{row['num']}",
            "medicamento": row["etiqueta"],
            "tomadas":     int(row["tomadas"]),
            "programadas": int(row["programadas"]),
        }
        for _, row in meds_df.iterrows()
    ]

    return jsonify({
        "fecha":   fecha,
        "eventos": eventos,
        "resumen": {"tomados": tomados, "total": total, "pct": pct},
        "meds":    meds_data,
    })


if __name__ == "__main__":
    app.run(debug=True, port=8050)