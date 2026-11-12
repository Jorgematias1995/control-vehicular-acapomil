"""
Perfil CONDUCTOR OPERATIVO (check-in / autogestión).

El conductor elige uno de sus vehículos autorizados, toma la foto del
odómetro y reporta kilometraje de salida, combustible, neumáticos, luces y
novedades. Además se piden los elementos de la Evaluación 02 (presión de
cada rueda, aceite, batería, frenos), que se resumen en 'observaciones'.

Lógica automática al enviar:
  1. reglas.evaluar_reporte() clasifica el reporte (OK / OBSERVACIONES / CRITICO).
  2. Se inserta en 'reportes_estado' (columnas del proyecto del curso).
  3. db.aplicar_reporte_a_vehiculo() actualiza la tabla maestra 'vehiculos':
     kilometraje_actual y, si el reporte es CRITICO, estado_operativo =
     'Requiere Mantención'.
"""

import pandas as pd
import streamlit as st

from modulos import auth, db, evidencias, reglas, ui

RUEDAS = ["Delantera izquierda", "Delantera derecha", "Trasera izquierda", "Trasera derecha"]


def vista() -> None:
    usuario = auth.usuario_actual() or {}
    rut = usuario.get("rut_conductor")
    st.title("📋 Reporte de estado del vehículo")

    conductor = next((c for c in db.conductores() if c["rut"] == rut), None)
    if conductor is None:
        st.error("Su usuario no está asociado a un conductor registrado.")
        return
    st.caption(f"{conductor['grado_o_cargo']} {conductor['nombre_completo']} · "
               f"{conductor['unidad_destino']} · RUT {rut}")

    if aviso := st.session_state.pop("conductor_mensaje", None):
        tipo, texto = aviso
        getattr(st, tipo)(texto)

    vehiculos = db.vehiculos_autorizados(rut)
    if not vehiculos:
        st.warning("No tiene vehículos con autorización vigente.")
        return
    por_patente = {v["patente"]: v for v in vehiculos}
    patente = st.selectbox(
        "Vehículo", list(por_patente),
        format_func=lambda p: f"{p} · {por_patente[p]['tipo_vehiculo']} · {por_patente[p]['marca_modelo']}",
    )
    v = por_patente[patente]
    ultimo = (db.reportes(patente=patente, limite=1) or [None])[0]

    c1, c2 = st.columns(2)
    c1.metric("Kilometraje registrado", f"{ui.miles(v['kilometraje_actual'])} km")
    c2.markdown("Estado actual<br>" + ui.chip(v["estado_operativo"], reglas.color_estado(v["estado_operativo"])),
                unsafe_allow_html=True)
    if not reglas.es_operativo(v["estado_operativo"]):
        st.warning(f"Este vehículo figura como «{v['estado_operativo']}». Igual puede reportar su condición.")

    ronda = st.session_state.setdefault("conductor_ronda", 0)

    # Evidencia ---------------------------------------------------------------
    foto = st.camera_input("Foto del odómetro (evidencia)", key=f"odometro_{ronda}")
    if foto is None:
        with st.expander("¿Sin cámara? Subir una imagen"):
            foto = st.file_uploader("Imagen del odómetro", type=["jpg", "jpeg", "png"], key=f"sub_odo_{ronda}")
    datos_foto = foto.getvalue() if foto is not None else None

    # Formulario (no recarga la página en cada cambio) ---------------------------
    with st.form(f"reporte_{ronda}_{patente}"):
        km = st.number_input("Kilometraje de salida (odómetro)", min_value=int(v["kilometraje_actual"]),
                             value=int(v["kilometraje_actual"]), step=1)
        c1, c2 = st.columns(2)
        combustible = c1.slider("Combustible (%)", 0, 100, int((ultimo or {}).get("nivel_combustible") or 75))
        aceite = c2.slider("Aceite (%)", 0, 100, 80)

        st.markdown("**Presión de neumáticos (PSI)**")
        columnas = [*st.columns(2), *st.columns(2)]
        presiones = {}
        for i, (col, nombre) in enumerate(zip(columnas, RUEDAS), start=1):
            presiones[i] = col.number_input(f"{i} · {nombre}", min_value=0.0, max_value=150.0,
                                            step=0.5, value=32.0)

        voltaje = st.number_input("Voltaje de batería (V)", min_value=0.0, max_value=32.0, step=0.1, value=12.6,
                                  help="12 V en vehículos livianos; 24 V en camiones y vehículos tácticos.")

        st.markdown("**Sistemas** (marcado = funciona correctamente)")
        c1, c2 = st.columns(2)
        luces_delanteras = c1.checkbox("Luces delanteras", value=True)
        luces_traseras = c2.checkbox("Luces traseras", value=True)
        balizas = c1.checkbox("Balizas", value=True)
        frenos = c2.checkbox("Frenos", value=True)
        novedades = st.text_area("Novedades mecánicas", placeholder="Ej.: ruido en la suspensión delantera")
        enviado = st.form_submit_button("Enviar reporte", type="primary")

    if enviado:
        _guardar_reporte(v, rut, datos_foto, {
            "kilometraje": int(km),
            "nivel_combustible": int(combustible),
            "nivel_aceite": aceite,
            **{f"presion_rueda_{i}": float(p) for i, p in presiones.items()},
            "voltaje_bateria": round(float(voltaje), 2),
            "luces_delanteras": luces_delanteras,
            "luces_traseras": luces_traseras,
            "balizas": balizas,
            "frenos": frenos,
        }, novedades.strip() or None)

    _mis_reportes(rut)


