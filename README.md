# Control Vehicular ACAPOMIL

Aplicación web y móvil para el control de acceso vehicular en garita y el estado operativo
de la flota. Programación Avanzada · Sesión 12. Python + Streamlit + Supabase (PostgreSQL y Storage).

| Perfil | Página | Qué hace |
|---|---|---|
| Guardia de Garita | Control de acceso | Foto de la patente (OCR), consulta cruzada vehículo + conductor, resolución **Autorizado / Alerta de Estado / Denegado**, registro con evidencia |
| Conductor Operativo | Reporte de estado | Kilometraje, combustible, aceite, neumáticos, batería, luces, frenos, novedades y foto del odómetro |
| Administrador (Puesto de Mando) | Panel de mando | % de disponibilidad, inmovilizados, matriz verde/amarillo/rojo, kilometraje, accesos por unidad, feed con fotos |
| Administrador (JEM) | Auditoría por patente | Reportes y accesos de un vehículo con sus fotos; cambio de estado operativo |

## Estructura

```
app.py                        Entrada: ingreso, sesión y navegación según el rol
modulos/
  modulo_guardia.py           Perfil Guardia
  modulo_conductor.py         Perfil Conductor
  modulo_bi.py                Perfil Administrador: panel BI
  modulo_jem.py               Perfil Administrador: auditoría y gestión de estado
  auth.py                     Inicio de sesión (Supabase Auth) y rol del usuario
  db.py                       Todas las consultas a las tablas
  bitacora.py                 Bitácora de accesos de la garita (en el bucket)
  reglas.py                   Lógica de negocio pura (umbrales, resolución de acceso)
  evidencias.py               Compresión (< 800 KB), carga al bucket y URL pública
  ocr.py                      Lectura de patentes con EasyOCR (opcional)
  ui.py                       Hora de Chile, etiquetas de color
sql/
  01_esquema.sql              Modelo de las 4 tablas del proyecto del curso (DER) y bucket
  02_datos.sql                30 conductores, 15 vehículos y 18 autorizaciones
scripts/
  crear_usuarios_prueba.py    Crea los perfiles de prueba (admin, guardia, conductor)
  explorar_bd.py              Muestra columnas, llaves y filas de cada tabla (solo lectura)
  crear_bucket.py             Crea el bucket de evidencias si no existe
tests/
  test_reglas.py              Pruebas unitarias de la lógica (python tests/test_reglas.py)
.streamlit/
  secrets.toml.example        Plantilla; el secrets.toml real NO se sube (.gitignore)
requirements.txt
```

## Puesta en marcha (local, VS Code)

1. **Base de datos.** La app usa el proyecto Supabase del curso, que ya tiene las tablas
   `conductores`, `vehiculos`, `autorizaciones` y `reportes_estado`, y el bucket
   `evidencias-vehiculares`. (`sql/` sirve para recrear el modelo en otro proyecto.)
2. **Credenciales.** Copie `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y pegue
   la URL y la secret key del proyecto del curso.
3. **Dependencias** (con el entorno virtual activado):
   ```
   pip install -r requirements.txt
   ```
   `easyocr` instala PyTorch y tarda varios minutos. Si se omite, la patente se escribe a mano.
4. **Usuarios de prueba:**
   ```
   python scripts/crear_usuarios_prueba.py
   ```
   Pide una contraseña y agrega a `secrets.toml` los usuarios `admin`, `guardia` y `conductor`
   (Carlos Soto Ramírez, autorizado para ABCD-12 y NPQR-78), con la contraseña guardada como hash.
5. **Pruebas (opcional):** `python tests/test_reglas.py` (7 grupos, 42 verificaciones, sin conexión).
6. **Ejecutar:**
   ```
   streamlit run app.py
   ```

## Despliegue en Streamlit Community Cloud

*Create app* → este repositorio → *Main file path*: `app.py` → *Advanced settings → Secrets*: pegue
el contenido completo de su `secrets.toml` (incluida la sección `[usuarios]`). La cámara del celular necesita HTTPS, que Streamlit Cloud entrega.

## Decisiones clave

- **Consulta cruzada (garita).** `db.vehiculo_con_autorizaciones()` hace una sola llamada:
  `vehiculos.select("*, autorizaciones(vigente, rut_conductor, conductores(*))")`. PostgREST
  resuelve los JOIN por las llaves foráneas, y `reglas.resolver_acceso()` decide con ese resultado:
  patente inexistente, conductor no Activo o sin autorización vigente → **Denegado**;
  autorizado pero vehículo no Operativo → **Alerta de Estado**; si no → **Autorizado**.
- **Reporte crítico → "Requiere Mantención".** `reglas.evaluar_reporte()` clasifica el reporte
  (OK / OBSERVACIONES / CRITICO) con los umbrales de la Eval 02. Se inserta en `reportes_estado` y
  luego `db.aplicar_reporte_a_vehiculo()` actualiza la tabla maestra: kilometraje y, si es CRITICO y
  el vehículo estaba operativo, `estado_operativo = 'Requiere Mantención'`. El kilometraje no puede
  ser menor al registrado. Volver a "Operativo" lo decide el Puesto de Mando (módulo JEM).
  (En el proyecto del curso no se pueden crear triggers; con acceso a SQL, esta regla iría en un
  trigger para que ocurra en la misma transacción.)
- **Reporte del conductor en las columnas del curso.** `presion_neumaticos` = las 4 ruedas sobre
  25 PSI; `luces_operativas` = luces delanteras, traseras y balizas OK; `observaciones` guarda
  `[RESULTADO] hallazgos | Detalle: presiones, aceite, batería, frenos… | Novedades: …`.
- **Bitácora de garita en el bucket.** No hay tabla de accesos y no se pueden crear tablas, así que
  cada registro es su foto: `garita/<fecha>__<PATENTE>__<MOVIMIENTO>__<RESULTADO>__<RUT>__<código>.jpg`.
  No existe registro sin evidencia y el panel lee la bitácora listando esa carpeta (`bitacora.py`).
- **Sesión y perfiles.** Los usuarios de prueba están en `secrets.toml` (fuera del repo) con la
  contraseña como hash PBKDF2-SHA256 con sal; al ingresar se recalcula y compara. El perfil se guarda
  en `st.session_state` y `st.navigation()` registra solo las páginas de ese rol. (Supabase Auth del
  proyecto compartido no permite crear usuarios: "Database error creating new user"; la app igual
  acepta usuarios de Auth con el rol en `app_metadata`, si existieran.)
- **Evidencias.** Bucket público `evidencias-vehiculares` (máx. 800 KB). La app comprime cada foto
  a JPEG ≤ 800 KB antes de subirla.
- **Base compartida.** `estado_operativo` es texto libre y lo editan todos los alumnos, así que
  `reglas.grupo_estado()` lleva cualquier valor a verde / amarillo / rojo.
- **Secretos.** La secret key vive solo en `.streamlit/secrets.toml` (local) o en los Secrets de
  Streamlit Cloud; nunca en el código.

### Umbrales (`modulos/reglas.py`)

| Elemento | Crítico (inmoviliza) | Observación |
|---|---|---|
| Presión de neumático | < 20 PSI | < 25 PSI |
| Aceite | < 25 % | < 50 % |
| Batería | < 11,8 V (12 V) / < 23,6 V (24 V) | — |
| Frenos | Falla | — |
| Combustible | — | < 25 % |
| Luces / balizas | — | Falla |
