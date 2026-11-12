"""
Perfil GUARDIA DE GARITA (terreno / móvil).

Flujo: foto de la patente -> OCR (editable) -> conductor -> consulta cruzada
en Supabase -> resolución AUTORIZADO / ALERTA DE ESTADO / DENEGADO ->
registro del movimiento con la foto como evidencia (también los denegados),
en la bitácora de garita del bucket (ver bitacora.py).
"""

import hashlib
import html

import pandas as pd
import streamlit as st

from modulos import bitacora, db, ocr, reglas, ui

TEXTO_RESULTADO = {"AUTORIZADO": "✅ AUTORIZADO", "ALERTA": "⚠️ ALERTA DE ESTADO", "DENEGADO": "⛔ DENEGADO"}


def _banner(resultado: str, motivo: str) -> None:
    color = reglas.COLOR_RESULTADO_ACCESO[resultado]
    st.markdown(
        f"<div style='background:{color};color:#fff;padding:16px;border-radius:12px;"
        f"text-align:center;margin:8px 0'>"
        f"<div style='font-size:1.7em;font-weight:800'>{TEXTO_RESULTADO[resultado]}</div>"
        f"<div style='font-size:1.05em'>{html.escape(motivo)}</div></div>",
        unsafe_allow_html=True,
    )


def _ficha_vehiculo(v: dict) -> None:
    estado = v["estado_operativo"]
    ultimo = (db.reportes(patente=v["patente"], limite=1) or [None])[0]
    with st.container(border=True):
        st.markdown(
            f"**{v['patente']}** · {html.escape(v['tipo_vehiculo'])} · {html.escape(v['marca_modelo'])} "
            f"({v['anio']}) &nbsp; {ui.chip(estado, reglas.color_estado(estado))}",
            unsafe_allow_html=True,
        )
        st.caption(f"Kilometraje registrado: {ui.miles(v['kilometraje_actual'])} km")
        if ultimo:
            st.caption(f"Último reporte ({ui.fecha_corta(ultimo['fecha_reporte'])}): "
                       f"**{ultimo['resultado']}** — {reglas.resumen_hallazgos(ultimo)}")
        else:
            st.caption("Sin reportes de estado del conductor.")
        autorizados = [a["conductores"]["nombre_completo"] for a in v.get("autorizaciones") or []
                       if a.get("vigente") and a.get("conductores")]
        st.caption("Conductores autorizados: " + (", ".join(autorizados) if autorizados else "ninguno"))


def vista() -> None:
    st.title("🛂 Control de acceso · Garita")
    ronda = st.session_state.setdefault("garita_ronda", 0)

    if mensaje := st.session_state.pop("garita_mensaje", None):
        st.success(mensaje)

    # 1. Foto de la patente (evidencia) --------------------------------------
    foto = st.camera_input("1 · Foto de la patente", key=f"cam_{ronda}")
    if foto is None:
        with st.expander("¿Sin cámara? Subir una imagen"):
            foto = st.file_uploader("Imagen de la patente", type=["jpg", "jpeg", "png"], key=f"sub_{ronda}")
    datos_foto = foto.getvalue() if foto is not None else None

    # 2. Patente: OCR (una vez por foto) + corrección manual -----------------
    leida = None
    if datos_foto and ocr.ocr_disponible():
        try:
            leida = ocr.leer_patente(datos_foto)
        except Exception as e:
            st.warning(f"No se pudo leer la patente automáticamente ({e}). Ingrésela a mano.")
    huella = hashlib.md5(datos_foto).hexdigest()[:8] if datos_foto else "sinfoto"
    texto = st.text_input("2 · Patente", value=leida or "", placeholder="ABCD-12",
                          key=f"patente_{ronda}_{huella}")
    if leida:
        st.caption(f"Leída por OCR: **{leida}**. Corríjala si no coincide con la placa.")
    elif datos_foto and not ocr.ocr_disponible():
        st.caption("Lector OCR no instalado: ingrese la patente a mano.")
    patente = reglas.normalizar_patente(texto)

    # 3. Conductor ------------------------------------------------------------
    por_rut = {c["rut"]: c for c in db.conductores()}
    rut = st.selectbox(
        "3 · Conductor", options=list(por_rut), index=None,
        format_func=lambda r: f"{r} · {por_rut[r]['nombre_completo']}",
        placeholder="Escriba RUT o nombre…", key=f"conductor_{ronda}",
    )

    if not patente:
        st.info("Tome la foto o escriba la patente para consultar.")
        _ultimos_movimientos(por_rut)
        return
    if not reglas.formato_patente_valido(patente):
        st.warning(f"«{patente}» no tiene formato de patente (ABCD-12).")
        return

    # Consulta cruzada: vehículo + autorizaciones + conductores en una llamada
    vehiculo = db.vehiculo_con_autorizaciones(patente)
    if vehiculo:
        _ficha_vehiculo(vehiculo)

    if rut is None:
        if vehiculo is None:
            _banner("DENEGADO", f"La patente {patente} no está registrada en el catálogo.")
        st.info("Seleccione al conductor para validar el acceso.")
        return
    conductor = por_rut[rut]
    st.caption(f"{conductor['grado_o_cargo']} {conductor['nombre_completo']} · "
               f"{conductor['unidad_destino']} · {conductor.get('estado') or 'Activo'}")

    resultado, motivo = reglas.resolver_acceso(vehiculo, conductor)
    _banner(resultado, motivo)

    # 4. Registro en la bitácora (foto en el bucket) ---------------------------
    if resultado == "DENEGADO":
        movimiento, etiqueta = "ENTRADA", "Registrar intento denegado"
    else:
        sugerido = "SALIDA" if bitacora.ultimo_movimiento(patente) == "ENTRADA" else "ENTRADA"
        movimiento = st.radio("4 · Movimiento", ["ENTRADA", "SALIDA"], horizontal=True,
                              index=0 if sugerido == "ENTRADA" else 1,
                              key=f"movimiento_{ronda}_{patente}")
        etiqueta = f"Registrar {movimiento}"

    if datos_foto is None:
        st.caption("La foto de la patente es obligatoria como evidencia.")
    if st.button(etiqueta, type="primary", disabled=datos_foto is None, key=f"registrar_{ronda}"):
        with st.spinner("Guardando evidencia…"):
            try:
                bitacora.registrar_acceso(patente, rut, movimiento, resultado, datos_foto)
            except Exception as e:
                st.error(f"No se pudo guardar la evidencia en el bucket: {e}")
                return
        if resultado == "DENEGADO":
            st.session_state["garita_mensaje"] = f"Intento denegado de {patente} registrado con evidencia."
        else:
            st.session_state["garita_mensaje"] = f"{movimiento} de {patente} registrada ({resultado})."
        st.session_state["garita_ronda"] = ronda + 1     # limpia el formulario
        st.rerun()


def _ultimos_movimientos(por_rut: dict) -> None:
    filas = bitacora.accesos()[:5]
    if not filas:
        return
    st.subheader("Últimos movimientos")
    st.dataframe(pd.DataFrame([{
        "Hora": ui.fecha_corta(f["fecha_hora"]),
        "Patente": f["patente"],
        "Movimiento": f["movimiento"],
        "Resultado": f["resultado"],
        "Conductor": (por_rut.get(f["rut_conductor"]) or {}).get("nombre_completo", f["rut_conductor"]),
    } for f in filas]), hide_index=True)
