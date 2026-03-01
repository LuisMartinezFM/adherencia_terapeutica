# =============================================================
# data/queries.py — Intento 2
# SQL puro. Sin lógica Python. Schema: ingenieria
# =============================================================

LISTA_USUARIOS = """
SELECT id_usuario, nombre
FROM ingenieria.usuario
ORDER BY id_usuario;
"""

# KPIs en una sola query por mes
KPIS_MES = """
SELECT
    COUNT(*) FILTER (WHERE e.estado = 'tomado')                           AS tomadas,
    COUNT(*)                                                               AS totales,
    COUNT(*) FILTER (WHERE e.estado = 'tomado'
                       AND e.modo_operativo = 'online')  * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE e.modo_operativo = 'online'), 0)  AS adh_online,
    COUNT(*) FILTER (WHERE e.estado = 'tomado'
                       AND e.modo_operativo = 'offline') * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE e.modo_operativo = 'offline'), 0) AS adh_offline,
    ROUND(
        AVG(EXTRACT(EPOCH FROM (e.alarma_confirmacion - e.alarma_programada)) / 60)
        FILTER (WHERE e.estado = 'tomado')::numeric, 1
    ) AS tiempo_respuesta
FROM ingenieria.evento_adherencia e
JOIN ingenieria.tratamiento t ON e.id_tratamiento = t.id_tratamiento
JOIN ingenieria.usuario u     ON t.id_usuario     = u.id_usuario
WHERE EXTRACT(YEAR  FROM e.alarma_programada) = :year
  AND EXTRACT(MONTH FROM e.alarma_programada) = :month
  AND t.id_medicamento != 0
  AND (:id_usuario = 0 OR u.id_usuario = :id_usuario);
"""

ADHERENCIA_HISTORICA = """
SELECT
    COUNT(*) FILTER (WHERE e.estado = 'tomado') * 1.0 / NULLIF(COUNT(*), 0) AS tasa
FROM ingenieria.evento_adherencia e
JOIN ingenieria.tratamiento t ON e.id_tratamiento = t.id_tratamiento
JOIN ingenieria.usuario u     ON t.id_usuario     = u.id_usuario
WHERE t.id_medicamento != 0
  AND (:id_usuario = 0 OR u.id_usuario = :id_usuario);
"""

TOMAS_POR_DIA_MES = """
SELECT
    DATE(e.alarma_programada) AS fecha,
    e.estado,
    COUNT(*) AS total
FROM ingenieria.evento_adherencia e
JOIN ingenieria.tratamiento t ON e.id_tratamiento = t.id_tratamiento
JOIN ingenieria.usuario u     ON t.id_usuario     = u.id_usuario
WHERE EXTRACT(YEAR  FROM e.alarma_programada) = :year
  AND EXTRACT(MONTH FROM e.alarma_programada) = :month
  AND t.id_medicamento != 0
  AND (:id_usuario = 0 OR u.id_usuario = :id_usuario)
GROUP BY DATE(e.alarma_programada), e.estado
ORDER BY fecha;
"""

EVENTOS_DIA = """
SELECT
    e.alarma_programada,
    e.alarma_confirmacion,
    e.estado,
    e.modo_operativo,
    c.codigo_fisico
FROM ingenieria.evento_adherencia e
JOIN ingenieria.tratamiento t ON e.id_tratamiento = t.id_tratamiento
JOIN ingenieria.casilla c     ON t.id_casilla     = c.id_casilla
JOIN ingenieria.usuario u     ON t.id_usuario     = u.id_usuario
WHERE DATE(e.alarma_programada) = :fecha
  AND t.id_medicamento != 0
  AND (:id_usuario = 0 OR u.id_usuario = :id_usuario)
ORDER BY e.alarma_programada;
"""

TOMAS_POR_CASILLA_MES = """
SELECT
    c.codigo_fisico,
    COUNT(*)                                     AS programadas,
    COUNT(*) FILTER (WHERE e.estado = 'tomado') AS tomadas
FROM ingenieria.evento_adherencia e
JOIN ingenieria.tratamiento t ON e.id_tratamiento = t.id_tratamiento
JOIN ingenieria.casilla c     ON t.id_casilla     = c.id_casilla
JOIN ingenieria.usuario u     ON t.id_usuario     = u.id_usuario
WHERE EXTRACT(YEAR  FROM e.alarma_programada) = :year
  AND EXTRACT(MONTH FROM e.alarma_programada) = :month
  AND t.id_medicamento != 0
  AND (:id_usuario = 0 OR u.id_usuario = :id_usuario)
GROUP BY c.codigo_fisico
ORDER BY c.codigo_fisico;
"""

TOMAS_POR_CASILLA_DIA = """
SELECT
    c.codigo_fisico,
    COUNT(*)                                     AS programadas,
    COUNT(*) FILTER (WHERE e.estado = 'tomado') AS tomadas
FROM ingenieria.evento_adherencia e
JOIN ingenieria.tratamiento t ON e.id_tratamiento = t.id_tratamiento
JOIN ingenieria.casilla c     ON t.id_casilla     = c.id_casilla
JOIN ingenieria.usuario u     ON t.id_usuario     = u.id_usuario
WHERE DATE(e.alarma_programada) = :fecha
  AND t.id_medicamento != 0
  AND (:id_usuario = 0 OR u.id_usuario = :id_usuario)
GROUP BY c.codigo_fisico
ORDER BY c.codigo_fisico;
"""