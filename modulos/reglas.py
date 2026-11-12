"""
Lógica de negocio pura (sin Streamlit ni Supabase), fácil de probar.

- evaluar_reporte(): clasifica un reporte del conductor en OK / OBSERVACIONES / CRITICO.
- resolver_acceso(): decide AUTORIZADO / ALERTA / DENEGADO en la garita.
- normalizar_patente(), formato_patente_valido(): formato de patentes.

Los umbrales de presión y batería vienen de la Evaluación 02;
los de aceite y combustible son supuestos documentados en el informe.
"""

import re

# ---------------------------------------------------------------------------
# Umbrales (cambiar aquí si el profesor define otros)
# ---------------------------------------------------------------------------
PRESION_CRITICA = 20.0      # PSI: bajo esto el neumático es falla crítica
PRESION_MINIMA = 25.0       # PSI: bajo esto es observación
ACEITE_CRITICO = 25.0       # %
ACEITE_MINIMO = 50.0        # %
COMBUSTIBLE_MINIMO = 25.0   # % (no inmoviliza, solo observación)
BATERIA_12V_MINIMA = 11.8   # V
BATERIA_24V_MINIMA = 23.6   # V (camiones y vehículos tácticos)
LIMITE_SISTEMA_24V = 18.0   # V: una lectura sobre esto indica sistema de 24 V

ESTADOS_VEHICULO = ["Operativo", "Requiere Mantención", "Crítico"]
COLOR_ESTADO = {            # matriz del Puesto de Mando
    "Operativo": "#1e8e3e",            # verde
    "Requiere Mantención": "#f2a600",  # amarillo
    "Crítico": "#d93025",              # rojo
}
COLOR_RESULTADO_ACCESO = {"AUTORIZADO": "#1e8e3e", "ALERTA": "#f2a600", "DENEGADO": "#d93025"}
RESULTADOS_REPORTE = ("OK", "OBSERVACIONES", "CRITICO")


def grupo_estado(estado: str | None) -> str:
    """
    La base es compartida por todo el curso y estado_operativo es texto libre,
    así que se agrupa cualquier valor en los 3 colores del semáforo.
    """
    texto = (estado or "").strip().lower()
    if texto.startswith("operativo"):           # "No operativo" / "Inoperativo" no califican
        return "Operativo"
    if any(p in texto for p in ("crític", "critic", "inmovil", "baja", "fuera de servicio")):
        return "Crítico"
    return "Requiere Mantención"


def color_estado(estado: str | None) -> str:
    return COLOR_ESTADO[grupo_estado(estado)]


def es_operativo(estado: str | None) -> bool:
    return grupo_estado(estado) == "Operativo"

_PATENTE_NUEVA = re.compile(r"^[A-Z]{4}[0-9]{2}$")   # ABCD12 -> ABCD-12
_PATENTE_ANTIGUA = re.compile(r"^[A-Z]{2}[0-9]{4}$")  # AB1234 -> AB-1234


# ---------------------------------------------------------------------------
# Patentes
# ---------------------------------------------------------------------------
def normalizar_patente(texto: str | None) -> str:
    """'abcd 12', 'ABCD-12', 'ab.cd.12' -> 'ABCD-12'. Si no calza, devuelve el texto limpio."""
    limpio = re.sub(r"[^A-Z0-9]", "", (texto or "").upper())
    if _PATENTE_NUEVA.match(limpio):
        return f"{limpio[:4]}-{limpio[4:]}"
    if _PATENTE_ANTIGUA.match(limpio):
        return f"{limpio[:2]}-{limpio[2:]}"
    return limpio


