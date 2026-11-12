"""
Perfil ADMINISTRADOR · Panel BI del Puesto de Mando.

- KPIs: % de disponibilidad, unidades inmovilizadas o en mantención,
  accesos de hoy, denegados/alertas de hoy.
- Alertas por fallas mecánicas (último reporte de cada vehículo).
- Matriz de estado por vehículo (verde / amarillo / rojo).
- Analítica: kilometraje acumulado y frecuencia de accesos por unidad.
- Feed cronológico de accesos con la foto guardada en Supabase Storage
  (la bitácora de garita vive en el bucket: ver bitacora.py).
Se actualiza solo cada 30 s (st.fragment) para mostrar datos en tiempo real.
"""

import html

import altair as alt
import pandas as pd
import streamlit as st

from modulos import bitacora, db, evidencias, reglas, ui

ICONO_RESULTADO = {"OK": "🟢", "OBSERVACIONES": "🟡", "CRITICO": "🔴"}


def vista() -> None:
    st.title("📊 Puesto de Mando · Estado de apresto")
    c1, c2 = st.columns([3, 1])
    automatico = c1.toggle("Actualización automática (cada 30 s)", value=True)
    if c2.button("🔄 Actualizar ahora"):
        db.limpiar_cache()
    if automatico:
        _panel_en_vivo()
    else:
        _panel()


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
def _tablas():
    vehiculos = pd.DataFrame(db.vehiculos())
    if not vehiculos.empty:
        vehiculos["grupo"] = vehiculos["estado_operativo"].map(reglas.grupo_estado)
    accesos = pd.DataFrame(bitacora.accesos())
    if not accesos.empty:
        por_rut = {c["rut"]: c for c in db.conductores()}
        accesos["fecha"] = ui.a_hora_chile(accesos["fecha_hora"])
        accesos["unidad"] = accesos["rut_conductor"].map(
            lambda r: (por_rut.get(r) or {}).get("unidad_destino", "Sin unidad"))
        accesos["conductor"] = accesos["rut_conductor"].map(
            lambda r: (por_rut.get(r) or {}).get("nombre_completo", r))
    reportes = pd.DataFrame(db.reportes())
    ultimos = pd.DataFrame()
    if not reportes.empty:
        reportes["fecha"] = ui.a_hora_chile(reportes["fecha_reporte"])
        reportes["hallazgos"] = [reglas.resumen_hallazgos(r) for r in reportes.to_dict("records")]
        ultimos = reportes.sort_values("fecha").groupby("patente").tail(1).set_index("patente")
    return vehiculos, accesos, ultimos


def _panel() -> None:
    vehiculos, accesos, ultimos = _tablas()
    if vehiculos.empty:
        st.warning("No hay vehículos registrados.")
        return
    _kpis(vehiculos, accesos)
    _alertas(vehiculos, ultimos)
    _matriz(vehiculos, ultimos)
    _analitica(vehiculos, accesos)
    _feed(accesos)


_panel_en_vivo = st.fragment(run_every=30)(_panel)


# ---------------------------------------------------------------------------
# Secciones
# ---------------------------------------------------------------------------
def _kpis(vehiculos: pd.DataFrame, accesos: pd.DataFrame) -> None:
    total = len(vehiculos)
    operativos = int((vehiculos["grupo"] == "Operativo").sum())
    inmovilizados = total - operativos
    criticos = int((vehiculos["grupo"] == "Crítico").sum())
    hoy = accesos[accesos["fecha"].dt.date == ui.hoy_chile()] if not accesos.empty else accesos
    incidencias = int(hoy["resultado"].isin(["DENEGADO", "ALERTA"]).sum()) if not hoy.empty else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Disponibilidad de la flota", f"{operativos / total * 100:.0f} %",
              help=f"{operativos} de {total} vehículos en estado Operativo")
    k2.metric("Inmovilizados o en mantención", inmovilizados,
              help=f"{criticos} en estado Crítico · {inmovilizados - criticos} requieren mantención")
    k3.metric("Accesos hoy", len(hoy))
    k4.metric("Denegados / alertas hoy", incidencias)


def _alertas(vehiculos: pd.DataFrame, ultimos: pd.DataFrame) -> None:
    st.subheader("Alertas por fallas mecánicas")
    orden = {"Crítico": 0, "Requiere Mantención": 1, "Operativo": 2}
    hubo = False
    for v in sorted(vehiculos.to_dict("records"), key=lambda x: orden[x["grupo"]]):
        rep = ultimos.loc[v["patente"]] if v["patente"] in ultimos.index else None
        detalle = (f"Último reporte {rep['fecha'].strftime('%d-%m %H:%M')} ({rep['resultado']}): "
                   f"{ui.texto(rep['hallazgos'])}" if rep is not None else "Sin reportes del conductor.")
        texto = f"**{v['patente']}** · {v['tipo_vehiculo']} {v['marca_modelo']} — {v['estado_operativo']}. {detalle}"
        if v["grupo"] == "Crítico":
            st.error(texto, icon="🔴")
        elif v["grupo"] == "Requiere Mantención":
            st.warning(texto, icon="🟡")
        elif rep is not None and rep["resultado"] == "OBSERVACIONES":
            st.info(f"**{v['patente']}** operativo con observaciones. {detalle}", icon="ℹ️")
        elif rep is not None and rep["resultado"] == "CRITICO":
            st.info(f"**{v['patente']}** liberado como Operativo por el Puesto de Mando. {detalle}", icon="ℹ️")
        else:
            continue
        hubo = True
    if not hubo:
        st.success("Sin alertas: toda la flota está operativa.")


