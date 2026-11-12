"""
Lectura de patentes con EasyOCR (opcional).
Si easyocr no está instalado, la app sigue funcionando con ingreso manual.
"""

import importlib.util
import io
import re

import streamlit as st

from modulos.reglas import normalizar_patente

LETRAS_Y_NUMEROS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_FORMATO = re.compile(r"[A-Z]{4}[0-9]{2}|[A-Z]{2}[0-9]{4}")

# Confusiones típicas del OCR según la posición (letra donde va número y viceversa)
_A_LETRA = str.maketrans({"0": "O", "1": "I", "2": "Z", "4": "A", "5": "S", "6": "G", "8": "B"})
_A_NUMERO = str.maketrans({"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2",
                           "A": "4", "S": "5", "G": "6", "T": "7", "B": "8"})


def ocr_disponible() -> bool:
    return importlib.util.find_spec("easyocr") is not None


@st.cache_resource(show_spinner="Cargando lector de patentes (solo la primera vez)…")
def _lector():
    import easyocr
    return easyocr.Reader(["es", "en"], gpu=False)


@st.cache_data(show_spinner="Leyendo patente…", max_entries=30)
def leer_patente(foto: bytes) -> str | None:
    """Se ejecuta una sola vez por foto (caché): los clics posteriores no repiten el OCR."""
    import numpy as np
    from PIL import Image

    imagen = np.array(Image.open(io.BytesIO(foto)).convert("RGB"))
    textos = _lector().readtext(imagen, detail=0, allowlist=LETRAS_Y_NUMEROS)
    return elegir_patente(textos)


def elegir_patente(textos: list[str]) -> str | None:
    """
    De todos los textos que encontró el OCR, elige el que parece patente.
    1) un texto con formato completo (ABCD12 / AB1234);
    2) el formato dentro de los textos unidos ('AB', 'CD', '12' -> ABCD12);
    3) un texto de 6 caracteres corrigiendo confusiones (O/0, I/1, B/8...);
    4) si nada calza, el texto más largo, para que el guardia lo corrija.
    """
    limpios = [re.sub(r"[^A-Z0-9]", "", t.upper()) for t in textos]
    limpios = [t for t in limpios if t]
    if not limpios:
        return None
    for t in limpios:
        if _FORMATO.fullmatch(t):
            return normalizar_patente(t)
    m = _FORMATO.search("".join(limpios))
    if m:
        return normalizar_patente(m.group())
    for t in limpios:
        if len(t) == 6:
            corregido = t[:4].translate(_A_LETRA) + t[4:].translate(_A_NUMERO)
            if _FORMATO.fullmatch(corregido):
                return normalizar_patente(corregido)
    return max(limpios, key=len)
