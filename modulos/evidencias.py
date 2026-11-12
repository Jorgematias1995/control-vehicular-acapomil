"""
Evidencias fotográficas en Supabase Storage (bucket público 'evidencias-vehiculares',
máximo 800 KB por archivo).

- comprimir_imagen(): deja la foto en JPEG de máximo 800 KB (límite del bucket).
- subir(): sube la foto a una ruta del bucket.
- url_publica(): dirección web de una foto del bucket (es público).
"""

import io
import uuid
from datetime import datetime, timezone

from PIL import Image, ImageOps

from modulos import db

BUCKET = "evidencias-vehiculares"
MAX_BYTES = 800_000      # el bucket acepta 819.200 bytes (800 KB); se deja margen
LADO_MAXIMO = 1600       # px: suficiente para leer una patente o un odómetro


def comprimir_imagen(datos: bytes, max_bytes: int = MAX_BYTES) -> bytes:
    """Convierte cualquier imagen a JPEG y baja calidad/tamaño hasta pesar <= max_bytes."""
    img = Image.open(io.BytesIO(datos))
    img = ImageOps.exif_transpose(img).convert("RGB")   # respeta la orientación del celular
    img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    while True:
        for calidad in (85, 75, 65, 55, 45):
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=calidad, optimize=True)
            if buffer.tell() <= max_bytes:
                return buffer.getvalue()
        ancho, alto = img.size                            # aún pesa mucho: achicar 25 %
        if ancho < 200 or alto < 200:
            return buffer.getvalue()
        img = img.resize((int(ancho * 0.75), int(alto * 0.75)))


def subir(ruta: str, datos: bytes) -> str:
    """Comprime y sube la foto a 'ruta' dentro del bucket. Devuelve la ruta."""
    db.cliente().storage.from_(BUCKET).upload(ruta, comprimir_imagen(datos), {"content-type": "image/jpeg"})
    return ruta


def subir_foto_reporte(patente: str, datos: bytes) -> str:
    """Foto del odómetro del conductor. Devuelve la URL pública (se guarda en foto_evidencia_url)."""
    ahora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ruta = subir(f"odometros/{patente}/{ahora}_{uuid.uuid4().hex[:6]}.jpg", datos)
    return url_publica(ruta)


def url_publica(ruta_o_url: str | None) -> str | None:
    """Acepta una ruta del bucket o una URL ya armada; None si no hay foto."""
    if not isinstance(ruta_o_url, str) or not ruta_o_url.strip():
        return None
    if ruta_o_url.startswith("http"):
        return ruta_o_url
    return db.cliente().storage.from_(BUCKET).get_public_url(ruta_o_url)
