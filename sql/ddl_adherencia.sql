-- =============================================================
-- DB_Adherencia_Terapeutica
-- DDL PostgreSQL — Modelo relacional normalizado (3FN)
-- =============================================================

CREATE SCHEMA IF NOT EXISTS "Ingenieria";
SET search_path TO "Ingenieria";


-- -------------------------------------------------------------
-- TABLA: usuario
-- -------------------------------------------------------------
CREATE TABLE usuario (
    id_usuario      SERIAL          PRIMARY KEY,
    nombre          VARCHAR(100)    NOT NULL,
    fecha_registro  DATE            NOT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);


-- -------------------------------------------------------------
-- TABLA: casilla
-- Cada usuario tiene sus propias 6 casillas (Med1 … Med6).
-- El estado de ocupación se infiere desde tratamiento.
-- -------------------------------------------------------------
CREATE TABLE casilla (
    id_casilla      SERIAL          PRIMARY KEY,
    id_usuario      INT             NOT NULL REFERENCES usuario(id_usuario),
    codigo_fisico   VARCHAR(10)     NOT NULL
                                    CHECK (codigo_fisico IN ('Med1','Med2','Med3','Med4','Med5','Med6')),

    CONSTRAINT uq_usuario_casilla UNIQUE (id_usuario, codigo_fisico)
);


-- -------------------------------------------------------------
-- TABLA: medicamento
-- id=0: valor especial para casillas libres (sin medicamento)
-- nombre_medicamento: etiqueta manual que el usuario escribe
-- nota: nombre simbólico o descripción libre
-- -------------------------------------------------------------
CREATE TABLE medicamento (
    id_medicamento      INT             PRIMARY KEY,
    nombre_medicamento  VARCHAR(150)    NOT NULL,
    nota                VARCHAR(255)    DEFAULT NULL
);


-- -------------------------------------------------------------
-- TABLA: dosis_catalogo
--   1 = media pastilla
--   2 = una pastilla entera
--   3 = una y media pastilla
--   4 = dos pastillas
--   5 = inyección / aplicación
-- -------------------------------------------------------------
CREATE TABLE dosis_catalogo (
    id_dosis        INT             PRIMARY KEY CHECK (id_dosis BETWEEN 1 AND 5),
    descripcion     VARCHAR(50)     NOT NULL
);

INSERT INTO dosis_catalogo (id_dosis, descripcion) VALUES
    (1, 'Media pastilla'),
    (2, 'Una pastilla entera'),
    (3, 'Una y media pastilla'),
    (4, 'Dos pastillas'),
    (5, 'Inyección / aplicación');


-- -------------------------------------------------------------
-- TABLA: tratamiento
-- Entidad central. Une usuario + medicamento + casilla.
-- id_medicamento = 0 → casilla libre, no genera eventos.
-- ventana_minutos: minutos que tiene el usuario para confirmar.
-- -------------------------------------------------------------
CREATE TABLE tratamiento (
    id_tratamiento          SERIAL          PRIMARY KEY,
    id_usuario              INT             NOT NULL REFERENCES usuario(id_usuario),
    id_medicamento          INT             NOT NULL REFERENCES medicamento(id_medicamento),
    id_casilla              INT             NOT NULL REFERENCES casilla(id_casilla),

    tipo_tratamiento        VARCHAR(10)     NOT NULL
                                            CHECK (tipo_tratamiento IN ('cronico', 'temporal')),
    estado_tratamiento      VARCHAR(15)     NOT NULL DEFAULT 'activo'
                                            CHECK (estado_tratamiento IN ('activo', 'finalizado')),

    inicio_muestra          DATE            NOT NULL,
    fecha_inicio_tratamiento DATE           DEFAULT NULL,
    fecha_fin               DATE            DEFAULT NULL,

    hora_inicio             INT             NOT NULL CHECK (hora_inicio BETWEEN 0 AND 23),
    minuto_inicio           INT             NOT NULL CHECK (minuto_inicio BETWEEN 0 AND 59),
    frecuencia_horas        INT             NOT NULL CHECK (frecuencia_horas > 0),
    ventana_minutos         INT             NOT NULL DEFAULT 30 CHECK (ventana_minutos > 0),
    dosis                   INT             NOT NULL REFERENCES dosis_catalogo(id_dosis),

    nota_medicamento        VARCHAR(255)    DEFAULT NULL,
    created_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ux_casilla_activa
    ON tratamiento (id_casilla)
    WHERE estado_tratamiento = 'activo';


-- -------------------------------------------------------------
-- TABLA: evento_adherencia
-- alarma_programada: momento en que el sistema dispara la alarma
-- alarma_confirmacion: momento en que el usuario responde
-- Nota: 'fuera_ventana' reservado para versiones futuras
-- -------------------------------------------------------------
CREATE TABLE evento_adherencia (
    id_evento               SERIAL          PRIMARY KEY,
    id_tratamiento          INT             NOT NULL REFERENCES tratamiento(id_tratamiento),

    alarma_programada       TIMESTAMP       NOT NULL,
    alarma_confirmacion     TIMESTAMP       DEFAULT NULL,

    estado                  VARCHAR(15)     NOT NULL
                                            CHECK (estado IN ('tomado', 'omitido', 'fuera_ventana')),
    modo_operativo          VARCHAR(10)     NOT NULL
                                            CHECK (modo_operativo IN ('online', 'offline')),

    created_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);
