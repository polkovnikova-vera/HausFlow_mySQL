###############################################################################################
# HAUSFLOW AI - RECHNUNGSANALYSE MIT DREI EIGENEN ML-MODELLEN
###############################################################################################
#
# MODELL 1:
# Volltext + erkannte/bestaetigte Beschreibung + Strukturkontext
# -> TF-IDF + Logistic Regression
# -> Kostenart
#
# MODELL 2:
# Einzelne Zeilen der Rechnung
# -> TF-IDF + Logistic Regression
# -> Welche Zeile ist die Leistungsbeschreibung?
#
# MODELL 3:
# Datums-Kandidaten + Kontext/Struktur
# -> Logistic Regression
# -> Rechnungsdatum
#
# Ollama:
# -> Firma, Betrag, Begründung usw.
# -> Fallback, wenn eigenes ML noch nicht sicher genug ist
#
###############################################################################################

import json
import os
import urllib.request
import urllib.error
import hashlib
import re
import unicodedata

from datetime import datetime

from services.ocr_service import (
    bildtext_lesen,
    pdf_ocr_lesen
)
from services.rechnung_validation import umlage_konsistenz_pruefen


###############################################################################################
# KONFIGURATION
###############################################################################################

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:1.5b"

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AI_DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

LEARNING_PATH = os.path.join(
    AI_DATA_DIR,
    "ai_training_data.json"
)


###############################################################################################
# MODELL 1 - KOSTENART
###############################################################################################

MODEL_PATH = os.path.join(
    AI_DATA_DIR,
    "rechnung_classifier.joblib"
)

MODEL_META_PATH = os.path.join(
    AI_DATA_DIR,
    "rechnung_classifier_meta.json"
)


###############################################################################################
# MODELL 2 - BESCHREIBUNG
###############################################################################################

BESCHREIBUNG_MODEL_PATH = os.path.join(
    AI_DATA_DIR,
    "beschreibung_classifier.joblib"
)

BESCHREIBUNG_META_PATH = os.path.join(
    AI_DATA_DIR,
    "beschreibung_classifier_meta.json"
)


###############################################################################################
# MODELL 3 - RECHNUNGSDATUM
###############################################################################################

DATUM_MODEL_PATH = os.path.join(
    AI_DATA_DIR,
    "datum_classifier.joblib"
)

DATUM_META_PATH = os.path.join(
    AI_DATA_DIR,
    "datum_classifier_meta.json"
)


###############################################################################################
# ML-EINSTELLUNGEN
###############################################################################################

MIN_TRAINING_EXAMPLES = 6
MIN_CLASSES = 2

# Momentan bewusst niedrig für deine Demo.
# Später z.B. 0.65 verwenden.
ML_CONFIDENCE_THRESHOLD = 0.65

# Mindestwahrscheinlichkeit für die Beschreibung.
# Für Tests zunächst relativ niedrig.
BESCHREIBUNG_CONFIDENCE_THRESHOLD = 0.65

# Mindestanzahl positiver Beschreibungsbeispiele.
MIN_BESCHREIBUNG_EXAMPLES = 4

# Mindestwahrscheinlichkeit fuer das Rechnungsdatum.
DATUM_CONFIDENCE_THRESHOLD = 0.65

# Mindestanzahl bestaetigter Rechnungsdaten.
MIN_DATUM_EXAMPLES = 4


###############################################################################################
# KOSTENARTEN
###############################################################################################

KOSTENARTEN = [
    "Grundsteuer",
    "Heizung & Warmwasser",
    "Wasser & Abwasser",
    "Müllabfuhr",
    "Gebäudereinigung & Straßenreinigung",
    "Gartenpflege",
    "Hausmeister",
    "Beleuchtung",
    "Versicherungen",
    "Aufzug",
    "Schornsteinreinigung",
    "Gemeinschaftsantenne/Breitbandkabel",
    "Waschraum",
    "Verwaltungskosten",
    "Instandhaltung / Reparatur",
    "Sonstiges"
]


###############################################################################################
# UMLAGESCHLÜSSEL
###############################################################################################

UMLAGESCHLUESSEL = [
    "Wohnfläche",
    "Miteigentumsanteile",
    "Personenanzahl",
    "Verbrauch",
    "Wohneinheiten",
    "Nicht umlagefähig"
]


###############################################################################################
# AKTUELLE DEMO-LOGIK
###############################################################################################

# Für deine Demo sollen momentan auch Verwaltungs-
# und Reparaturkosten verteilt werden.

NICHT_UMLAGEFAEHIG = set()


DEFAULT_UMLAGE = {
    "Grundsteuer": "Wohnfläche",
    "Heizung & Warmwasser": "Verbrauch",
    "Wasser & Abwasser": "Verbrauch",
    "Müllabfuhr": "Wohneinheiten",
    "Gebäudereinigung & Straßenreinigung": "Wohnfläche",
    "Gartenpflege": "Wohnfläche",
    "Hausmeister": "Wohnfläche",
    "Beleuchtung": "Wohnfläche",
    "Versicherungen": "Wohnfläche",
    "Aufzug": "Wohnfläche",
    "Schornsteinreinigung": "Wohnfläche",
    "Gemeinschaftsantenne/Breitbandkabel": "Wohneinheiten",
    "Waschraum": "Verbrauch",
    "Verwaltungskosten": "Miteigentumsanteile",
    "Instandhaltung / Reparatur": "Miteigentumsanteile",
    "Sonstiges": "Wohnfläche"
}


###############################################################################################
# RECHNUNGSTEXT LESEN
###############################################################################################

def rechnungstext_lesen(path):
    """
    Text aus PDF, TXT oder Bild-Rechnung lesen.
    """

    if not path:
        raise ValueError(
            "Keine Rechnung ausgewählt."
        )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Rechnung wurde nicht gefunden: {path}"
        )

    ext = os.path.splitext(path)[1].lower()


    # PDF
    if ext == ".pdf":

        from pypdf import PdfReader

        reader = PdfReader(path)

        text = ""

        for page in reader.pages:

            page_text = (
                page.extract_text()
                or ""
            )

            text += (
                page_text
                + "\n"
            )

        text = text.strip()

        if text:

            print(
                "[HausFlow AI] "
                f"PDF-Text erkannt: {len(text)} Zeichen"
            )

            return text

        print(
            "[HausFlow AI] "
            "Kein PDF-Text gefunden "
            "-> OCR-Fallback."
        )

        return pdf_ocr_lesen(path)


    # TXT
    if ext == ".txt":

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            text = file.read().strip()

        if not text:
            raise RuntimeError(
                "Die Textdatei enthält keinen Text."
            )

        return text


    # BILDER
    if ext in [
        ".png",
        ".jpg",
        ".jpeg",
        ".heic"
    ]:

        print(
            f"[HausFlow AI] "
            f"Bild erkannt ({ext}) "
            f"-> OCR."
        )

        return bildtext_lesen(path)


    raise ValueError(
        "Unterstützt werden "
        "PDF, TXT, PNG, JPG, JPEG und HEIC."
    )


###############################################################################################
# TRAININGSDATEN LADEN / SPEICHERN
###############################################################################################

