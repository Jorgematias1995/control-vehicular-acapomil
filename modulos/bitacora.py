"""
Bitácora de accesos de la garita, guardada en Supabase Storage.

El proyecto del curso no tiene una tabla de accesos y no se pueden crear tablas
en él, así que cada registro de garita ES su foto de evidencia en el bucket, y
los datos del registro van en el nombre del archivo:

    garita/20261112T134512Z__ABCD-12__ENTRADA__AUTORIZADO__18234567-K__a1b2c3.jpg
           fecha y hora UTC   patente  movimiento resultado  RUT (sin puntos)  código

Ventajas: no hay registro sin foto, el orden por nombre es el orden cronológico
y el Puesto de Mando lee toda la bitácora listando una carpeta del bucket.
"""

import re
import uuid
from datetime import datetime, timezone

import streamlit as st

from modulos import db, evidencias

CARPETA = "garita"
TTL = 15
_NOMBRE = re.compile(
    r"^(?P<fecha>\d{8}T\d{6}Z)__(?P<patente>[A-Z0-9-]{4,10})__(?P<movimiento>ENTRADA|SALIDA)"
    r"__(?P<resultado>AUTORIZADO|ALERTA|DENEGADO)__(?P<rut>\d{1,8}-[\dK])__[0-9a-f]+\.jpg$"
)


def rut_sin_puntos(rut: str) -> str:
    return (rut or "").replace(".", "").upper()


def registrar_acceso(patente: str, rut: str, movimiento: str, resultado: str, foto: bytes) -> str:
    """Sube la foto con los datos del registro en su nombre. Devuelve la ruta."""
    ahora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    nombre = (f"{ahora}__{patente}__{movimiento}__{resultado}__"
              f"{rut_sin_puntos(rut)}__{uuid.uuid4().hex[:6]}.jpg")
    ruta = evidencias.subir(f"{CARPETA}/{nombre}", foto)
    db.limpiar_cache()
    return ruta


@st.cache_data(ttl=TTL, show_spinner=False)
def accesos() -> list[dict]:
    """Todos los registros de garita, del más reciente al más antiguo."""
    bucket = db.cliente().storage.from_(evidencias.BUCKET)
    objetos, desde = [], 0
    while True:
        lote = bucket.list(CARPETA, {"limit": 1000, "offset": desde,
                                     "sortBy": {"column": "name", "order": "desc"}}) or []
        objetos += lote
        if len(lote) < 1000:
            break
        desde += 1000

    rut_con_puntos = {rut_sin_puntos(c["rut"]): c["rut"] for c in db.conductores()}
    registros = []
    for o in objetos:
        m = _NOMBRE.match(o.get("name", ""))
        if not m:                      # archivos de otros programas en la misma carpeta
            continue
        f = m.group("fecha")
        registros.append({
            "fecha_hora": f"{f[0:4]}-{f[4:6]}-{f[6:8]}T{f[9:11]}:{f[11:13]}:{f[13:15]}+00:00",
            "patente": m.group("patente"),
            "movimiento": m.group("movimiento"),
            "resultado": m.group("resultado"),
            "rut_conductor": rut_con_puntos.get(m.group("rut"), m.group("rut")),
            "foto": f"{CARPETA}/{o['name']}",
        })
    registros.sort(key=lambda r: r["fecha_hora"], reverse=True)
    return registros


def accesos_de(patente: str) -> list[dict]:
    return [a for a in accesos() if a["patente"] == patente]


def ultimo_movimiento(patente: str) -> str | None:
    """'ENTRADA' o 'SALIDA' del último registro aceptado (para sugerir el siguiente)."""
    for a in accesos_de(patente):
        if a["resultado"] != "DENEGADO":
            return a["movimiento"]
    return None
