"""
Control Vehicular ACAPOMIL · punto de entrada.

    streamlit run app.py

Gestión de sesión y navegación condicional:
- Sin sesión: solo existe la página de ingreso.
- Con sesión: st.navigation() registra SOLO las páginas del rol guardado en
  st.session_state["usuario"]. Una página que no está registrada no se
  puede abrir ni escribiendo su URL.
"""

import streamlit as st

st.set_page_config(page_title="Control Vehicular ACAPOMIL", page_icon="🚙", layout="wide")

from modulos import auth, db  # noqa: E402
from modulos import modulo_bi, modulo_conductor, modulo_guardia, modulo_jem  # noqa: E402


def _hay_secretos() -> bool:
    try:
        return "supabase" in st.secrets
    except Exception:
        return False


def pantalla_ingreso() -> None:
    st.title("🚙 Control Vehicular ACAPOMIL")
    st.caption("Gestión de acceso y estado operativo del material rodante")
    if not _hay_secretos():
        st.error("Falta el archivo .streamlit/secrets.toml con la sección [supabase] (url y key). "
                 "Vea el README.")
        st.stop()

    with st.form("ingreso"):
        nombre_usuario = st.text_input("Usuario", placeholder="admin, guardia o conductor")
        clave = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar", type="primary"):
            error = auth.iniciar_sesion(nombre_usuario, clave)
            if error:
                st.error(error)
            else:
                st.rerun()

    if auth.modo_demo():
        st.divider()
        st.caption("Modo demo (solo pruebas locales): entrar sin contraseña")
        rol = st.selectbox("Rol", list(auth.ROLES), format_func=auth.ROLES.get)
        rut, nombre = None, None
        if rol == "CONDUCTOR":
            conductores = {c["rut"]: c for c in db.conductores()}
            rut = st.selectbox("Conductor", list(conductores),
                               format_func=lambda r: f"{r} · {conductores[r]['nombre_completo']}")
            nombre = conductores[rut]["nombre_completo"] if rut else None
        if st.button("Entrar en modo demo"):
            auth.entrar_modo_demo(rol, rut, nombre)
            st.rerun()


PAGINAS_POR_ROL = {
    "GUARDIA": [
        st.Page(modulo_guardia.vista, title="Control de acceso", icon=":material/badge:", url_path="garita"),
    ],
    "CONDUCTOR": [
        st.Page(modulo_conductor.vista, title="Reporte de estado", icon=":material/assignment:", url_path="reporte"),
    ],
    "ADMIN": [
        st.Page(modulo_bi.vista, title="Panel de mando", icon=":material/monitoring:", url_path="panel"),
        st.Page(modulo_jem.vista, title="Auditoría por patente", icon=":material/manage_search:",
                url_path="auditoria"),
    ],
}

usuario = auth.usuario_actual()
if usuario is None:
    paginas = [st.Page(pantalla_ingreso, title="Ingreso", icon=":material/login:")]
else:
    paginas = PAGINAS_POR_ROL[usuario["rol"]]
    with st.sidebar:
        st.markdown(f"**{usuario['nombre']}**  \n{auth.ROLES[usuario['rol']]}")
        if st.button("Cerrar sesión", icon=":material/logout:"):
            auth.cerrar_sesion()
            st.rerun()

st.navigation(paginas).run()