def _lerndaten_laden():

    if not os.path.exists(
        LEARNING_PATH
    ):
        return []

    try:

        with open(
            LEARNING_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


def _lerndaten_schreiben(data):

    os.makedirs(
        AI_DATA_DIR,
        exist_ok=True
    )

    with open(
        LEARNING_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


###############################################################################################
# HILFSFUNKTION - RECHNUNGSZEILEN
###############################################################################################

def _rechnung_zeilen(text):
    """
    Zerlegt einen Rechnungstext in brauchbare einzelne Zeilen.

    Es werden KEINE fachlichen Schlüsselwörter verwendet.
    """

    if not text:
        return []

    zeilen = []

    for raw_line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            raw_line
        ).strip()

        if not line:
            continue

        # Extrem kurze OCR-Fragmente ignorieren.
        if len(line) < 3:
            continue

        # Sehr lange Absätze sind keine sinnvollen Einzelzeilen.
        if len(line) > 250:
            continue

        zeilen.append(line)

    return zeilen


###############################################################################################
# TEXT NORMALISIEREN
###############################################################################################

def _normalisieren(text):

    text = str(
        text
        or ""
    ).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"[^\wäöüß ]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


###############################################################################################
# TRAININGSBEISPIEL SPEICHERN
###############################################################################################

def lernbeispiel_speichern(
    rechnung_text,
    korrektur
):
    """
    Speichert eine vom Benutzer bestätigte Rechnung.

    Danach werden DREI eigene Modelle neu trainiert:

    1. Kostenart
    2. Beschreibung
    3. Rechnungsdatum
    """

    text = (
        rechnung_text
        or ""
    ).strip()

    if not text:

        return {
            "gespeichert": False,
            "training": ml_status(),
            "beispiele": lerndaten_anzahl()
        }


    kostenart = korrektur.get(
        "kostenart",
        "Sonstiges"
    )

    if kostenart not in KOSTENARTEN:
        kostenart = "Sonstiges"


    umlageschluessel = korrektur.get(
        "umlageschluessel",
        "Wohnfläche"
    )


    umlagefaehig = bool(
        korrektur.get(
            "umlagefaehig",
            True
        )
    )


    verteilung = korrektur.get(
        "verteilung",
        "ALLE"
    )


    beschreibung = str(
        korrektur.get(
            "beschreibung",
            ""
        )
    ).strip()

    datum = str(
        korrektur.get(
            "datum",
            ""
        )
    ).strip()


    if (
        kostenart in NICHT_UMLAGEFAEHIG
        or
        umlageschluessel == "Nicht umlagefähig"
    ):

        umlageschluessel = (
            "Nicht umlagefähig"
        )

        umlagefaehig = False

        verteilung = (
            "NICHT_UMLAGEFAEHIG"
        )


    now = datetime.now().isoformat(
        timespec="seconds"
    )


    text_hash = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:16]


    beispiel = {

        "id":
            f"{now}_{text_hash}",

        "gespeichert_am":
            now,

        "text_hash":
            text_hash,

        "rechnung_text":
            text[:12000],

        "kostenart":
            kostenart,

        "umlageschluessel":
            umlageschluessel,

        "umlagefaehig":
            umlagefaehig,

        "verteilung":
            verteilung,

        "beschreibung":
            beschreibung,

        "datum":
            datum
    }


    daten = _lerndaten_laden()

    daten.append(
        beispiel
    )

    _lerndaten_schreiben(
        daten
    )


    print(
        "[HausFlow AI] "
        f"Trainingsbeispiel gespeichert: "
        f"{len(daten)}"
    )


    # Modell 1
    kostenart_training = (
        modell_trainieren()
    )


    # Modell 2
    beschreibung_training = (
        beschreibung_modell_trainieren()
    )

    # Modell 3
    datum_training = (
        datum_modell_trainieren()
    )


    return {

        "gespeichert":
            True,

        "beispiele":
            len(daten),

        "training":
            kostenart_training,

        "beschreibung_training":
            beschreibung_training,

        "datum_training":
            datum_training
    }


def lerndaten_anzahl():

    return len(
        _lerndaten_laden()
    )



###############################################################################################
# MODELL 1 - KONTEXT FUER KOSTENART
###############################################################################################

def _kostenart_struktur_tokens(text):
    """
    Erzeugt neutrale Strukturmerkmale fuer Modell 1.
    Keine fachlichen Schluesselwoerter und keine feste Kostenart-Regel.
    """

    zeilen = _rechnung_zeilen(text)

    anzahl_zeilen = len(zeilen)
    betrag_zeilen = sum(
        1 for zeile in zeilen
        if re.search(r"\d+[.,]\d{2}\s*(?:EUR|€)?", zeile)
    )
    datum_zeilen = sum(
        1 for zeile in zeilen
        if re.search(
            r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b",
            zeile
        )
    )

    def bucket(value, borders):
        for border in borders:
            if value <= border:
                return str(border)
        return "mehr"

    return " ".join([
        f"struktur_zeilen_{bucket(anzahl_zeilen, [5, 10, 20, 40])}",
        f"struktur_betraege_{bucket(betrag_zeilen, [0, 1, 3, 6, 10])}",
        f"struktur_daten_{bucket(datum_zeilen, [0, 1, 2, 4])}"
    ])


def _kostenart_kontext_erstellen(text, beschreibung=""):
    """
    Erstellt den Eingabetext fuer Modell 1.

    Verwendet:
    - gesamten Rechnungstext
    - Kopfbereich der Rechnung
    - bestaetigte/erkannte Beschreibung
    - direkte Nachbarzeilen um die erkannte Beschreibung
    - neutrale Strukturmerkmale

    Dadurch bekommt Modell 1 mehr Kontext, ohne feste
    Schluesselwoerter fuer einzelne Kostenarten zu benutzen.
    """

    volltext = str(text or "").strip()
    beschreibung = str(beschreibung or "").strip()

    zeilen = _rechnung_zeilen(volltext)
    kopfbereich = "\n".join(zeilen[:6])

    umgebung = ""

    if beschreibung and zeilen:
        ziel = _normalisieren(beschreibung)

        best_index = None
        best_score = 0.0

        ziel_woerter = set(ziel.split())

        for index, zeile in enumerate(zeilen):
            norm = _normalisieren(zeile)

            if not norm:
                continue

            if ziel == norm or ziel in norm or norm in ziel:
                score = 1.0
            else:
                woerter = set(norm.split())
                union = ziel_woerter | woerter
                score = (
                    len(ziel_woerter & woerter) / len(union)
                    if union else 0.0
                )

            if score > best_score:
                best_score = score
                best_index = index

        if best_index is not None:
            start = max(0, best_index - 1)
            ende = min(len(zeilen), best_index + 2)
            umgebung = "\n".join(zeilen[start:ende])

    struktur = _kostenart_struktur_tokens(volltext)

    # Beschreibung wird bewusst staerker gewichtet, indem sie
    # als eigener Kontextblock mehrfach erscheint.
    beschreibung_block = ""
    if beschreibung:
        beschreibung_block = (
            f"BESCHREIBUNG_KONTEXT {beschreibung}\n"
            f"BESCHREIBUNG_KONTEXT {beschreibung}\n"
            f"BESCHREIBUNG_KONTEXT {beschreibung}"
        )

    return (
        f"VOLLTEXT\n{volltext}\n\n"
        f"KOPF_KONTEXT\n{kopfbereich}\n\n"
        f"{beschreibung_block}\n\n"
        f"UMGEBUNG_KONTEXT\n{umgebung}\n\n"
        f"STRUKTUR\n{struktur}"
    ).strip()


