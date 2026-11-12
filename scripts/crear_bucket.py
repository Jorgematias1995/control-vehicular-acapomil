"""
Crea el bucket 'evidencias-vehiculares' (máximo 800 KB por imagen) en el
proyecto Supabase configurado en .streamlit/secrets.toml.

- Si el bucket NO existe: lo crea (privado, 800 KB, solo JPEG/PNG).
- Si YA existe (por ejemplo, lo creó el profesor o un compañero): no lo
  modifica, solo muestra su configuración. El bucket es compartido.

Uso, desde la carpeta del proyecto y con el entorno virtual activado:
    python scripts/crear_bucket.py
"""

from pathlib import Path

from supabase import create_client

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import toml as tomllib

BUCKET = "evidencias-vehiculares"
LIMITE_BYTES = 800 * 1024            # 800 KB
TIPOS = ["image/jpeg", "image/png"]

raiz = Path(__file__).resolve().parents[1]
cfg = tomllib.loads((raiz / ".streamlit" / "secrets.toml").read_text(encoding="utf-8"))["supabase"]
supabase = create_client(cfg["url"], cfg["key"])


def campo(obj, nombre):
    return obj.get(nombre) if isinstance(obj, dict) else getattr(obj, nombre, None)


existentes = {campo(b, "name"): b for b in supabase.storage.list_buckets()}
print(f"Proyecto: {cfg['url']}")
print(f"Buckets actuales: {', '.join(existentes) or '(ninguno)'}")

if BUCKET in existentes:
    b = existentes[BUCKET]
    print(f"\nEl bucket '{BUCKET}' ya existe; no se modifica.")
    print(f"  público: {campo(b, 'public')} · límite: {campo(b, 'file_size_limit')} bytes · "
          f"tipos: {campo(b, 'allowed_mime_types')}")
else:
    supabase.storage.create_bucket(
        BUCKET,
        options={"public": False, "file_size_limit": LIMITE_BYTES, "allowed_mime_types": TIPOS},
    )
    print(f"\nBucket '{BUCKET}' creado: privado, máximo {LIMITE_BYTES} bytes, tipos {TIPOS}.")
