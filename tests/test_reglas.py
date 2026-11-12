"""
Pruebas unitarias de la lógica de negocio (no necesitan Supabase ni internet).

    python tests/test_reglas.py        (o: python -m pytest tests)

Cubre: formato de patentes, clasificación del reporte con los umbrales
(incluidos los bordes), resolución de acceso en garita, semáforo de estados,
lectura del resultado guardado en 'observaciones', elección de patente del
OCR y compresión de fotos bajo 800 KB.
"""

import io
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from modulos import reglas  # noqa: E402
from modulos.evidencias import comprimir_imagen  # noqa: E402
from modulos.ocr import elegir_patente  # noqa: E402

BASE = dict(kilometraje=1, nivel_combustible=80, nivel_aceite=80, presion_rueda_1=32, presion_rueda_2=32,
            presion_rueda_3=32, presion_rueda_4=32, voltaje_bateria=12.6, luces_delanteras=True,
            luces_traseras=True, balizas=True, frenos=True)


def evaluar(**cambios):
    return reglas.evaluar_reporte({**BASE, **cambios})


def test_patentes():
    n = reglas.normalizar_patente
    assert n("abcd 12") == "ABCD-12"
    assert n("ABCD-12") == "ABCD-12"
    assert n("ab.12.34") == "AB-1234"
    assert n(None) == ""
    assert reglas.formato_patente_valido("ABCD-12")
    assert not reglas.formato_patente_valido("ABCD12")


def test_umbrales_y_bordes():
    assert evaluar() == ("OK", [])
    assert evaluar(presion_rueda_2=19.9)[0] == "CRITICO"
    assert evaluar(presion_rueda_2=20)[0] == "OBSERVACIONES"
    assert evaluar(presion_rueda_2=25)[0] == "OK"
    assert evaluar(nivel_aceite=24)[0] == "CRITICO"
    assert evaluar(nivel_aceite=25)[0] == "OBSERVACIONES"
    assert evaluar(nivel_aceite=50)[0] == "OK"
    assert evaluar(voltaje_bateria=11.7)[0] == "CRITICO"
    assert evaluar(voltaje_bateria=11.8)[0] == "OK"
    assert evaluar(voltaje_bateria=23.5)[0] == "CRITICO"      # sistema de 24 V
    assert evaluar(voltaje_bateria=25.2)[0] == "OK"
    assert evaluar(frenos=False) == ("CRITICO", ["CRÍTICO: Falla en sistema de frenos"])
    resultado, hallazgos = evaluar(nivel_combustible=10, balizas=False)
    assert resultado == "OBSERVACIONES" and len(hallazgos) == 2
    assert reglas.validar_kilometraje(10, 20) and reglas.validar_kilometraje(20, 20) is None


def test_resolucion_de_acceso():
    vehiculo = {"patente": "ABCD-12", "estado_operativo": "Operativo",
                "autorizaciones": [{"rut_conductor": "1", "vigente": True},
                                   {"rut_conductor": "2", "vigente": False}]}

    def conductor(rut, estado="Activo"):
        return {"rut": rut, "estado": estado}

    r = reglas.resolver_acceso
    assert r(None, conductor("1"))[0] == "DENEGADO"                 # patente desconocida
    assert r(vehiculo, None)[0] == "DENEGADO"                       # conductor desconocido
    assert r(vehiculo, conductor("1"))[0] == "AUTORIZADO"
    assert r(vehiculo, conductor("2"))[0] == "DENEGADO"             # autorización no vigente
    assert r(vehiculo, conductor("3"))[0] == "DENEGADO"             # sin autorización
    assert r(vehiculo, conductor("1", "Suspendido"))[0] == "DENEGADO"
    assert r(vehiculo, conductor("1", None))[0] == "AUTORIZADO"     # estado vacío = default 'Activo'
    assert r({**vehiculo, "estado_operativo": "Crítico"}, conductor("1"))[0] == "ALERTA"


def test_semaforo_de_estados():
    g = reglas.grupo_estado
    assert g("Operativo") == "Operativo"
    assert g("Requiere Mantención") == "Requiere Mantención"
    assert g("Crítico") == g("Inmovilizado") == "Crítico"
    assert g("No operativo") == g("Inoperativo") == g("En mantención") == "Requiere Mantención"


def test_observaciones():
    texto = reglas.componer_observaciones("CRITICO", ["CRÍTICO: Falla en sistema de frenos"],
                                          "Neumáticos 32/32/32/32 PSI", "ruido")
    reporte = {"observaciones": texto, "presion_neumaticos": True, "luces_operativas": True}
    assert reglas.leer_resultado(reporte) == "CRITICO"
    assert reglas.resumen_hallazgos(reporte) == "CRÍTICO: Falla en sistema de frenos"
    # reportes guardados por otros programas (sin prefijo)
    assert reglas.leer_resultado({"observaciones": "prueba", "presion_neumaticos": True,
                                  "luces_operativas": True}) == "OK"
    assert reglas.leer_resultado({"observaciones": None, "presion_neumaticos": False,
                                  "luces_operativas": True}) == "OBSERVACIONES"


def test_ocr_elegir_patente():
    assert elegir_patente(["CHILE", "ABCD12"]) == "ABCD-12"
    assert elegir_patente(["AB", "CD", "12"]) == "ABCD-12"          # pedazos separados
    assert elegir_patente(["A8CDI2"]) == "ABCD-12"                  # confusiones 8/B e I/1
    assert elegir_patente([]) is None


def test_compresion_bajo_800kb():
    random.seed(1)
    ruido = Image.frombytes("RGB", (3000, 2000), bytes(random.getrandbits(8) for _ in range(3000 * 2000 * 3)))
    buffer = io.BytesIO()
    ruido.save(buffer, "PNG")
    salida = comprimir_imagen(buffer.getvalue())
    assert buffer.tell() > 800_000 and len(salida) <= 800_000
    assert Image.open(io.BytesIO(salida)).format == "JPEG"


if __name__ == "__main__":
    pruebas = [f for nombre, f in sorted(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"OK  {prueba.__name__}")
    print(f"\n{len(pruebas)} grupos de pruebas aprobados.")