###############################################################################################
# MODELL 1
# KOSTENART TRAINIEREN
###############################################################################################

def modell_trainieren():
    """
    Modell 1 v2:
    Volltext + bestaetigte Beschreibung + Strukturkontext -> Kostenart.
    """

    daten = _lerndaten_laden()
    gueltig = []

    for d in daten:

        rechnung_text = str(
            d.get("rechnung_text", "")
        ).strip()

        beschreibung = str(
            d.get("beschreibung", "")
        ).strip()

        kostenart = d.get(
            "kostenart",
            "Sonstiges"
        )

        if (
            rechnung_text
            and kostenart in KOSTENARTEN
        ):
            kontext = _kostenart_kontext_erstellen(
                rechnung_text,
                beschreibung
            )

            gueltig.append(
                (
                    kontext,
                    kostenart
                )
            )

    anzahl = len(gueltig)

    klassen = sorted({
        y for _, y in gueltig
    })

    if (
        anzahl < MIN_TRAINING_EXAMPLES
        or len(klassen) < MIN_CLASSES
    ):
        return {
            "aktiv": False,
            "trainiert": False,
            "beispiele": anzahl,
            "klassen": len(klassen),
            "meldung": (
                "Noch nicht genug Trainingsdaten "
                "fuer Kostenart."
            )
        }

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        import joblib
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn und joblib fehlen."
        ) from exc

    x = [
        item[0]
        for item in gueltig
    ]

    y = [
        item[1]
        for item in gueltig
    ]

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
                max_features=12000
            )
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1500,
                class_weight="balanced",
                random_state=42
            )
        )
    ])

    # HIER LERNT MODELL 1 v2
    model.fit(x, y)

    os.makedirs(
        AI_DATA_DIR,
        exist_ok=True
    )

    joblib.dump(
        model,
        MODEL_PATH
    )

    meta = {
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "examples": anzahl,
        "classes": klassen,
        "model": (
            "TF-IDF Volltext + Beschreibung + Umgebung + "
            "Strukturkontext + LogisticRegression"
        )
    }

    with open(
        MODEL_META_PATH,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            meta,
            file,
            indent=4,
            ensure_ascii=False
        )

    return {
        "aktiv": True,
        "trainiert": True,
        "beispiele": anzahl,
        "klassen": len(klassen),
        "meldung": (
            "Kostenart-Modell v2 trainiert: "
            f"{anzahl} Beispiele, "
            f"{len(klassen)} Klassen."
        )
    }


def _zeilen_features(zeile, index, gesamt_zeilen):
    """
    Erstellt strukturelle Merkmale fuer eine Rechnungszeile.
    Es werden keine fachlichen Schluesselwoerter verwendet.
    """

    text = str(zeile or "").strip()

    position = index / max(gesamt_zeilen - 1, 1)

    hat_betrag = bool(
        re.search(r"\d+[.,]\d{2}", text)
    )

    hat_prozent = "%" in text

    hat_datum = bool(
        re.search(
            r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
            text
        )
    )

    hat_viele_zahlen = (
        sum(char.isdigit() for char in text) >= 4
    )

    return {
        "text": text,
        "position": float(position),
        "laenge": float(len(text)),
        "wortanzahl": float(len(text.split())),
        "hat_betrag": int(hat_betrag),
        "hat_prozent": int(hat_prozent),
        "hat_datum": int(hat_datum),
        "hat_viele_zahlen": int(hat_viele_zahlen)
    }


###############################################################################################
# MODELL 2
# TRAININGSDATEN FÜR BESCHREIBUNG ERZEUGEN
###############################################################################################

def _beschreibung_trainingsdaten():
    """
    Erstellt Trainingsdaten fuer Modell 2.

    Positive Klasse:
        Die Rechnungszeile, die am besten zur vom Benutzer
        bestaetigten Beschreibung derselben Rechnung passt.

    Negative Klasse:
        Alle anderen Zeilen derselben Rechnung.

    Zusaetzlich werden strukturelle Merkmale verwendet:
        Position, Laenge, Wortanzahl, Betrag, Prozent, Datum, Zahlen.

    Es werden keine fachlichen Schluesselwoerter verwendet.
    """

    daten = _lerndaten_laden()

    features = []
    labels = []

    positive_anzahl = 0
    negative_anzahl = 0

    for d in daten:

        rechnung_text = str(
            d.get("rechnung_text", "")
        ).strip()

        beschreibung = str(
            d.get("beschreibung", "")
        ).strip()

        if not rechnung_text or not beschreibung:
            continue

        zeilen = _rechnung_zeilen(rechnung_text)

        if not zeilen:
            continue

        ziel = _normalisieren(beschreibung)

        if not ziel:
            continue

        ziel_woerter = set(ziel.split())

        best_index = None
        best_score = 0.0

        for index, zeile in enumerate(zeilen):

            normalisiert = _normalisieren(zeile)

            if not normalisiert:
                continue

            if (
                ziel == normalisiert
                or ziel in normalisiert
                or normalisiert in ziel
            ):
                score = 1.0
            else:
                zeilen_woerter = set(normalisiert.split())
                union = ziel_woerter | zeilen_woerter

                if union:
                    score = len(ziel_woerter & zeilen_woerter) / len(union)
                else:
                    score = 0.0

            if score > best_score:
                best_score = score
                best_index = index

        # Nur Beispiele verwenden, bei denen die bestaetigte Beschreibung
        # im Rechnungstext sinnvoll wiedergefunden werden kann.
        if best_index is None or best_score < 0.30:
            continue

        gesamt_zeilen = len(zeilen)

        for index, zeile in enumerate(zeilen):

            features.append(
                _zeilen_features(
                    zeile,
                    index,
                    gesamt_zeilen
                )
            )

            if index == best_index:
                labels.append(1)
                positive_anzahl += 1
            else:
                labels.append(0)
                negative_anzahl += 1

    return (
        features,
        labels,
        positive_anzahl,
        negative_anzahl
    )

###############################################################################################
# MODELL 2 TRAINIEREN
###############################################################################################