def _si_no(valor: bool) -> str:
    return "OK" if valor else "FALLA"


def _guardar_reporte(v: dict, rut: str, datos_foto: bytes | None, valores: dict, novedades: str | None) -> None:
    if datos_foto is None:
        st.error("Falta la foto del odómetro.")
        return
    error_km = reglas.validar_kilometraje(valores["kilometraje"], v["kilometraje_actual"])
    if error_km:
        st.error(error_km)
        return

    resultado, hallazgos = reglas.evaluar_reporte(valores)
    presiones = [valores[f"presion_rueda_{i}"] for i in range(1, 5)]
    detalle = (f"Neumáticos {'/'.join(f'{p:g}' for p in presiones)} PSI · "
               f"Aceite {valores['nivel_aceite']} % · Batería {valores['voltaje_bateria']:g} V · "
               f"Frenos {_si_no(valores['frenos'])} · Luces del./tras. "
               f"{_si_no(valores['luces_delanteras'])}/{_si_no(valores['luces_traseras'])} · "
               f"Balizas {_si_no(valores['balizas'])}")

    with st.spinner("Enviando reporte…"):
        try:
            url_foto = evidencias.subir_foto_reporte(v["patente"], datos_foto)
        except Exception as e:
            st.error(f"No se pudo subir la foto al bucket: {e}")
            return
        try:
            db.registrar_reporte({
                "patente": v["patente"],
                "rut_conductor": rut,
                "kilometraje_salida": valores["kilometraje"],
                "nivel_combustible": valores["nivel_combustible"],
                # true = las 4 ruedas sobre el mínimo; true = luces y balizas funcionando
                "presion_neumaticos": min(presiones) >= reglas.PRESION_MINIMA,
                "luces_operativas": valores["luces_delanteras"] and valores["luces_traseras"] and valores["balizas"],
                "observaciones": reglas.componer_observaciones(resultado, hallazgos, detalle, novedades),
                "foto_evidencia_url": url_foto,
            })
        except Exception as e:
            st.error(f"La foto se subió, pero no se pudo guardar el reporte: {e}")
            return
        try:
            estado = db.aplicar_reporte_a_vehiculo(v, valores["kilometraje"], resultado)
        except Exception as e:
            st.warning(f"Reporte guardado, pero no se pudo actualizar el vehículo: {e}")
            estado = v["estado_operativo"]

    lista = "".join(f"\n- {h}" for h in hallazgos)
    if resultado == "CRITICO":
        aviso = ("error", f"Reporte CRÍTICO registrado. {v['patente']} quedó en estado «{estado}» "
                          f"y fue informado al Puesto de Mando.{lista}")
    elif resultado == "OBSERVACIONES":
        aviso = ("warning", f"Reporte registrado con observaciones:{lista}")
    else:
        aviso = ("success", f"Reporte registrado. {v['patente']} sin novedades.")
    st.session_state["conductor_mensaje"] = aviso
    st.session_state["conductor_ronda"] = st.session_state.get("conductor_ronda", 0) + 1
    st.rerun()


def _mis_reportes(rut: str) -> None:
    filas = db.reportes(rut=rut, limite=10)
    if not filas:
        return
    st.subheader("Mis últimos reportes")
    st.dataframe(pd.DataFrame([{
        "Fecha": ui.fecha_corta(r["fecha_reporte"]),
        "Patente": r["patente"],
        "Km salida": r["kilometraje_salida"],
        "Resultado": r["resultado"],
        "Observaciones": reglas.resumen_hallazgos(r),
    } for r in filas]), hide_index=True)
