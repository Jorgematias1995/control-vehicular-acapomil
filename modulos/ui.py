"""Utilidades de presentación: horas en Chile, chips de color, tarjetas."""

from datetime import datetime, timedelta, timezone

import pandas as pd

try:
    from zoneinfo import ZoneInfo
    ZONA_CHILE = ZoneInfo("America/Santiago")
except Exception:                       # Windows sin el paquete tzdata
    ZONA_CHILE = timezone(timedelta(hours=-3))


def a_hora_chile(serie: pd.Series) -> pd.Series:
    """Convierte fechas ISO en UTC (como las guarda Supabase) a hora de Chile."""
    return pd.to_datetime(serie, utc=True, format="ISO8601").dt.tz_convert(ZONA_CHILE)


def fecha_corta(iso: str | None) -> str:
    if not iso:
        return "—"
    fecha = pd.to_datetime(iso, utc=True, format="ISO8601").tz_convert(ZONA_CHILE)
    return fecha.strftime("%d-%m-%Y %H:%M")


def hoy_chile():
    return datetime.now(ZONA_CHILE).date()


def chip(texto: str, color: str) -> str:
    """Etiqueta de color en HTML (usar con st.markdown(..., unsafe_allow_html=True))."""
    return (f"<span style='background:{color};color:#fff;padding:2px 10px;"
            f"border-radius:999px;font-size:0.85em;font-weight:600;white-space:nowrap'>{texto}</span>")


def texto(valor) -> str:
    """Texto seguro desde pandas: None/NaN -> ''."""
    return valor if isinstance(valor, str) else ""


def miles(n) -> str:
    """45200 -> '45.200' (formato chileno)."""
    return f"{int(n):,}".replace(",", ".")