def beschreibung_modell_trainieren():
    """
    Trainiert Modell 2.

    Text + Strukturmerkmale einer Rechnungszeile
    -> Wahrscheinlichkeit, dass diese Zeile die Beschreibung ist.
    """

    (
        feature_rows,
        labels,
        positive_anzahl,
        negative_anzahl
    ) = _beschreibung_trainingsdaten()

    if positive_anzahl < MIN_BESCHREIBUNG_EXAMPLES:
        return {
            "aktiv": False,
            "trainiert": False,
            "positive_beispiele": positive_anzahl,
            "negative_beispiele": negative_anzahl,
            "meldung": (
                "Noch nicht genug bestaetigte "
                "Beschreibungen fuer Modell 2 "
                f"({positive_anzahl}/{MIN_BESCHREIBUNG_EXAMPLES})."
            )
        }

    if not feature_rows:
        return {
            "aktiv": False,
            "trainiert": False,
            "meldung": "Keine Trainingsdaten vorhanden."
        }

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.compose import ColumnTransformer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        import pandas as pd
        import joblib

    except ImportError as exc:
        raise RuntimeError(
            "Fuer Modell 2 werden scikit-learn, pandas und joblib benoetigt."
        ) from exc

    df = pd.DataFrame(feature_rows)

    numerische_spalten = [
        "position",
        "laenge",
        "wortanzahl",
        "hat_betrag",
        "hat_prozent",
        "hat_datum",
        "hat_viele_zahlen"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "text",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,
                    max_features=8000
                ),
                "text"
            ),
            (
                "struktur",
                StandardScaler(),
                numerische_spalten
            )
        ]
    )

    model = Pipeline([
        ("features", preprocessor),
        (
            "classifier",
            LogisticRegression(
                max_iter=1200,
                class_weight="balanced",
                random_state=42
            )
        )
    ])

    # HIER LERNT MODELL 2
    model.fit(df, labels)

    os.makedirs(AI_DATA_DIR, exist_ok=True)
    joblib.dump(model, BESCHREIBUNG_MODEL_PATH)

    meta = {
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positive_examples": positive_anzahl,
        "negative_examples": negative_anzahl,
        "model": "TF-IDF + Strukturmerkmale + LogisticRegression"
    }

    with open(
        BESCHREIBUNG_META_PATH,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            meta,
            file,
            indent=4,
            ensure_ascii=False
        )

    return {
        "aktiv": True,
        "trainiert": True,
        "positive_beispiele": positive_anzahl,
        "negative_beispiele": negative_anzahl,
        "meldung": (
            "Beschreibung-Modell trainiert: "
            f"{positive_anzahl} positive und "
            f"{negative_anzahl} negative Zeilen."
        )
    }

###############################################################################################
# MODELL 1 - KOSTENART VORHERSAGEN
###############################################################################################

def ml_kostenart_vorhersagen(
    text,
    beschreibung=""
):
    """
    Modell 1 v2:
    Kostenart aus Volltext + Beschreibung + Umgebung + Struktur.
    """

    if not os.path.exists(
        MODEL_PATH
    ):
        return None

    try:
        import joblib

        model = joblib.load(
            MODEL_PATH
        )

        kontext = _kostenart_kontext_erstellen(
            text,
            beschreibung
        )

        probs = model.predict_proba(
            [kontext]
        )[0]

        classes = model.classes_

        best_idx = int(
            probs.argmax()
        )

        return {
            "kostenart": str(
                classes[best_idx]
            ),
            "confidence": float(
                probs[best_idx]
            ),
            "beschreibung_kontext": str(
                beschreibung or ""
            ).strip(),
            "kontext_typ": (
                "Volltext + Beschreibung + Umgebung + Struktur"
            )
        }

    except Exception as exc:
        print(
            "[HausFlow ML] "
            f"Kostenart-Vorhersage fehlgeschlagen: {exc}"
        )
        return None



###############################################################################################
# MODELL 2 - BESCHREIBUNG AUS NEUER RECHNUNG EXTRAHIEREN
###############################################################################################

def ml_beschreibung_vorhersagen(
    text,
    min_confidence=BESCHREIBUNG_CONFIDENCE_THRESHOLD
):
    """
    Bewertet jede Zeile der aktuellen Rechnung.

    Die ausgewaehlte Beschreibung ist immer eine Originalzeile
    aus genau dieser neuen Rechnung. Alte Beschreibungen werden
    nicht uebernommen.
    """

    if not os.path.exists(BESCHREIBUNG_MODEL_PATH):
        return None

    try:
        import joblib
        import pandas as pd

        model = joblib.load(BESCHREIBUNG_MODEL_PATH)

    except Exception as exc:
        print(
            "[HausFlow ML] "
            f"Beschreibung-Modell konnte nicht geladen werden: {exc}"
        )
        return None

    zeilen = _rechnung_zeilen(text)

    if not zeilen:
        return None

    feature_rows = [
        _zeilen_features(
            zeile,
            index,
            len(zeilen)
        )
        for index, zeile in enumerate(zeilen)
    ]

    df = pd.DataFrame(feature_rows)

    try:
        probs = model.predict_proba(df)
        classes = list(model.classes_)

        if 1 not in classes:
            return None

        positive_index = classes.index(1)

    except Exception as exc:
        print(
            "[HausFlow ML] "
            f"Beschreibung-Vorhersage fehlgeschlagen: {exc}"
        )
        return None

    kandidaten = []

    for index, zeile in enumerate(zeilen):

        confidence = float(
            probs[index, positive_index]
        )

        kandidaten.append({
            "zeile": zeile,
            "confidence": confidence,
            "position": feature_rows[index]["position"],
            "hat_betrag": feature_rows[index]["hat_betrag"],
            "hat_prozent": feature_rows[index]["hat_prozent"],
            "hat_datum": feature_rows[index]["hat_datum"],
            "wortanzahl": feature_rows[index]["wortanzahl"]
        })

    kandidaten.sort(
        key=lambda item: item["confidence"],
        reverse=True
    )

    beste = kandidaten[0]

    return {
        "gefunden": beste["confidence"] >= min_confidence,
        "beschreibung": beste["zeile"],
        "confidence": beste["confidence"],
        "kandidaten": kandidaten[:10]
    }


###############################################################################################
# MODELL 3 - RECHNUNGSDATUM
###############################################################################################

_DATUM_REGEX = re.compile(
    r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b"
)


