"""
Perfil ADMINISTRADOR · Jefe del Puesto de Mando (JEM): auditoría por patente.

- Selecciona una patente y revisa la ficha, los conductores autorizados,
  los reportes de estado (con la foto del odómetro) y los accesos en
  garita (con la foto de la patente) guardados en Supabase Storage.
- Cambia el estado operativo del vehículo (p. ej., vuelve a 'Operativo'
  después de la reparación, o lo inmoviliza como 'Crítico').
"""

import pandas as pd
import streamlit as st

from modulos import bitacora, db, evidencias, reglas, ui

ICONO_RESULTADO = {"OK": "🟢", "OBSERVACIONES": "🟡", "CRITICO": "🔴"}


def vista() -> None:
    st.title("🔎 Auditoría por patente")
    if aviso := st.session_state.pop("jem_mensaje", None):
        st.success(aviso)

    por_patente = {v["patente"]: v for v in db.vehiculos()}
    patente = st.selectbox(
        "Patente", list(por_patente), index=None, placeholder="Seleccione o escriba una patente…",
        format_func=lambda p: f"{p} · {por_patente[p]['marca_modelo']} ({por_patente[p]['estado_operativo']})",
    )
    if not patente:
        st.info("Seleccione un vehículo para ver su bitácora.")
        return

    v = db.vehiculo_con_autorizaciones(patente) or por_patente[patente]
    _ficha(v)
    _cambiar_estado(v)

    reportes = db.reportes(patente=patente)
    accesos = bitacora.accesos_de(patente)
    tab_reportes, tab_accesos = st.tabs([f"Reportes de conductores ({len(reportes)})",
                                         f"Accesos en garita ({len(accesos)})"])
    with tab_reportes:
        _reportes(reportes)
    with tab_accesos:
        _accesos(accesos)


def _ficha(v: dict) -> None:
    estado = v["estado_operativo"]
    with st.container(border=True):
        st.markdown(f"### {v['patente']} &nbsp; {ui.chip(estado, reglas.color_estado(estado))}",
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Tipo", v["tipo_vehiculo"])
        c2.metric("Marca / modelo", v["marca_modelo"])
        c3.metric("Kilometraje", f"{ui.miles(v['kilometraje_actual'])} km")
        autorizados = [f"{a['conductores']['grado_o_cargo']} {a['conductores']['nombre_completo']}"
                       + ("" if a.get("vigente") else " (no vigente)")
                       for a in v.get("autorizaciones") or [] if a.get("conductores")]
        st.caption("Conductores autorizados: " + (", ".join(autorizados) if autorizados else "ninguno"))


def _cambiar_estado(v: dict) -> None:
    with st.expander("Cambiar estado operativo"):
        actual = v["estado_operativo"]
        opciones = reglas.ESTADOS_VEHICULO + ([actual] if actual not in reglas.ESTADOS_VEHICULO else [])
        nuevo = st.selectbox("Nuevo estado", opciones, index=opciones.index(actual), key=f"estado_{v['patente']}")
        st.caption("Use «Operativo» cuando el vehículo vuelva de mantención; «Crítico» lo inmoviliza.")
        if st.button("Guardar estado", disabled=nuevo == actual, key=f"guardar_estado_{v['patente']}"):
            try:
                filas = db.cambiar_estado_vehiculo(v["patente"], nuevo)
            except Exception as e:
                st.error(f"No se pudo actualizar: {e}")
                return
            if filas == 0:
                st.error("La base no actualizó ninguna fila (revise la key o las políticas RLS).")
                return
            st.session_state["jem_mensaje"] = f"{v['patente']}: «{actual}» → «{nuevo}»."
            st.rerun()


def _ok(valor) -> str:
    if valor is None:
        return "—"
    return "✅ Correcta" if valor else "❌ Con falla"


def _reportes(reportes: list[dict]) -> None:
    if not reportes:
        st.info("Este vehículo no tiene reportes de estado.")
        return
    for i, r in enumerate(reportes):
        conductor = (r.get("conductores") or {}).get("nombre_completo", r.get("rut_conductor"))
        titulo = (f"{ICONO_RESULTADO[r['resultado']]} {ui.fecha_corta(r['fecha_reporte'])} · "
                  f"{r['resultado']} · {conductor} · {ui.miles(r['kilometraje_salida'] or 0)} km")
        with st.expander(titulo, expanded=(i == 0)):
            foto, datos = st.columns([1, 2])
            url = evidencias.url_publica(r.get("foto_evidencia_url"))
            if url:
                foto.image(url, caption="Odómetro")
            else:
                foto.caption("Sin foto")
            combustible = r.get("nivel_combustible")
            datos.dataframe(pd.DataFrame([
                ("Kilometraje de salida", f"{ui.miles(r['kilometraje_salida'] or 0)} km"),
                ("Combustible", f"{combustible} %" if combustible is not None else "—"),
                ("Presión de neumáticos", _ok(r.get("presion_neumaticos"))),
                ("Luces", _ok(r.get("luces_operativas"))),
            ], columns=["Elemento", "Valor"]), hide_index=True)
            if r.get("observaciones"):
                datos.markdown("**Observaciones:** " + r["observaciones"].replace(" | ", "  \n"))


def _accesos(accesos: list[dict]) -> None:
    if not accesos:
        st.info("Este vehículo no tiene accesos registrados.")
        return
    por_rut = {c["rut"]: c for c in db.conductores()}
    st.dataframe(pd.DataFrame([{
        "Fecha": ui.fecha_corta(a["fecha_hora"]),
        "Movimiento": a["movimiento"],
        "Resultado": a["resultado"],
        "Conductor": (por_rut.get(a["rut_conductor"]) or {}).get("nombre_completo", a["rut_conductor"]),
    } for a in accesos]), hide_index=True)

    st.markdown("**Evidencias fotográficas (últimas 12)**")
    columnas = st.columns(3)
    for i, a in enumerate(accesos[:12]):
        url = evidencias.url_publica(a["foto"])
        if url:
            columnas[i % 3].image(url, caption=f"{ui.fecha_corta(a['fecha_hora'])} · {a['movimiento']}")
