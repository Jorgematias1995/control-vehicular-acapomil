"""
Crea los perfiles de prueba (Administrador, Guardia y Conductor) y los
guarda en .streamlit/secrets.toml, sección [usuarios] (archivo fuera del
repositorio).

La contraseña NO queda escrita: se guarda su hash PBKDF2-SHA256 con una
sal aleatoria. Al ingresar, la app recalcula el hash y lo compara.

(¿Por qué no Supabase Auth? En el proyecto compartido del curso, crear
usuarios responde "Database error creating new user".)

Uso, desde la carpeta del proyecto y con el entorno virtual activado:
    python scripts/crear_usuarios_prueba.py
Se puede ejecutar de nuevo para cambiar la contraseña.
En Streamlit Cloud, copie también la sección [usuarios] en Settings > Secrets.
"""

import getpass
import hashlib
import os
from pathlib import Path

ITERACIONES = 200_000
USUARIOS = [
    # usuario,    nombre,                   rol,         RUT de conductor
    ("admin",     "Jefe Puesto de Mando",   "ADMIN",     None),
    ("guardia",   "Guardia de Garita",      "GUARDIA",   None),
    ("conductor", "Carlos Soto Ramírez",    "CONDUCTOR", "18.234.567-K"),   # autorizado: ABCD-12 y NPQR-78
]


def hash_clave(clave: str) -> str:
    sal = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, ITERACIONES).hex()
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${digest}"


archivo = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
if not archivo.exists():
    raise SystemExit(f"No existe {archivo}. Créelo primero con la sección [supabase].")

clave = getpass.getpass("Contraseña para los 3 usuarios (mínimo 6 caracteres; no se verá al escribir): ")
if len(clave) < 6:
    raise SystemExit("La contraseña debe tener al menos 6 caracteres.")
if getpass.getpass("Repita la contraseña: ") != clave:
    raise SystemExit("Las contraseñas no coinciden.")

# Conserva todo lo que no sea [usuarios...] y agrega la sección nueva al final
conservadas, dentro = [], False
for linea in archivo.read_text(encoding="utf-8").splitlines():
    if linea.strip().startswith("["):
        dentro = linea.strip().startswith("[usuarios")
    if not dentro:
        conservadas.append(linea)
while conservadas and not conservadas[-1].strip():
    conservadas.pop()

bloque = ["", "# Usuarios de prueba (generado por scripts/crear_usuarios_prueba.py)"]
for usuario, nombre, rol, rut in USUARIOS:
    bloque += ["", f"[usuarios.{usuario}]", f'nombre = "{nombre}"', f'rol = "{rol}"']
    if rut:
        bloque.append(f'rut_conductor = "{rut}"')
    bloque.append(f'clave = "{hash_clave(clave)}"')

archivo.write_text("\n".join(conservadas + bloque) + "\n", encoding="utf-8")
for usuario, _, rol, _ in USUARIOS:
    print(f"{rol:<10} usuario: {usuario}")
print("\nListo. Reinicie la app (Ctrl+C y streamlit run app.py) e ingrese con esos usuarios.")