def _datum_normalisieren(value):
    """Normalisiert ein Datum auf YYYY-MM-DD, wenn moeglich."""

    value = str(value or "").strip()

    if not value:
        return ""

    for fmt in (
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%y",
        "%d/%m/%y",
        "%d-%m-%y"
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def _datum_kandidaten(text):
    """
    Findet Datums-Kandidaten und erzeugt Kontext-/Strukturmerkmale.
    Keine fachliche Keyword-Liste: gelernt wird aus Textkontext und Position.
    """

    zeilen = _rechnung_zeilen(text)
    kandidaten = []

    for index, zeile in enumerate(zeilen):
        matches = list(_DATUM_REGEX.finditer(zeile))

        for match in matches:
            rohdatum = match.group(0)
            normdatum = _datum_normalisieren(rohdatum)

            if not normdatum:
                continue

            vorher = zeilen[index - 1] if index > 0 else ""
            nachher = zeilen[index + 1] if index + 1 < len(zeilen) else ""

            kontext = " | ".join(
                x for x in (vorher, zeile, nachher) if x
            )

            kandidaten.append({
                "datum": normdatum,
                "rohdatum": rohdatum,
                "zeile": zeile,
                "kontext": kontext,
                "position": float(index / max(len(zeilen) - 1, 1)),
                "zeilenlaenge": float(len(zeile)),
                "wortanzahl": float(len(zeile.split())),
                "anzahl_daten_zeile": float(len(matches)),
                "hat_betrag": int(bool(re.search(r"\d+[.,]\d{2}\s*(?:EUR|€)?", zeile))),
                "digit_anteil": float(
                    sum(ch.isdigit() for ch in zeile) / max(len(zeile), 1)
                )
            })

    return kandidaten


def _datum_trainingsdaten():
    """Erzeugt positive/negative Kandidaten aus bestaetigten Rechnungsdaten."""

    feature_rows = []
    labels = []
    positive_anzahl = 0
    negative_anzahl = 0

    for d in _lerndaten_laden():
        rechnung_text = str(d.get("rechnung_text", "")).strip()
        ziel = _datum_normalisieren(d.get("datum", ""))

        if not rechnung_text or not ziel:
            continue

        kandidaten = _datum_kandidaten(rechnung_text)

        if not kandidaten:
            continue

        positive_indices = [
            i for i, kandidat in enumerate(kandidaten)
            if kandidat["datum"] == ziel
        ]

        if not positive_indices:
            continue

        # Wenn dasselbe Datum mehrfach vorkommt, wird der erste Treffer positiv.
        best_positive = positive_indices[0]

        for i, kandidat in enumerate(kandidaten):
            feature_rows.append(kandidat.copy())

            if i == best_positive:
                labels.append(1)
                positive_anzahl += 1
            else:
                labels.append(0)
                negative_anzahl += 1

    return feature_rows, labels, positive_anzahl, negative_anzahl


def datum_modell_trainieren():
    """
    Trainiert Modell 3:
    Kontext + Struktur eines Datums-Kandidaten -> Rechnungsdatum ja/nein.
    """

    (
        feature_rows,
        labels,
        positive_anzahl,
        negative_anzahl
    ) = _datum_trainingsdaten()

    if positive_anzahl < MIN_DATUM_EXAMPLES:
        return {
            "aktiv": False,
            "trainiert": False,
            "positive_beispiele": positive_anzahl,
            "negative_beispiele": negative_anzahl,
            "meldung": (
                "Noch nicht genug bestaetigte Rechnungsdaten fuer Modell 3 "
                f"({positive_anzahl}/{MIN_DATUM_EXAMPLES})."
            )
        }

    if len(set(labels)) < 2:
        return {
            "aktiv": False,
            "trainiert": False,
            "positive_beispiele": positive_anzahl,
            "negative_beispiele": negative_anzahl,
            "meldung": "Fuer Modell 3 werden positive und negative Datums-Kandidaten benoetigt."
        }

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.compose import ColumnTransformer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        import pandas as pd
        import joblib
    except ImportError as exc:
        raise RuntimeError(
            "Fuer Modell 3 werden scikit-learn, pandas und joblib benoetigt."
        ) from exc

    df = pd.DataFrame(feature_rows)

    numerische_spalten = [
        "position",
        "zeilenlaenge",
        "wortanzahl",
        "anzahl_daten_zeile",
        "hat_betrag",
        "digit_anteil"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "text",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,
                    max_features=8000
                ),
                "kontext"
            ),
            (
                "struktur",
                StandardScaler(),
                numerische_spalten
            )
        ]
    )

    model = Pipeline([
        ("features", preprocessor),
        (
            "classifier",
            LogisticRegression(
                max_iter=1200,
                class_weight="balanced",
                random_state=42
            )
        )
    ])

    # HIER LERNT MODELL 3
    model.fit(df, labels)

    os.makedirs(AI_DATA_DIR, exist_ok=True)
    joblib.dump(model, DATUM_MODEL_PATH)

    meta = {
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positive_examples": positive_anzahl,
        "negative_examples": negative_anzahl,
        "model": "TF-IDF Kontext + Strukturmerkmale + LogisticRegression"
    }

    with open(DATUM_META_PATH, "w", encoding="utf-8") as file:
        json.dump(meta, file, indent=4, ensure_ascii=False)

    return {
        "aktiv": True,
        "trainiert": True,
        "positive_beispiele": positive_anzahl,
        "negative_beispiele": negative_anzahl,
        "meldung": (
            "Datum-Modell trainiert: "
            f"{positive_anzahl} positive und {negative_anzahl} negative Kandidaten."
        )
    }


def ml_datum_vorhersagen(
    text,
    min_confidence=DATUM_CONFIDENCE_THRESHOLD
):
    """Bewertet alle Datums-Kandidaten der aktuellen Rechnung."""

    if not os.path.exists(DATUM_MODEL_PATH):
        return None

    try:
        import joblib
        import pandas as pd

        model = joblib.load(DATUM_MODEL_PATH)
    except Exception as exc:
        print(f"[HausFlow ML] Datum-Modell konnte nicht geladen werden: {exc}")
        return None

    kandidaten = _datum_kandidaten(text)

    if not kandidaten:
        return None

    df = pd.DataFrame(kandidaten)

    try:
        probs = model.predict_proba(df)
        classes = list(model.classes_)

        if 1 not in classes:
            return None

        positive_index = classes.index(1)
    except Exception as exc:
        print(f"[HausFlow ML] Datum-Vorhersage fehlgeschlagen: {exc}")
        return None

    bewertet = []

    for index, kandidat in enumerate(kandidaten):
        item = kandidat.copy()
        item["confidence"] = float(probs[index, positive_index])
        bewertet.append(item)

    bewertet.sort(
        key=lambda item: item["confidence"],
        reverse=True
    )

    beste = bewertet[0]

    return {
        "gefunden": beste["confidence"] >= min_confidence,
        "datum": beste["datum"],
        "rohdatum": beste["rohdatum"],
        "zeile": beste["zeile"],
        "confidence": beste["confidence"],
        "kandidaten": bewertet[:10]
    }


###############################################################################################
# ML STATUS
###############################################################################################

def ml_status():

    daten = _lerndaten_laden()


    klassen = sorted({

        d.get("kostenart")

        for d in daten

        if (
            d.get("kostenart")
            in KOSTENARTEN
        )
    })


    status = {

        "aktiv":
            os.path.exists(
                MODEL_PATH
            ),

        "beschreibung_aktiv":
            os.path.exists(
                BESCHREIBUNG_MODEL_PATH
            ),

        "datum_aktiv":
            os.path.exists(
                DATUM_MODEL_PATH
            ),

        "beispiele":
            len(daten),

        "klassen":
            len(klassen),

        "trained_at":
            "",

        "beschreibung_trained_at":
            "",

        "datum_trained_at":
            ""
    }


    if os.path.exists(
        MODEL_META_PATH
    ):

        try:

            with open(
                MODEL_META_PATH,
                "r",
                encoding="utf-8"
            ) as file:

                meta = json.load(file)


            status[
                "trained_at"
            ] = meta.get(
                "trained_at",
                ""
            )

        except Exception:
            pass


    if os.path.exists(
        BESCHREIBUNG_META_PATH
    ):

        try:

            with open(
                BESCHREIBUNG_META_PATH,
                "r",
                encoding="utf-8"
            ) as file:

                meta = json.load(file)


            status[
                "beschreibung_trained_at"
            ] = meta.get(
                "trained_at",
                ""
            )


            status[
                "beschreibung_positive"
            ] = meta.get(
                "positive_examples",
                0
            )

        except Exception:
            pass


    if os.path.exists(
        DATUM_META_PATH
    ):
        try:
            with open(
                DATUM_META_PATH,
                "r",
                encoding="utf-8"
            ) as file:
                meta = json.load(file)

            status["datum_trained_at"] = meta.get("trained_at", "")
            status["datum_positive"] = meta.get("positive_examples", 0)
        except Exception:
            pass


    return status


