# =============================================================
# services/pipeline.py — Intento 2
# Orquestador con caché. cache se inyecta desde app.py.
# =============================================================

import pandas as pd
from sqlalchemy import text
from config.database import get_engine
from data.queries import (
    LISTA_USUARIOS, KPIS_MES, ADHERENCIA_HISTORICA,
    TOMAS_POR_DIA_MES, EVENTOS_DIA, TOMAS_POR_CASILLA_MES,
    TOMAS_POR_CASILLA_DIA,
)

cache = None

def init_cache(c):
    global cache
    cache = c

def _run(query, params=None):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})

def load_usuarios():
    return _run(LISTA_USUARIOS)

def load_kpis_mes(id_usuario, year, month):
    key = f"kpis_{id_usuario}_{year}_{month}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    row     = _run(KPIS_MES, {"id_usuario": id_usuario, "year": year, "month": month}).iloc[0]
    tomadas = int(row["tomadas"] or 0)
    totales = int(row["totales"] or 0)
    result  = {
        "tomadas":          tomadas,
        "totales":          totales,
        "adh_general":      round(tomadas / totales * 100, 1) if totales > 0 else 0.0,
        "adh_online":       round(float(row["adh_online"]  or 0) * 100, 1),
        "adh_offline":      round(float(row["adh_offline"] or 0) * 100, 1),
        "tiempo_respuesta": round(float(row["tiempo_respuesta"] or 0), 1),
    }
    cache.set(key, result, timeout=300)
    return result

def load_adherencia_historica(id_usuario):
    key = f"hist_{id_usuario}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    row    = _run(ADHERENCIA_HISTORICA, {"id_usuario": id_usuario}).iloc[0]
    result = round(float(row["tasa"] or 0) * 100, 1)
    cache.set(key, result, timeout=300)
    return result

def load_tomas_por_dia(id_usuario, year, month):
    key = f"cal_{id_usuario}_{year}_{month}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    df = _run(TOMAS_POR_DIA_MES, {"id_usuario": id_usuario, "year": year, "month": month})
    cache.set(key, df, timeout=300)
    return df

def load_eventos_dia(id_usuario, fecha):
    key = f"dia_{id_usuario}_{fecha}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    df = _run(EVENTOS_DIA, {"id_usuario": id_usuario, "fecha": fecha})
    cache.set(key, df, timeout=300)
    return df

def _preparar_meds(df):
    """Normaliza el DataFrame de medicamentos — siempre 6 filas."""
    # Normalizar codigo_fisico a formato med_N sin importar cómo venga de la BD
    def normalizar(cod):
        # "Med1" → "med_1", "med_1" → "med_1", "med1" → "med_1"
        import re
        n = re.search(r"\d+", str(cod))
        return f"med_{n.group()}" if n else cod
    df["codigo_fisico"] = df["codigo_fisico"].apply(normalizar)

    base = pd.DataFrame({"codigo_fisico": [f"med_{i}" for i in range(1, 7)]})
    df   = base.merge(df, on="codigo_fisico", how="left").fillna(0)
    df["tomadas"]      = df["tomadas"].astype(int)
    df["programadas"]  = df["programadas"].astype(int)
    df["etiqueta"]     = df["codigo_fisico"].str.replace("med_", "Medicamento ", regex=False)
    df["num"]          = df["codigo_fisico"].str.replace("med_", "", regex=False)
    return df

def load_medicamentos_mes(id_usuario, year, month):
    key = f"meds_v2_{id_usuario}_{year}_{month}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    df  = _run(TOMAS_POR_CASILLA_MES, {"id_usuario": id_usuario, "year": year, "month": month})
    df  = _preparar_meds(df)
    cache.set(key, df, timeout=300)
    return df

def load_medicamentos_dia(id_usuario, fecha):
    key = f"meds_dia_{id_usuario}_{fecha}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    df  = _run(TOMAS_POR_CASILLA_DIA, {"id_usuario": id_usuario, "fecha": fecha})
    df  = _preparar_meds(df)
    cache.set(key, df, timeout=300)
    return df