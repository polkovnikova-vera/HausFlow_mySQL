###############################################################################################
# HAUSFLOW - OCR SERVICE
###############################################################################################
# Texterkennung für gescannte Rechnungen und Bilder
# Unterstützt: PNG, JPG, JPEG, HEIC
###############################################################################################

import os
import tempfile

from PIL import Image
from pillow_heif import register_heif_opener

# HEIC-Unterstützung für Pillow aktivieren
register_heif_opener()

# EasyOCR Reader wird nur einmal geladen
_reader = None


###############################################################################################
# OCR MODELL LADEN
###############################################################################################

def _get_reader():
    """
    EasyOCR-Modell einmal laden und danach wiederverwenden.
    Dadurch muss das Modell nicht bei jeder Rechnung neu geladen werden.
    """

    global _reader

    if _reader is None:
        import easyocr

        print("[HausFlow OCR] OCR-Modell wird geladen ...")

        _reader = easyocr.Reader(
            ["de", "en"],
            gpu=False
        )

        print("[HausFlow OCR] OCR-Modell bereit.")

    return _reader


###############################################################################################
# TEXT AUS BILD LESEN
###############################################################################################

def bildtext_lesen(path):
    """
    Text aus PNG, JPG, JPEG oder HEIC mit EasyOCR extrahieren.
    HEIC wird vorher temporär in PNG umgewandelt.
    """

    if not path:
        raise ValueError(
            "Keine Bilddatei ausgewählt."
        )

    if not os.path.exists(path):
        raise FileNotFoundError(
            "Bilddatei wurde nicht gefunden."
        )

    ext = os.path.splitext(path)[1].lower()

    reader = _get_reader()

    # -------------------------------------------------------------------------------------------
    # HEIC
    # -------------------------------------------------------------------------------------------

    if ext == ".heic":

        print(
            "[HausFlow OCR] HEIC erkannt -> "
            "temporäre PNG-Konvertierung."
        )

        image = Image.open(path)

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False
        )

        temp_path = temp_file.name
        temp_file.close()

        image.save(
            temp_path,
            "PNG"
        )

        try:
            result = reader.readtext(
                temp_path,
                detail=0,
                paragraph=False
            )

        finally:
            # Temporäre Datei wieder löschen
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------------------------------------
    # PNG / JPG / JPEG
    # -------------------------------------------------------------------------------------------

    elif ext in [
        ".png",
        ".jpg",
        ".jpeg"
    ]:

        result = reader.readtext(
            path,
            detail=0,
            paragraph=False
        )

    # -------------------------------------------------------------------------------------------
    # NICHT UNTERSTÜTZTES FORMAT
    # -------------------------------------------------------------------------------------------

    else:
        raise ValueError(
            "OCR unterstützt PNG, JPG, JPEG und HEIC."
        )

    # -------------------------------------------------------------------------------------------
    # OCR ERGEBNIS ZU TEXT ZUSAMMENFÜGEN
    # -------------------------------------------------------------------------------------------

    text = "\n".join(result).strip()

    if not text:
        raise RuntimeError(
            "Auf dem Bild konnte kein Text erkannt werden."
        )

    print(
        f"[HausFlow OCR] Text erkannt: "
        f"{len(text)} Zeichen"
    )

    return text

###############################################################################################
# TEXT AUS GESCANNTEM PDF LESEN
###############################################################################################

def pdf_ocr_lesen(path):
    """
    Gescannte PDF-Seiten in Bilder umwandeln
    und anschließend mit EasyOCR auslesen.
    """

    if not path:
        raise ValueError("Keine PDF-Datei ausgewählt.")

    if not os.path.exists(path):
        raise FileNotFoundError(
            "PDF-Datei wurde nicht gefunden."
        )

    import fitz

    reader = _get_reader()
    dokument = fitz.open(path)

    texte = []

    print(
        f"[HausFlow OCR] Scan-PDF erkannt: "
        f"{len(dokument)} Seite(n)"
    )

    try:
        for nummer, seite in enumerate(dokument):

            print(
                f"[HausFlow OCR] Seite "
                f"{nummer + 1}/{len(dokument)} wird gelesen ..."
            )

            # PDF-Seite mit höherer Auflösung rendern
            pixmap = seite.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False
            )

            temp_file = tempfile.NamedTemporaryFile(
                suffix=".png",
                delete=False
            )

            temp_path = temp_file.name
            temp_file.close()

            pixmap.save(temp_path)

            try:
                result = reader.readtext(
                    temp_path,
                    detail=0,
                    paragraph=False
                )

                seiten_text = "\n".join(result).strip()

                if seiten_text:
                    texte.append(seiten_text)

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    finally:
        dokument.close()

    text = "\n\n".join(texte).strip()

    if not text:
        raise RuntimeError(
            "Auch mit OCR konnte kein Text "
            "aus dem PDF erkannt werden."
        )

    print(
        f"[HausFlow OCR] PDF-OCR abgeschlossen: "
        f"{len(text)} Zeichen"
    )

    return text