###############################################################################################
# ML DEBUG - KOSTENART
###############################################################################################

def ml_top_woerter(
    top_n=10
):

    if not os.path.exists(
        MODEL_PATH
    ):
        return {}


    import joblib
    import numpy as np


    model = joblib.load(
        MODEL_PATH
    )


    tfidf = model.named_steps[
        "tfidf"
    ]


    classifier = model.named_steps[
        "classifier"
    ]


    feature_names = np.array(
        tfidf.get_feature_names_out()
    )


    ergebnis = {}


    for i, klasse in enumerate(
        classifier.classes_
    ):

        gewichte = (
            classifier.coef_[i]
        )


        top_indices = np.argsort(
            gewichte
        )[-top_n:][::-1]


        ergebnis[
            str(klasse)
        ] = [

            (
                str(
                    feature_names[
                        idx
                    ]
                ),

                float(
                    gewichte[
                        idx
                    ]
                )
            )

            for idx
            in top_indices
        ]


    return ergebnis


###############################################################################################
# ML DEBUG - KONKRETE RECHNUNG
###############################################################################################

def ml_debug_vorhersage(
    text,
    top_n=8
):
    """
    Debug fuer alle drei Modelle.
    Bei Modell 1 wird derselbe Kontext wie bei der echten Vorhersage verwendet.
    """

    result = {}

    # Modell 2 zuerst, damit die erkannte Beschreibung
    # fuer Modell 1 als Kontext benutzt werden kann.
    beschreibung_result = (
        ml_beschreibung_vorhersagen(
            text
        )
    )

    beschreibung_kontext = ""

    if (
        beschreibung_result
        and beschreibung_result.get("gefunden")
    ):
        beschreibung_kontext = beschreibung_result.get(
            "beschreibung",
            ""
        )

    # ===== KOSTENART DEBUG =====
    if os.path.exists(
        MODEL_PATH
    ):
        try:
            import joblib
            import numpy as np

            model = joblib.load(
                MODEL_PATH
            )

            tfidf = model.named_steps[
                "tfidf"
            ]

            classifier = model.named_steps[
                "classifier"
            ]

            kontext = _kostenart_kontext_erstellen(
                text,
                beschreibung_kontext
            )

            vector = tfidf.transform(
                [kontext]
            )

            probs = classifier.predict_proba(
                vector
            )[0]

            classes = classifier.classes_

            best_idx = int(
                np.argmax(probs)
            )

            klasse = str(
                classes[best_idx]
            )

            feature_names = np.array(
                tfidf.get_feature_names_out()
            )

            row = classifier.coef_[
                best_idx
            ]

            vorhandene_indices = (
                vector.nonzero()[1]
            )

            beitraege = []

            for idx in vorhandene_indices:
                beitrag = (
                    vector[0, idx]
                    *
                    row[idx]
                )

                beitraege.append(
                    (
                        str(feature_names[idx]),
                        float(beitrag)
                    )
                )

            beitraege.sort(
                key=lambda x: x[1],
                reverse=True
            )

            result["kostenart"] = klasse
            result["confidence"] = float(
                probs[best_idx]
            )

            result["wichtigste_woerter"] = (
                beitraege[:top_n]
            )

            result["wahrscheinlichkeiten"] = {
                str(c): float(p)
                for c, p in zip(
                    classes,
                    probs
                )
            }

            result["kostenart_kontext"] = {
                "beschreibung": beschreibung_kontext,
                "typ": (
                    "Volltext + Beschreibung + "
                    "Umgebung + Struktur"
                )
            }

        except Exception as exc:
            result[
                "kostenart_fehler"
            ] = str(exc)

    else:
        result[
            "kostenart_fehler"
        ] = (
            "Kostenart-Modell nicht vorhanden."
        )

    # ===== BESCHREIBUNG DEBUG =====
    result[
        "beschreibung_ml"
    ] = beschreibung_result

    # ===== DATUM DEBUG =====
    result[
        "datum_ml"
    ] = ml_datum_vorhersagen(text)

    return result



###############################################################################################
# OLLAMA
###############################################################################################

def _ollama_chat(
    prompt,
    model=OLLAMA_MODEL
):

    payload = {

        "model":
            model,

        "stream":
            False,

        "format":
            "json",

        "options": {
            "temperature":
                0.1
        },

        "messages": [

            {
                "role":
                    "system",

                "content": (
                    "Du bist ein präziser Assistent "
                    "für deutsche Immobilienverwaltung. "
                    "Extrahiere nur Informationen, "
                    "die aus der Rechnung ableitbar sind. "
                    "Gib ausschließlich valides JSON zurück."
                )
            },

            {
                "role":
                    "user",

                "content":
                    prompt
            }
        ]
    }


    request = urllib.request.Request(

        OLLAMA_URL,

        data=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),

        headers={
            "Content-Type":
                "application/json"
        },

        method="POST"
    )


    try:

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:

            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )


    except urllib.error.URLError as exc:

        raise RuntimeError(
            "Ollama ist nicht erreichbar. "
            "Prüfe, ob Ollama läuft."
        ) from exc


    content = (
        result.get(
            "message",
            {}
        )
        .get(
            "content",
            ""
        )
        .strip()
    )


    if not content:

        raise RuntimeError(
            "Ollama hat keine Analyse zurückgegeben."
        )


    try:

        return json.loads(
            content
        )


    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "Ollama-Antwort ist kein gültiges JSON: "
            f"{content[:300]}"
        ) from exc


###############################################################################################
# ADRESSEN AUS OCR-TEXT EXTRAHIEREN
###############################################################################################

_ADRESSROLLEN = {
    "leistungsort",
    "objektadresse",
    "rechnungsadresse",
    "lieferantenadresse",
    "unbekannt",
}


def _adressen_ollama_chat(text, model=OLLAMA_MODEL):
    """Extract address candidates in an isolated Ollama request."""
    prompt = f"""
Extrahiere alle im folgenden OCR-Text ausdruecklich vorhandenen Adressen.
Erfinde keine Adresse und ergaenze keine fehlenden Komponenten.
Verwende fuer rolle ausschliesslich: leistungsort, objektadresse,
rechnungsadresse, lieferantenadresse oder unbekannt.
Leistungsort ist der Ort der ausgefuehrten Leistung. Objektadresse ist das
betroffene Gebaeude. Rechnungsadresse ist die Rechnungs-/Empfaengeradresse.
Lieferantenadresse ist die Adresse des Rechnungsstellers. Wenn die Rolle nicht
klar erkennbar ist, verwende unbekannt. Rechnungsadresse ist nicht automatisch
die Objektadresse. Fehlende Komponenten muessen null sein.
originaltext muss ein woertliches, zusammenhaengendes Fragment aus dem OCR-Text
sein. Gib mehrere Adressen einzeln und in Textreihenfolge aus.
Antworte ausschliesslich mit JSON in diesem Format:
{{"adressen":[{{"rolle":"unbekannt","strasse":null,"hausnummer":null,"plz":null,"stadt":null,"originaltext":""}}]}}
Wenn keine Adresse gefunden wird, gib {{"adressen":[]}} zurueck.

OCR-TEXT:
{str(text or "")[:12000]}
"""
    return _ollama_chat(prompt, model=model)


