"""
explorar_bd.py · Sesión 12 (Programación Avanzada)

Responde "¿Qué tiene cada tabla?" del proyecto Supabase de la clase:
  - columnas, tipo, llave primaria (PK), llaves foráneas (FK) y obligatorias
  - cantidad de filas y una fila de ejemplo
  - buckets de Storage (límite de tamaño, tipos permitidos)
Además descarga cada tabla a CSV en la carpeta datos_clase12/.

Uso (en la carpeta del proyecto, con el entorno virtual activado):
    python scripts/explorar_bd.py

Lee la URL y la key desde .streamlit/secrets.toml, sección [supabase].
Solo LEE: no modifica nada en la base.
"""

import json
import re
import urllib.request
from pathlib import Path

import pandas as pd
from supabase import create_client

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import toml as tomllib  # Python más antiguo (viene con Streamlit)

TABLAS = ["conductores", "vehiculos", "autorizaciones", "reportes_estado"]
BUCKET = "evidencias-vehiculares"
RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "datos_clase12"
SALIDA = RAIZ / "estructura_bd.txt"

secretos = tomllib.loads((RAIZ / ".streamlit" / "secrets.toml").read_text(encoding="utf-8"))
cfg = secretos["supabase"]
URL, KEY = cfg["url"].strip().rstrip("/"), cfg["key"].strip()

lineas = []


def log(texto=""):
    print(texto)
    lineas.append(str(texto))


def campo(obj, nombre):
    """Lee un atributo tanto de un dict como de un objeto."""
    return obj.get(nombre) if isinstance(obj, dict) else getattr(obj, nombre, None)


# 1) Estructura: PostgREST publica un esquema OpenAPI con todas las columnas,
#    incluso de tablas vacías (select * no muestra columnas si no hay filas).
esquema = {}
try:
    req = urllib.request.Request(
        f"{URL}/rest/v1/",
        headers={"apikey": KEY, "Accept": "application/openapi+json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        esquema = json.load(r).get("definitions", {})
except Exception as e:
    log(f"(No se pudo leer el esquema OpenAPI: {e}. Se usaran solo los datos.)")

supabase = create_client(URL, KEY)
CARPETA.mkdir(exist_ok=True)

log(f"Proyecto: {URL}")
otras = sorted(set(esquema) - set(TABLAS))
if otras:
    log(f"Otras tablas/vistas del proyecto: {', '.join(otras)}")

# 2) Tablas: columnas + datos
for tabla in TABLAS:
    log()
    log(f"=== {tabla} ===")
    definicion = esquema.get(tabla)
    if definicion:
        obligatorias = set(definicion.get("required", []))
        for col, info in definicion.get("properties", {}).items():
            tipo = info.get("format") or info.get("type", "?")
            desc = info.get("description", "") or ""
            notas = []
            if "<pk/>" in desc:
                notas.append("PK")
            fk = re.search(r"<fk table='([^']+)' column='([^']+)'/>", desc)
            if fk:
                notas.append(f"FK -> {fk.group(1)}.{fk.group(2)}")
            if col in obligatorias:
                notas.append("obligatoria")
            if "enum" in info:
                notas.append("valores: " + " / ".join(map(str, info["enum"])))
            if "default" in info:
                notas.append(f"default {info['default']}")
            if "maxLength" in info:
                notas.append(f"max {info['maxLength']} car.")
            log(f"  {col:<26} {tipo:<30} {'  '.join(notas)}")
    elif esquema:
        log("  (la tabla no aparece en el esquema: revisa el nombre en el Table Editor)")

    try:
        datos = supabase.table(tabla).select("*").execute().data
    except Exception as e:
        log(f"  ERROR al leer datos: {e}")
        continue

    if not definicion and datos:
        log("  Columnas (deducidas de los datos): " + ", ".join(datos[0].keys()))
    log(f"  Filas: {len(datos)}")
    if datos:
        pd.DataFrame(datos).to_csv(CARPETA / f"{tabla}.csv", index=False, encoding="utf-8-sig")
        log(f"  Ejemplo: {datos[0]}")

# 3) Storage
log()
log("=== Storage ===")
try:
    for b in supabase.storage.list_buckets():
        log(
            f"  bucket {campo(b, 'name')}: publico={campo(b, 'public')}, "
            f"limite_bytes={campo(b, 'file_size_limit')}, tipos={campo(b, 'allowed_mime_types')}"
        )
    archivos = supabase.storage.from_(BUCKET).list()
    nombres = [campo(a, "name") for a in archivos[:10]]
    log(f"  {BUCKET}: {len(archivos)} elementos en la raiz -> {', '.join(map(str, nombres))}")
except Exception as e:
    log(f"  ERROR al leer Storage: {e}")

SALIDA.write_text("\n".join(lineas), encoding="utf-8")
print(f"\nListo: {SALIDA.name} y la carpeta {CARPETA.name}/ con un CSV por tabla.")