def formato_patente_valido(patente: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{4}-[0-9]{2}|[A-Z]{2}-[0-9]{4}", patente or ""))


# ---------------------------------------------------------------------------
# Reporte de estado del conductor
# ---------------------------------------------------------------------------
def evaluar_reporte(r: dict) -> tuple[str, list[str]]:
    """
    Recibe los valores del formulario y devuelve (resultado, hallazgos).
    resultado: 'CRITICO' si hay al menos una falla crítica,
               'OBSERVACIONES' si solo hay observaciones, 'OK' si no hay nada.
    """
    criticos: list[str] = []
    observaciones: list[str] = []

    for i in range(1, 5):
        p = float(r[f"presion_rueda_{i}"])
        if p < PRESION_CRITICA:
            criticos.append(f"Rueda {i} a {p:.1f} PSI (mínimo {PRESION_CRITICA:.0f})")
        elif p < PRESION_MINIMA:
            observaciones.append(f"Rueda {i} a {p:.1f} PSI (bajo {PRESION_MINIMA:.0f})")

    aceite = float(r["nivel_aceite"])
    if aceite < ACEITE_CRITICO:
        criticos.append(f"Aceite al {aceite:.0f}% (mínimo {ACEITE_CRITICO:.0f}%)")
    elif aceite < ACEITE_MINIMO:
        observaciones.append(f"Aceite al {aceite:.0f}% (bajo {ACEITE_MINIMO:.0f}%)")

    voltaje = float(r["voltaje_bateria"])
    minimo = BATERIA_24V_MINIMA if voltaje > LIMITE_SISTEMA_24V else BATERIA_12V_MINIMA
    if voltaje < minimo:
        criticos.append(f"Batería en {voltaje:.1f} V (mínimo {minimo} V)")

    if not r.get("frenos", True):
        criticos.append("Falla en sistema de frenos")

    combustible = float(r["nivel_combustible"])
    if combustible < COMBUSTIBLE_MINIMO:
        observaciones.append(f"Combustible al {combustible:.0f}% (bajo {COMBUSTIBLE_MINIMO:.0f}%)")

    for campo, nombre in (("luces_delanteras", "Luces delanteras"),
                          ("luces_traseras", "Luces traseras"),
                          ("balizas", "Balizas")):
        if not r.get(campo, True):
            observaciones.append(f"{nombre} con falla")

    if criticos:
        resultado = "CRITICO"
    elif observaciones:
        resultado = "OBSERVACIONES"
    else:
        resultado = "OK"
    hallazgos = [f"CRÍTICO: {c}" for c in criticos] + observaciones
    return resultado, hallazgos


def _texto(valor) -> str:
    return valor if isinstance(valor, str) else ""      # None o NaN (pandas) -> ""


def componer_observaciones(resultado: str, hallazgos: list[str], detalle: str, novedades: str | None) -> str:
    """
    Arma el texto que se guarda en reportes_estado.observaciones, p. ej.:
    [CRITICO] CRÍTICO: Falla en sistema de frenos | Detalle: Neumáticos 32/32/32/32 PSI · ... | Novedades: ruido
    El prefijo [RESULTADO] permite que el Puesto de Mando vuelva a leer la clasificación.
    """
    partes = [f"[{resultado}] " + ("; ".join(hallazgos) if hallazgos else "Sin hallazgos"),
              f"Detalle: {detalle}"]
    if novedades:
        partes.append(f"Novedades: {novedades}")
    return " | ".join(partes)


def leer_resultado(reporte: dict) -> str:
    """Resultado de un reporte: del prefijo [..] de observaciones o, si otro programa lo
    guardó sin prefijo, de los booleanos de presión y luces."""
    m = re.match(r"^\[(OK|OBSERVACIONES|CRITICO)\]", _texto(reporte.get("observaciones")))
    if m:
        return m.group(1)
    if reporte.get("presion_neumaticos") is False or reporte.get("luces_operativas") is False:
        return "OBSERVACIONES"
    return "OK"


def resumen_hallazgos(reporte: dict) -> str:
    """Solo la parte de hallazgos de observaciones (sin el detalle ni las novedades)."""
    obs = _texto(reporte.get("observaciones"))
    m = re.match(r"^\[(?:OK|OBSERVACIONES|CRITICO)\] ([^|]*)", obs)
    return (m.group(1).strip() if m else obs.strip()) or "Sin observaciones"


def validar_kilometraje(nuevo: int, actual: int) -> str | None:
    """Devuelve un mensaje de error, o None si el kilometraje es válido."""
    if nuevo < actual:
        return f"El kilometraje ({nuevo:,}) no puede ser menor al registrado ({actual:,}).".replace(",", ".")
    return None


# ---------------------------------------------------------------------------
# Control de acceso en garita
# ---------------------------------------------------------------------------
def resolver_acceso(vehiculo: dict | None, conductor: dict | None) -> tuple[str, str]:
    """
    vehiculo: fila de 'vehiculos' con sus 'autorizaciones' anidadas (consulta cruzada).
    conductor: fila de 'conductores'.
    Devuelve (resultado, motivo) con resultado en AUTORIZADO / ALERTA / DENEGADO.
    """
    if vehiculo is None:
        return "DENEGADO", "Patente no registrada en el catálogo de vehículos."
    if conductor is None:
        return "DENEGADO", "Conductor no registrado."
    estado_conductor = conductor.get("estado") or "Activo"      # la columna tiene default 'Activo'
    if estado_conductor.strip().lower() != "activo":
        return "DENEGADO", f"Conductor en estado «{estado_conductor}»."

    autorizaciones = [a for a in vehiculo.get("autorizaciones") or []
                      if a.get("rut_conductor") == conductor["rut"]]
    if not autorizaciones:
        return "DENEGADO", "El conductor no tiene autorización para este vehículo."
    if not any(a.get("vigente") for a in autorizaciones):
        return "DENEGADO", "La autorización del conductor para este vehículo no está vigente."

    estado = vehiculo.get("estado_operativo")
    if not es_operativo(estado):
        return "ALERTA", f"Conductor autorizado, pero el vehículo está en estado «{estado}»."
    return "AUTORIZADO", "Conductor habilitado y vehículo operativo."