def _adresskomponente_normalisieren(field, value):
    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFKC", value).casefold().replace("ß", "ss")
    if field == "strasse":
        value = re.sub(r"(?<=\w)str\.(?=\s|$)", "strasse", value.strip())
        value = re.sub(r"str\.?$", "strasse", value.strip())
        return re.sub(r"[^\w]", "", value, flags=re.UNICODE)
    if field == "hausnummer":
        return re.sub(r"\s+", "", value)
    return re.sub(r"[^\w]", "", value, flags=re.UNICODE)


def _adressen_antwort_normalisieren(ai_result, ocr_text):
    """Validate address shape and require the cited OCR fragment verbatim."""
    warnings = []
    if not isinstance(ai_result, dict):
        return [], ["Adress-Erkennung lieferte kein JSON-Objekt."]
    raw_addresses = ai_result.get("adressen")
    if not isinstance(raw_addresses, list):
        return [], ["Adress-Erkennung lieferte keine gueltige Adressen-Liste."]

    normalized = []
    fields = ("strasse", "hausnummer", "plz", "stadt")
    for index, raw in enumerate(raw_addresses):
        if not isinstance(raw, dict):
            warnings.append(f"Adresse {index + 1} wurde wegen ungueltiger Struktur ignoriert.")
            continue
        original = raw.get("originaltext")
        if not isinstance(original, str) or not original or original not in (ocr_text or ""):
            warnings.append(
                f"Adresse {index + 1} wurde ignoriert: Originaltext ist im OCR-Text nicht exakt belegt."
            )
            continue

        role = raw.get("rolle")
        role = role.strip().casefold() if isinstance(role, str) else "unbekannt"
        if role not in _ADRESSROLLEN:
            role = "unbekannt"
            warnings.append(f"Adresse {index + 1}: unklare Rolle auf 'unbekannt' gesetzt.")

        original_compact = _adresskomponente_normalisieren("strasse", original)
        address = {"rolle": role}
        for field in fields:
            value = raw.get(field)
            if value is None or value == "":
                address[field] = None
                continue
            if not isinstance(value, str):
                address[field] = None
                warnings.append(f"Adresse {index + 1}: ungueltige Komponente {field} verworfen.")
                continue
            component = _adresskomponente_normalisieren(field, value)
            if field == "hausnummer":
                house_pattern = re.escape(component)
                house_pattern = house_pattern.replace(r"/", r"\s*/\s*").replace(r"-", r"\s*-\s*")
                evidenced = bool(re.search(
                    rf"(?<![\w]){house_pattern}(?![\w/\-])",
                    original,
                    flags=re.IGNORECASE,
                ))
            elif field == "plz":
                digits = re.sub(r"\D", "", component)
                evidenced = bool(digits and re.search(
                    rf"(?<!\d){re.escape(digits)}(?!\d)", original
                ))
            else:
                evidenced = bool(component and component in original_compact)
            if not component or not evidenced:
                address[field] = None
                warnings.append(
                    f"Adresse {index + 1}: Komponente {field} ist im Originaltext nicht belegt und wurde verworfen."
                )
            else:
                address[field] = value.strip()
        address["originaltext"] = original
        normalized.append(address)

    return normalized, warnings


###############################################################################################
# HYBRIDE RECHNUNGSANALYSE
###############################################################################################

