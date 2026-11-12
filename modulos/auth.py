"""
Autenticación y sesión.

1. El usuario ingresa usuario (o correo) y contraseña.
2. Se verifica contra los usuarios de prueba definidos en .streamlit/secrets.toml,
   sección [usuarios]. La contraseña NO se guarda: se guarda su hash
   PBKDF2-SHA256 con sal (lo genera scripts/crear_usuarios_prueba.py), y al
   ingresar se recalcula el hash y se compara.
   (Si el nombre no está ahí, se intenta con Supabase Auth, leyendo el rol de
   app_metadata. En el proyecto del curso no se pueden crear usuarios de Auth:
   responde "Database error creating new user".)
3. El perfil (nombre, rol, RUT si es conductor) se guarda en
   st.session_state["usuario"]: cada pestaña del navegador tiene su propio
   session_state, por eso cada persona ve solo su rol.
4. app.py arma la navegación (st.navigation) según ese rol.

modo_demo (secrets.toml -> [app] modo_demo = true) permite elegir el rol sin
contraseña, solo para pruebas locales.
"""

import hashlib
import hmac

import streamlit as st
from supabase import create_client

ROLES = {
    "GUARDIA": "Guardia de Garita",
    "CONDUCTOR": "Conductor Operativo",
    "ADMIN": "Administrador de Puesto de Mando",
}


def usuario_actual() -> dict | None:
    return st.session_state.get("usuario")


def modo_demo() -> bool:
    try:
        return bool(st.secrets.get("app", {}).get("modo_demo", False))
    except Exception:
        return False


def verificar_clave(clave: str, guardado: str) -> bool:
    """guardado = 'pbkdf2_sha256$<iteraciones>$<sal hex>$<hash hex>'."""
    try:
        algoritmo, iteraciones, sal, esperado = guardado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        calculado = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), int(iteraciones)).hex()
        return hmac.compare_digest(calculado, esperado)
    except (ValueError, AttributeError):
        return False


def iniciar_sesion(nombre_usuario: str, clave: str) -> str | None:
    """Devuelve None si el ingreso fue correcto, o un mensaje de error."""
    nombre_usuario = nombre_usuario.strip().lower()
    try:
        locales = st.secrets.get("usuarios", {})
    except Exception:
        locales = {}
    if nombre_usuario in locales:
        u = locales[nombre_usuario]
        if not verificar_clave(clave, u.get("clave", "")):
            return "Usuario o contraseña incorrectos."
        if u.get("rol") not in ROLES:
            return "El usuario no tiene un rol válido en secrets.toml."
        _guardar(None, u.get("nombre", nombre_usuario), u["rol"], u.get("rut_conductor"), nombre_usuario)
        return None
    if "@" not in nombre_usuario:
        return "Usuario o contraseña incorrectos."
    return _iniciar_con_supabase_auth(nombre_usuario, clave)


def _iniciar_con_supabase_auth(email: str, clave: str) -> str | None:
    cfg = st.secrets["supabase"]
    temporal = create_client(cfg["url"], cfg["key"])
    try:
        respuesta = temporal.auth.sign_in_with_password(
            {"email": email.strip().lower(), "password": clave})
    except Exception as e:
        if "invalid" in str(e).lower():
            return "Usuario o contraseña incorrectos."
        return f"No se pudo iniciar sesión: {e}"

    usuario = respuesta.user
    datos = getattr(usuario, "app_metadata", None) or {}
    rol = datos.get("rol")
    if rol not in ROLES:
        return "El usuario existe, pero no tiene un rol asignado."
    if rol == "CONDUCTOR" and not datos.get("rut_conductor"):
        return "El usuario conductor no tiene RUT asociado."
    _guardar(usuario.id, datos.get("nombre") or usuario.email, rol, datos.get("rut_conductor"), usuario.email)
    return None


def entrar_modo_demo(rol: str, rut_conductor: str | None = None, nombre: str | None = None) -> None:
    _guardar(None, nombre or f"{ROLES[rol]} (demo)", rol, rut_conductor, None)


def _guardar(uid, nombre, rol, rut_conductor, email) -> None:
    st.session_state["usuario"] = {
        "id": uid, "nombre": nombre, "rol": rol,
        "rut_conductor": rut_conductor, "email": email,
    }


def cerrar_sesion() -> None:
    for clave in list(st.session_state.keys()):
        del st.session_state[clave]