def _matriz(vehiculos: pd.DataFrame, ultimos: pd.DataFrame) -> None:
    st.subheader("Matriz de estado por vehículo")
    conteo = vehiculos["grupo"].value_counts()
    st.markdown(" &nbsp; ".join(ui.chip(f"{e}: {int(conteo.get(e, 0))}", c)
                                for e, c in reglas.COLOR_ESTADO.items()), unsafe_allow_html=True)
    tarjetas = []
    for v in vehiculos.to_dict("records"):
        color = reglas.color_estado(v["estado_operativo"])
        rep = ultimos.loc[v["patente"]] if v["patente"] in ultimos.index else None
        ultimo = f"{ICONO_RESULTADO[rep['resultado']]} {rep['fecha'].strftime('%d-%m')}" if rep is not None else "sin reporte"
        tarjetas.append(
            f"<div style='background:{color}22;border:2px solid {color};border-radius:10px;padding:8px 10px'>"
            f"<div style='font-weight:800;font-size:1.1em'>{v['patente']}</div>"
            f"<div style='font-size:.8em;opacity:.85'>{html.escape(v['tipo_vehiculo'])}</div>"
            f"<div style='font-size:.8em'>{ui.miles(v['kilometraje_actual'])} km · {ultimo}</div>"
            f"<div style='font-size:.8em;font-weight:700;color:{color}'>● {v['estado_operativo']}</div></div>"
        )
    st.markdown("<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));"
                "gap:10px;margin:8px 0 16px'>" + "".join(tarjetas) + "</div>", unsafe_allow_html=True)


def _analitica(vehiculos: pd.DataFrame, accesos: pd.DataFrame) -> None:
    st.subheader("Analítica de uso")
    escala_estado = alt.Scale(domain=list(reglas.COLOR_ESTADO), range=list(reglas.COLOR_ESTADO.values()))
    izquierda, derecha = st.columns(2)

    with izquierda:
        agrupar = st.radio("Kilometraje acumulado por", ["Vehículo", "Tipo de vehículo"],
                           horizontal=True, key="km_agrupar")
        if agrupar == "Vehículo":
            seleccion = alt.selection_point(fields=["grupo"], bind="legend")
            grafico = alt.Chart(vehiculos).mark_bar().encode(
                x=alt.X("kilometraje_actual:Q", title="Kilómetros"),
                y=alt.Y("patente:N", sort="-x", title=None),
                color=alt.Color("grupo:N", scale=escala_estado, title="Estado"),
                opacity=alt.condition(seleccion, alt.value(1), alt.value(0.25)),
                tooltip=["patente", "tipo_vehiculo", "marca_modelo", "anio", "estado_operativo",
                         alt.Tooltip("kilometraje_actual:Q", title="km", format=",")],
            ).add_params(seleccion)
        else:
            por_tipo = (vehiculos.groupby("tipo_vehiculo", as_index=False)
                        .agg(km=("kilometraje_actual", "sum"), unidades=("patente", "count")))
            grafico = alt.Chart(por_tipo).mark_bar(color="#4b5d23").encode(
                x=alt.X("km:Q", title="Kilómetros acumulados"),
                y=alt.Y("tipo_vehiculo:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240)),
                tooltip=["tipo_vehiculo", "unidades", alt.Tooltip("km:Q", format=",")],
            )
        st.altair_chart(grafico)

    with derecha:
        periodo = st.radio("Accesos por unidad", ["7 días", "30 días", "Todo"], horizontal=True, key="acc_periodo")
        if accesos.empty:
            st.info("Aún no hay accesos registrados.")
            return
        datos = accesos
        if periodo != "Todo":
            desde = pd.Timestamp.now(tz=ui.ZONA_CHILE) - pd.Timedelta(days=int(periodo.split()[0]))
            datos = accesos[accesos["fecha"] >= desde]
        if datos.empty:
            st.info("Sin accesos en el período.")
            return
        conteo = datos.groupby(["unidad", "movimiento"], as_index=False).size()
        seleccion = alt.selection_point(fields=["movimiento"], bind="legend")
        grafico = alt.Chart(conteo).mark_bar().encode(
            x=alt.X("size:Q", title="Registros", axis=alt.Axis(tickMinStep=1, format="d")),
            y=alt.Y("unidad:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240)),
            color=alt.Color("movimiento:N", title="Movimiento",
                            scale=alt.Scale(domain=["ENTRADA", "SALIDA"], range=["#1a73e8", "#9334e6"])),
            opacity=alt.condition(seleccion, alt.value(1), alt.value(0.25)),
            tooltip=["unidad", "movimiento", alt.Tooltip("size:Q", title="registros")],
        ).add_params(seleccion)
        st.altair_chart(grafico)


def _feed(accesos: pd.DataFrame, cantidad: int = 10) -> None:
    st.subheader("Feed de accesos (más recientes)")
    if accesos.empty:
        st.info("Aún no hay accesos registrados.")
        return
    for a in accesos.sort_values("fecha", ascending=False).head(cantidad).to_dict("records"):
        with st.container(border=True):
            foto, texto = st.columns([1, 3])
            url = evidencias.url_publica(a.get("foto"))
            if url:
                foto.image(url, width=160)
            else:
                foto.caption("Sin foto")
            color = reglas.COLOR_RESULTADO_ACCESO[a["resultado"]]
            texto.markdown(
                f"**{a['patente']}** · {a['movimiento']} &nbsp; {ui.chip(a['resultado'], color)}<br>"
                f"{html.escape(a['conductor'])} · {html.escape(a['unidad'])}<br>"
                f"<span style='opacity:.75'>{a['fecha'].strftime('%d-%m-%Y %H:%M')}</span>",
                unsafe_allow_html=True,
            )