def rechnung_analysieren(
    text,
    wohnungen=None,
    model=OLLAMA_MODEL
):

    wohnungen = (
        wohnungen
        or []
    )


    wohnungsinfo = [

        {
            "id":
                w.get("id"),

            "nummer":
                w.get("nummer"),

            "flaeche":
                w.get("flaeche"),

            "mea":
                w.get(
                    "miteigentumsanteile"
                )
        }

        for w
        in wohnungen
    ]


    ###########################################################################################
    # MODELL 2 - BESCHREIBUNG ZUERST
    ###########################################################################################

    beschreibung_ml = (
        ml_beschreibung_vorhersagen(
            text
        )
    )

    beschreibung_kontext = ""

    if (
        beschreibung_ml
        and
        beschreibung_ml.get("gefunden")
    ):
        beschreibung_kontext = (
            beschreibung_ml.get(
                "beschreibung",
                ""
            )
        )


    ###########################################################################################
    # MODELL 1 v2 - KOSTENART MIT BESCHREIBUNGS-/UMGEBUNGSKONTEXT
    ###########################################################################################

    ml_result = (
        ml_kostenart_vorhersagen(
            text,
            beschreibung_kontext
        )
    )


    ml_hint = (
        "Kein eigenes ML-Modell verfügbar."
    )


    if ml_result:
        ml_hint = (
            "Eigenes ML-Modell v2 schlägt "
            f"'{ml_result['kostenart']}' "
            "mit Confidence "
            f"{ml_result['confidence']:.3f} vor. "
            "Verwendeter Kontext: Volltext + erkannte "
            "Beschreibung + Umgebung + Struktur."
        )


    ###########################################################################################
    # MODELL 3
    ###########################################################################################

    datum_ml = (
        ml_datum_vorhersagen(
            text
        )
    )


    ###########################################################################################
    # OLLAMA
    ###########################################################################################

    prompt = f"""
Analysiere folgende Rechnung für eine deutsche Hausverwaltung.

Erlaubte Kostenarten:
{json.dumps(KOSTENARTEN, ensure_ascii=False)}

Erlaubte Umlageschlüssel:
{json.dumps(UMLAGESCHLUESSEL, ensure_ascii=False)}

Wohnungen des Gebäudes:
{json.dumps(wohnungsinfo, ensure_ascii=False)}

INFO AUS DEM EIGENEN HAUSFLOW-ML-MODELL:
{ml_hint}

Gib GENAU dieses JSON-Schema zurück:

{{
  "firma": "",
  "datum": "YYYY-MM-DD oder leer",
  "betrag": 0.0,
  "kostenart": "eine erlaubte Kostenart",
  "umlagefaehig": true,
  "umlageschluessel": "ein erlaubter Umlageschlüssel",
  "verteilung": "ALLE oder AUSWAHL oder NICHT_UMLAGEFAEHIG",
  "betroffene_wohnung_ids": [],
  "beschreibung": "kurze sachliche Beschreibung",
  "confidence": 0.0,
  "begruendung": "kurze Begründung"
}}

Regeln:

- Nutze ausschließlich erlaubte Werte.
- Wenn keine konkrete Wohnung eindeutig genannt ist:
  verteilung="ALLE".
- AUSWAHL nur bei eindeutig genannter Wohnung.
- confidence liegt zwischen 0 und 1.

RECHNUNG:

{text[:12000]}
"""


    result = _ollama_chat(
        prompt,
        model=model
    )


    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "Ollama hat kein gültiges Analyse-Objekt geliefert."
        )



    # Address extraction is intentionally isolated: its failure must not
    # interrupt the existing invoice analysis or change its extracted fields.
    try:
        address_response = _adressen_ollama_chat(text, model=model)
        addresses, address_warnings = _adressen_antwort_normalisieren(
            address_response,
            text or "",
        )
    except Exception:
        addresses = []
        address_warnings = [
            "Adress-Erkennung fehlgeschlagen; der Hauptanalyse wurde fortgesetzt."
        ]
    result["adressen"] = addresses
    result["adressen_warnungen"] = address_warnings

    ###########################################################################################
    # RECHNUNGSDATUM
    ###########################################################################################

    if (
        datum_ml
        and
        datum_ml.get("gefunden")
    ):
        result["datum"] = datum_ml["datum"]
        result["datum_quelle"] = "Eigenes ML – aktuelle Rechnung"
        result["datum_confidence"] = datum_ml["confidence"]
        result["datum_kandidaten"] = datum_ml.get("kandidaten", [])
    else:
        result["datum_quelle"] = "Ollama-Fallback"

        if datum_ml:
            result["datum_confidence"] = datum_ml.get("confidence", 0)
            result["datum_kandidaten"] = datum_ml.get("kandidaten", [])
        else:
            result["datum_confidence"] = 0.0
            result["datum_kandidaten"] = []


    ###########################################################################################
    # BESCHREIBUNG
    #
    # WICHTIG:
    # Wenn Modell 2 sicher genug ist,
    # stammt Beschreibung DIREKT aus der NEUEN Rechnung.
    ###########################################################################################

    if (
        beschreibung_ml
        and
        beschreibung_ml.get(
            "gefunden"
        )
    ):

        result[
            "beschreibung"
        ] = (
            beschreibung_ml[
                "beschreibung"
            ]
        )


        result[
            "beschreibung_quelle"
        ] = (
            "Eigenes ML – aktuelle Rechnung"
        )


        result[
            "beschreibung_confidence"
        ] = (
            beschreibung_ml[
                "confidence"
            ]
        )


        result[
            "beschreibung_kandidaten"
        ] = (
            beschreibung_ml.get(
                "kandidaten",
                []
            )
        )


    else:

        result[
            "beschreibung_quelle"
        ] = (
            "Ollama-Fallback"
        )


        if beschreibung_ml:

            result[
                "beschreibung_confidence"
            ] = (
                beschreibung_ml.get(
                    "confidence",
                    0
                )
            )

        else:

            result[
                "beschreibung_confidence"
            ] = 0.0


    ###########################################################################################
    # KOSTENART ABSICHERN
    ###########################################################################################

    if (
        result.get(
            "kostenart"
        )
        not in KOSTENARTEN
    ):

        result[
            "kostenart"
        ] = (
            "Sonstiges"
        )


    if (
        result.get(
            "umlageschluessel"
        )
        not in UMLAGESCHLUESSEL
    ):

        result[
            "umlageschluessel"
        ] = (
            None
        )


    ###########################################################################################
    # MODELL 1 GEWINNT BEI GENÜGEND CONFIDENCE
    ###########################################################################################

    if (
        ml_result
        and
        ml_result[
            "confidence"
        ]
        >= ML_CONFIDENCE_THRESHOLD
    ):

        result[
            "kostenart"
        ] = (
            ml_result[
                "kostenart"
            ]
        )


        result[
            "confidence"
        ] = (
            ml_result[
                "confidence"
            ]
        )


        result[
            "entscheidungsquelle"
        ] = (
            "Eigenes ML-Modell v2"
        )

        result[
            "kostenart_kontext"
        ] = {
            "beschreibung":
                beschreibung_kontext,
            "typ":
                "Volltext + Beschreibung + Umgebung + Struktur"
        }


    elif ml_result:

        result[
            "entscheidungsquelle"
        ] = (

            "Ollama-Fallback "

            f"(ML nur "
            f"{ml_result['confidence']:.0%})"
        )


    else:

        result[
            "entscheidungsquelle"
        ] = (
            "Ollama-Fallback "
            "(ML noch nicht trainiert)"
        )


    ###########################################################################################
    # UMLAGE
    ###########################################################################################

    kostenart = result.get(
        "kostenart",
        "Sonstiges"
    )


    # Ollama provides a proposal, not a legal/accounting confirmation.
    # Keep explicit booleans as proposals and represent missing/invalid values
    # as None. Never infer eligibility or an allocation key from Kostenart.
    umlagefaehig_vorschlag = result.get("umlagefaehig")
    if not isinstance(umlagefaehig_vorschlag, bool):
        umlagefaehig_vorschlag = None
    result["umlagefaehig"] = umlagefaehig_vorschlag
    result["umlagefaehig_quelle"] = (
        "Ollama-Vorschlag – nicht fachlich bestätigt"
        if umlagefaehig_vorschlag is not None
        else "Nicht bestimmt"
    )

    # Keep Ollama's key only as a visible proposal. No object allocation
    # basis is supplied to this function, so it cannot be treated as selected.
    result["umlageschluessel_vorschlag"] = result.get("umlageschluessel")
    result["umlageschluessel"] = None

    if result.get("verteilung") not in ["ALLE", "AUSWAHL", "NICHT_UMLAGEFAEHIG"]:
        result["verteilung"] = None


    ###########################################################################################
    # WOHNUNGEN ABSICHERN
    ###########################################################################################

    valid_ids = {

        w.get("id")

        for w
        in wohnungen
    }


    selected = (

        result.get(
            "betroffene_wohnung_ids"
        )

        or []
    )


    result[
        "betroffene_wohnung_ids"
    ] = [

        x

        for x
        in selected

        if x
        in valid_ids
    ]


    umlage_pruefung = umlage_konsistenz_pruefen(
        umlagefaehig=result["umlagefaehig"],
        umlageschluessel=result.get("umlageschluessel"),
        verteilung=result.get("verteilung"),
        ausgewaehlte_wohnungen=result["betroffene_wohnung_ids"],
        kostenart=kostenart,
        # No Abrechnungsmodus or verified object rules are available here.
        modus=None,
    )
    result["umlagespruefung"] = umlage_pruefung
    result["umlage_status"] = "pruefen"
    result["warnungen"] = list(umlage_pruefung["warnungen"])
    result["warnungen"].extend(address_warnings)
    if umlagefaehig_vorschlag is not None:
        result["warnungen"].append(
            "Umlagefähigkeit ist nur ein Ollama-Vorschlag und muss vom Benutzer geprüft werden."
        )


    ###########################################################################################
    # STATUS
    ###########################################################################################

    result[
        "ml_status"
    ] = (
        ml_status()
    )


    ###########################################################################################
    # DEBUG
    ###########################################################################################

    try:

        result[
            "ml_debug"
        ] = (
            ml_debug_vorhersage(
                text,
                top_n=8
            )
        )

    except Exception as exc:

        print(
            "[HausFlow ML] "
            f"Debug fehlgeschlagen: {exc}"
        )


    return result
