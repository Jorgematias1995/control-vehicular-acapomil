"""
Acceso a las tablas de Supabase (PostgreSQL) del proyecto del curso.
Todas las consultas a tablas de la app están aquí.

- El cliente se crea una sola vez por servidor (@st.cache_resource).
- Las lecturas se guardan 15 s en caché (@st.cache_data) para no consultar
  la base en cada clic; después de cada escritura se limpia la caché para
  que todos los perfiles vean el dato nuevo al instante.
- Credenciales: .streamlit/secrets.toml, sección [supabase] (fuera del repo).
"""

import streamlit as st
from supabase import Client, create_client

from modulos import reglas

TTL = 15  # segundos


@st.cache_resource
def cliente() -> Client:
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["key"])


def limpiar_cache() -> None:
    st.cache_data.clear()


def _completar_vehiculo(v: dict) -> dict:
    """La base es compartida: si alguien dejó campos vacíos, se usan los valores por defecto."""
    v["kilometraje_actual"] = v.get("kilometraje_actual") or 0
    v["estado_operativo"] = v.get("estado_operativo") or "Operativo"
    return v


# ---------------------------------------------------------------------------
# Lecturas
# ---------------------------------------------------------------------------
@st.cache_data(ttl=TTL, show_spinner=False)
def vehiculos() -> list[dict]:
    filas = cliente().table("vehiculos").select("*").order("patente").execute().data or []
    return [_completar_vehiculo(v) for v in filas]


@st.cache_data(ttl=TTL, show_spinner=False)
def conductores() -> list[dict]:
    return (cliente().table("conductores").select("*")
            .order("nombre_completo").execute().data or [])


@st.cache_data(ttl=TTL, show_spinner=False)
def vehiculo_con_autorizaciones(patente: str) -> dict | None:
    """
    CONSULTA CRUZADA de la garita: una sola llamada a la API trae el vehículo,
    sus autorizaciones y los datos de cada conductor autorizado.
    PostgREST hace los JOIN siguiendo las llaves foráneas
    autorizaciones.patente -> vehiculos.patente y
    autorizaciones.rut_conductor -> conductores.rut. Equivale a:

        SELECT v.*, a.vigente, a.rut_conductor, c.*
          FROM vehiculos v
          LEFT JOIN autorizaciones a ON a.patente = v.patente
          LEFT JOIN conductores   c ON c.rut = a.rut_conductor
         WHERE v.patente = :patente;
    """
    filas = (cliente().table("vehiculos")
             .select("*, autorizaciones(vigente, rut_conductor, conductores(*))")
             .eq("patente", patente).limit(1).execute().data)
    return _completar_vehiculo(filas[0]) if filas else None


@st.cache_data(ttl=TTL, show_spinner=False)
def vehiculos_autorizados(rut: str) -> list[dict]:
    """Vehículos que el conductor tiene autorizados y vigentes."""
    filas = (cliente().table("autorizaciones")
             .select("vigente, vehiculos(*)")
             .eq("rut_conductor", rut).eq("vigente", True).execute().data or [])
    unicos = {f["vehiculos"]["patente"]: _completar_vehiculo(f["vehiculos"])
              for f in filas if f.get("vehiculos")}
    return [unicos[p] for p in sorted(unicos)]


@st.cache_data(ttl=TTL, show_spinner=False)
def reportes(patente: str | None = None, rut: str | None = None, limite: int | None = None) -> list[dict]:
    q = (cliente().table("reportes_estado")
         .select("*, conductores(nombre_completo, grado_o_cargo)")
         .order("fecha_reporte", desc=True))
    if patente:
        q = q.eq("patente", patente)
    if rut:
        q = q.eq("rut_conductor", rut)
    if limite:
        q = q.limit(limite)
    filas = q.execute().data or []
    for r in filas:
        r["resultado"] = reglas.leer_resultado(r)
    return filas


# ---------------------------------------------------------------------------
# Escrituras
# ---------------------------------------------------------------------------
def registrar_reporte(datos: dict) -> dict:
    fila = cliente().table("reportes_estado").insert(datos).execute().data[0]
    limpiar_cache()
    return fila


def aplicar_reporte_a_vehiculo(vehiculo: dict, kilometraje: int, resultado: str) -> str:
    """
    LÓGICA AUTOMÁTICA después de cada reporte del conductor:
      - kilometraje_actual := kilometraje informado (si es mayor);
      - si el reporte es CRITICO y el vehículo estaba operativo,
        estado_operativo := 'Requiere Mantención'.
    Volver a 'Operativo' lo decide el Puesto de Mando (módulo JEM).
    Devuelve el estado con que quedó el vehículo.
    """
    cambios = {}
    if kilometraje > (vehiculo.get("kilometraje_actual") or 0):
        cambios["kilometraje_actual"] = kilometraje
    estado = vehiculo["estado_operativo"]
    if resultado == "CRITICO" and reglas.es_operativo(estado):
        estado = cambios["estado_operativo"] = "Requiere Mantención"
    if cambios:
        cliente().table("vehiculos").update(cambios).eq("patente", vehiculo["patente"]).execute()
        limpiar_cache()
    return estado


def cambiar_estado_vehiculo(patente: str, estado: str) -> int:
    filas = (cliente().table("vehiculos").update({"estado_operativo": estado})
             .eq("patente", patente).execute().data or [])
    limpiar_cache()
    return len(filas)
