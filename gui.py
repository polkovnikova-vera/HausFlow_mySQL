################################################################################################
# HAUSFLOW GUI
################################################################################################

import tkinter as tk
import sys
import os
import shutil
# SQLite wird für den direkten Zugriff auf die HausFlow-Datenbank verwendet.
import sqlite3

# WICHTIG:
# Pandas, Matplotlib und scikit-learn werden NICHT beim Programmstart importiert.
# Diese Bibliotheken sind relativ groß und werden nur im Analytics-Bereich benötigt.
# Durch den verzögerten Import startet das normale Tkinter-Hauptfenster schneller
# und mögliche Konflikte beim Erzeugen des ersten Tk-Fensters werden vermieden.

from tkinter import ttk
from tkinter import filedialog
from datetime import datetime
from tkinter import PhotoImage
import ctypes

# für PDF
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

################################################################################################
# PFAD-KONFIGURATION
################################################################################################

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


################################################################################################
# FARBEN
################################################################################################

BG_COLOR = "white"
BRAND_COLOR = "#49BDB8"
BRAND_HOVER = "#369B96"
TEXT_DARK = "#1F2D2D"

CARD_WIDTH = 400
CARD_HEIGHT = 230
IMAGE_WIDTH_SUBSAMPLE = 4

################################################################################################
# SERVICES IMPORTIEREN
################################################################################################
from services.gebaeude_service import (
    load_gebaeude,
    add_gebaeude,
    init_gebaeude_table,
    update_gebaeude,
    delete_gebaeude
)

from services.wohnungen_service import (
    init_wohnungen_table,
    add_wohnung,
    get_wohnungen_by_gebaeude
)

from services.meldungen_service import (
    init_meldungen_table,
    add_meldung,
    get_meldungen_by_gebaeude
)

from services.konto_service import (
    init_konto_table,
    add_kontobewegung,
    get_kontobewegungen_by_gebaeude
)

from services.ai_rechnung_service import (
    rechnungstext_lesen,
    rechnung_analysieren,
    lernbeispiel_speichern,
    lerndaten_anzahl,
    ml_status,
    ml_debug_vorhersage
)

################################################################################################
# HILFSFUNKTIONEN
################################################################################################

def only_numbers(value):
    # Leeres Feld erlauben, damit der Benutzer löschen kann
    if value == "":
        return True

    # Komma und Punkt als Dezimaltrennzeichen erlauben
    value = value.replace(",", ".")

    # Nur einen Dezimalpunkt erlauben
    if value.count(".") > 1:
        return False

    # Prüfen, ob nur Zahlen und ggf. ein Punkt enthalten sind
    return value.replace(".", "").isdigit()


def only_plz(value):
    # Leeres Feld erlauben
    if value == "":
        return True

    # Nur Zahlen erlauben und maximal 5 Zeichen
    return value.isdigit() and len(value) <= 5


def show_status(message):
    # Statusmeldung im Hauptfenster anzeigen
    status_var.set(message)


def set_window_icon(window):
    # Fenster-Icon setzen; fehlende Icon-Datei darf die App nicht stoppen
    icon_path = os.path.join(BASE_DIR, "assets", "icons", "hausflow.ico")
    if os.path.exists(icon_path):
        window.iconbitmap(icon_path)


def center_window(window, width, height):
    # Fenster mittig auf dem Bildschirm platzieren
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def add_logo(parent):
    # Logo im Fenster anzeigen
    header_frame = tk.Frame(parent, bg=BG_COLOR)
    header_frame.pack(pady=10)

    logo_label = tk.Label(header_frame, image=root.logo, bg=BG_COLOR)
    logo_label.image = root.logo
    logo_label.pack()

    return header_frame



def app_button(parent, text, command, width=30):
    # Einheitlicher Button im HausFlow-Stil
    btn = tk.Button(
        parent,
        text=text,
        width=width,
        command=command,
        bg=BRAND_COLOR,
        fg="white",
        activebackground=BRAND_HOVER,
        activeforeground="white",
        relief="flat",
        bd=0,
        cursor="hand2",
        font=("Arial", 10, "bold"),
        padx=10,
        pady=6
    )

    btn.bind("<Enter>", lambda e: btn.config(bg=BRAND_HOVER))
    btn.bind("<Leave>", lambda e: btn.config(bg=BRAND_COLOR))

    return btn

def clear_main_frame():
    # Hauptbereich leeren
    for widget in main_frame.winfo_children():
        widget.destroy()


def show_header(title):
    # Einheitlicher Header für alle Screens
    add_logo(main_frame)

    tk.Label(
        main_frame,
        text=title,
        font=("Arial", 18, "bold"),
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack(pady=10)



#####################################################################################################
#OPEN BELEG
#####################################################################################################

def open_beleg(path):
    # Beleg-Datei öffnen
    if not path:
        show_status("Kein Beleg vorhanden.")
        return

    if not os.path.exists(path):
        show_status("Beleg-Datei wurde nicht gefunden.")
        return

    os.startfile(path)

#####################################################################################################
#BELEG SPEICHERN
#####################################################################################################
def beleg_speichern(original_path):
    # Beleg in den Projektordner kopieren
    if not original_path:
        return ""

    beleg_ordner = os.path.join(BASE_DIR, "assets", "belege")
    os.makedirs(beleg_ordner, exist_ok=True)

    dateiname = os.path.basename(original_path)
    ziel_pfad = os.path.join(beleg_ordner, dateiname)

    # Falls Datei schon existiert, eindeutigen Namen erzeugen
    name, ext = os.path.splitext(dateiname)
    counter = 1

    while os.path.exists(ziel_pfad):
        ziel_pfad = os.path.join(beleg_ordner, f"{name}_{counter}{ext}")
        counter += 1

    shutil.copy2(original_path, ziel_pfad)

    return ziel_pfad



def gebaeude_loeschen(gebaeude):
    from tkinter import messagebox

    confirm = messagebox.askyesno(
        "Bestätigung",
        f"Gebäude {gebaeude['id']} wirklich löschen?"
    )

    if not confirm:
        return

    delete_gebaeude(gebaeude["id"])
    show_status(f"Gebäude {gebaeude['id']} gelöscht.")
    show_dashboard()

###############################################################################################
#BELEG ZEIGEN
###############################################################################################

def open_beleg(path):
    if not path:
        show_status("Kein Beleg vorhanden.")
        return

    if not os.path.exists(path):
        show_status("Datei nicht gefunden.")
        return

    ext = path.lower().split(".")[-1]

    if ext in ["png", "gif"]:
        window = tk.Toplevel(root)
        window.title("Beleg Vorschau")

        img = tk.PhotoImage(file=path)

        label = tk.Label(window, image=img)
        label.image = img
        label.pack()

    else:
        os.startfile(path)
###############################################################################################
#PDF ERSTELLEN NEBENKOSTEN
###############################################################################################
def pdf_escape(text):
    # Sonderzeichen für PDF-Text escapen
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def nebenkosten_pdf_erstellen(dateipfad, gebaeude, gesamt_kosten, ergebnis):
    c = pdf_canvas.Canvas(dateipfad, pagesize=A4)
    width, height = A4

    logo_path = os.path.join(BASE_DIR, "assets", "images", "logo.png")

    adr = gebaeude["adresse"]
    adresse = f"{adr['plz']} {adr['stadt']}, {adr['strasse']} {adr['hausnummer']}"

    # ===== LOGO =====
    if os.path.exists(logo_path):
        try:
            c.drawImage(
                logo_path,
                width - 300,
                height - 160,
                width=300,
                height=150,
                preserveAspectRatio=True
            )
        except Exception as e:
            print("LOGO PDF ERROR:", e)

    # ===== TITEL =====
    c.setFillColor(colors.HexColor(BRAND_COLOR))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, height - 90, "Nebenkostenabrechnung")

    # ===== GEBÄUDE INFO =====
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 125, f"Gebäude-ID: {gebaeude['id']}")
    c.drawString(50, height - 145, f"Adresse: {adresse}")

    # ===== LINIE =====
    c.setStrokeColor(colors.HexColor(BRAND_COLOR))
    c.setLineWidth(1.5)
    c.line(50, height - 165, width - 50, height - 165)

    # ===== GESAMTKOSTEN BOX =====
    c.setFillColor(colors.HexColor("#F2FBFA"))
    c.rect(50, height - 220, width - 100, 40, fill=True, stroke=False)

    c.setFillColor(colors.HexColor(BRAND_COLOR))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(65, height - 205, f"Gesamtkosten: {gesamt_kosten:.2f} EUR")

    y = height - 260

    # ===== TABELLE =====
    for wohnung, kostenarten in ergebnis.items():
        if y < 130:
            c.showPage()
            y = height - 70

        # Wohnung Header
        c.setFillColor(colors.HexColor(BRAND_COLOR))
        c.rect(50, y, width - 100, 24, fill=True, stroke=False)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(65, y + 7, f"Wohnung {wohnung}")

        y -= 28

        # Kostenarten
        gesamt_wohnung = 0

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)

        for art, betrag in kostenarten.items():
            if y < 90:
                c.showPage()
                y = height - 70

            c.drawString(70, y, art)
            c.drawRightString(width - 70, y, f"{betrag:.2f} EUR")

            c.setStrokeColor(colors.lightgrey)
            c.setLineWidth(0.5)
            c.line(65, y - 6, width - 65, y - 6)

            gesamt_wohnung += betrag
            y -= 18

        # Gesamt pro Wohnung
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.black)
        c.drawString(70, y, "Gesamt")
        c.drawRightString(width - 70, y, f"{gesamt_wohnung:.2f} EUR")

        y -= 28

    # ===== FOOTER =====
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawString(50, 55, "HausFlow Verwaltung")
    c.drawString(50, 40, "Musterstraße 1, 80331 München")
    c.drawString(50, 25, "E-Mail: info@hausflow.de | Tel: +49 123 456789")

    c.save()
###############################################################################################
###############################################################################################
# FENSTER
################################################################################################
###############################################################################################
#####################################################################################################
#1 Window
#####################################################################################################

def show_dashboard():
    # Startseite anzeigen
    clear_main_frame()
    show_header("HausFlow")

    CARD_WIDTH = 200
    CARD_HEIGHT = 235

    gebaeude_liste = load_gebaeude()

    app_button(
        main_frame,
        "Neues Gebäude hinzufügen",
        neues_gebaeude_form,
        width=30
    ).pack(pady=10)

    app_button(
        main_frame,
        "📊 Analytics",
        analytics_anzeigen,
        width=30
    ).pack(pady=5)
    
    tk.Label(
        main_frame,
        text="Suche nach Stadt / PLZ / Straße / Hausnummer:",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack()

    search_entry = tk.Entry(main_frame, width=40)
    search_entry.pack(pady=5)

    cards_frame = tk.Frame(main_frame, bg=BG_COLOR)
    cards_frame.pack(pady=15)

    def zeige_karten(liste_daten):
        # Alte Karten löschen
        for widget in cards_frame.winfo_children():
            widget.destroy()

        if not liste_daten:
            tk.Label(
                cards_frame,
                text="Keine Treffer",
                bg=BG_COLOR,
                fg=TEXT_DARK
            ).grid(row=0, column=0, padx=10, pady=10)
            return

        for index, g in enumerate(liste_daten):
            adr = g["adresse"]

            row = index // 3
            column = index % 3

            # Schatten
            shadow = tk.Frame(
                cards_frame,
                bg="#d9d9d9",
                width=CARD_WIDTH,
                height=CARD_HEIGHT
            )
            shadow.grid(row=row, column=column, padx=12, pady=12)
            shadow.grid_propagate(False)
            shadow.pack_propagate(False)

            # Karte über dem Schatten
            card = tk.Frame(
                shadow,
                bg="white",
                width=CARD_WIDTH - 6,
                height=CARD_HEIGHT - 6,
                bd=0,
                relief="flat",
                cursor="hand2"
            )
            card.place(x=0, y=0)
            card.grid_propagate(False)
            card.pack_propagate(False)

            # Bild oben
            img_label = tk.Label(
                card,
                image=root.building_img,
                bg="white",
                cursor="hand2"
            )
            img_label.pack(pady=(12, 6))

            title = f"{adr['strasse']} {adr['hausnummer']}"
            subtitle = f"{adr['plz']} {adr['stadt']}"
            details = (
                f"Fläche: {g['flaeche']} m²\n"
                f"MEA: {g['miteigentumsanteile']}"
            )

            tk.Label(
                card,
                text=title,
                font=("Arial", 10, "bold"),
                bg="white",
                fg=TEXT_DARK,
                wraplength=160,
                height=2,
                cursor="hand2"
            ).pack()

            tk.Label(
                card,
                text=subtitle,
                bg="white",
                fg=TEXT_DARK,
                wraplength=160,
                height=1,
                cursor="hand2"
            ).pack()

            tk.Label(
                card,
                text=details,
                bg="white",
                fg="gray",
                wraplength=160,
                height=2,
                cursor="hand2"
            ).pack(pady=5)

            def open_card(event=None, geb=g):
                gebaeude_detail_fenster(geb)

            card.bind("<Button-1>", open_card)
            shadow.bind("<Button-1>", open_card)

            for child in card.winfo_children():
                child.bind("<Button-1>", open_card)

    def suchen(event=None):
        such = search_entry.get().lower().strip()

        if not such:
            zeige_karten(gebaeude_liste)
            return

        gefiltert = []

        for g in gebaeude_liste:
            adr = g["adresse"]

            suchtext = (
                f"{adr['plz']} "
                f"{adr['stadt']} "
                f"{adr['strasse']} "
                f"{adr['hausnummer']}"
            ).lower()

            if such in suchtext:
                gefiltert.append(g)

        zeige_karten(gefiltert)

    search_entry.bind("<KeyRelease>", suchen)

    zeige_karten(gebaeude_liste)

    app_button(
        main_frame,
        "Beenden",
        root.destroy,
        width=30
    ).pack(pady=20)

################################################################################################
# KONTOBEWEGUNGEN ANZEIGEN
################################################################################################

def kontobewegungen_anzeigen(gebaeude):
    clear_main_frame()
    show_header("Kontobewegungen")

    bewegungen = get_kontobewegungen_by_gebaeude(gebaeude["id"])

    if not bewegungen:
        tk.Label(
            main_frame,
            text="Keine Kontobewegungen vorhanden.",
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=10)

        app_button(
            main_frame,
            "Zurück",
            lambda: gebaeude_detail_fenster(gebaeude),
            width=25
        ).pack(pady=20)

        return

    for b in bewegungen:
        text = (
            f"ID: {b['id']} | {b['datum']} | {b['typ']}\n"
            f"Kostenart: {b['kostenart']}\n"
            f"Umlageschlüssel: {b['umlageschluessel']}\n"
            f"Betrag: {b['betrag']} €\n"
            f"Beschreibung: {b['beschreibung']}\n"
            "-----------------------------"
        )

        tk.Label(
            main_frame,
            text=text,
            justify="left",
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=5)

        app_button(
            main_frame,
            "Beleg anzeigen",
            lambda path=b["beleg_pfad"]: open_beleg(path),
            width=25
        ).pack(pady=2)

    app_button(
        main_frame,
        "Zurück",
        lambda: gebaeude_detail_fenster(gebaeude),
        width=25
    ).pack(pady=20)

################################################################################################
# KONTOBEWEGUNG HINZUFÜGEN
################################################################################################

def kontobewegung_hinzufuegen(gebaeude):
    clear_main_frame()
    show_header("Kontobewegung hinzufügen")

    # Wohnungen für Verteilung laden
    wohnungen = get_wohnungen_by_gebaeude(gebaeude["id"])

    # Validierungsfunktion für Betrag registrieren
    vcmd = (root.register(only_numbers), "%P")

    content = tk.Frame(main_frame, bg=BG_COLOR)
    content.pack(pady=10)

    kostenarten_info = {
        "Grundsteuer": "Von der Gemeinde erhobene Steuer.",
        "Heizung & Warmwasser": "Kosten für Brennstoffe, Betrieb, Wartung und Messung.",
        "Wasser & Abwasser": "Kosten für Frischwasser und Entsorgung.",
        "Müllabfuhr": "Gebühren für die Entsorgung.",
        "Gebäudereinigung & Straßenreinigung": "Reinigung von Flur, Hof und angrenzenden Straßen.",
        "Gartenpflege": "Kosten für die Pflege der Außenanlagen.",
        "Hausmeister": "Kosten für den Hausmeisterdienst.",
        "Beleuchtung": "Strom für Flur, Hof und Außenlampen.",
        "Versicherungen": "Gebäudeversicherung und Haftpflicht.",
        "Aufzug": "Kosten für Betrieb, Überwachung und Reinigung.",
        "Schornsteinreinigung": "Kosten für den Schornsteinfeger.",
        "Gemeinschaftsantenne/Breitbandkabel": "Kosten für Kabelanschluss oder Antennenanlage.",
        "Waschraum": "Kosten für Reinigung und Strom in der Gemeinschaftswaschküche.",
        "Verwaltungskosten": "Nicht umlagefähige Kosten.",
        "Instandhaltung / Reparatur": "Nicht umlagefähige Kosten.",
        "Sonstiges": "Weitere Kosten."
    }

    row = 0

    # ===== DATUM =====
    tk.Label(content, text="Datum", bg=BG_COLOR, fg=TEXT_DARK).grid(
        row=row, column=0, padx=10, pady=6, sticky="e"
    )

    date_frame = tk.Frame(content, bg=BG_COLOR)
    date_frame.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    tag_box = ttk.Combobox(date_frame, values=[str(d).zfill(2) for d in range(1, 32)], width=5, state="readonly")
    monat_box = ttk.Combobox(date_frame, values=[str(m).zfill(2) for m in range(1, 13)], width=5, state="readonly")
    jahr_box = ttk.Combobox(date_frame, values=[str(y) for y in range(2018, 2035)], width=8, state="readonly")

    tag_box.set("01"); monat_box.set("01"); jahr_box.set("2026")
    tag_box.pack(side="left", padx=2); monat_box.pack(side="left", padx=2); jahr_box.pack(side="left", padx=2)
    row += 1

    # ===== TYP =====
    tk.Label(content, text="Typ", bg=BG_COLOR, fg=TEXT_DARK).grid(row=row, column=0, padx=10, pady=6, sticky="e")
    typ_box = ttk.Combobox(content, values=["Einnahme", "Ausgabe"], state="readonly", width=37)
    typ_box.set("Ausgabe")
    typ_box.grid(row=row, column=1, padx=10, pady=6, sticky="w")
    row += 1

    # ===== KOSTENART =====
    tk.Label(content, text="Kostenart", bg=BG_COLOR, fg=TEXT_DARK).grid(row=row, column=0, padx=10, pady=6, sticky="e")
    kostenart_box = ttk.Combobox(content, values=list(kostenarten_info.keys()), state="readonly", width=37)
    kostenart_box.set("Grundsteuer")
    kostenart_box.grid(row=row, column=1, padx=10, pady=6, sticky="w")
    row += 1

    info_label = tk.Label(content, text=kostenarten_info["Grundsteuer"], wraplength=330, fg="gray", bg=BG_COLOR, justify="left")
    info_label.grid(row=row, column=1, padx=10, pady=2, sticky="w")

    def kostenart_info_anzeigen(event=None):
        umlage_bestaetigt.set(False)
        info_label.config(text=kostenarten_info.get(kostenart_box.get(), ""))

    kostenart_box.bind("<<ComboboxSelected>>", kostenart_info_anzeigen)
    row += 1

    # ===== UMLAGESCHLÜSSEL =====
    tk.Label(content, text="Umlageschlüssel", bg=BG_COLOR, fg=TEXT_DARK).grid(row=row, column=0, padx=10, pady=6, sticky="e")
    umlage_box = ttk.Combobox(
        content,
        values=["Wohnfläche", "Miteigentumsanteile", "Personenanzahl", "Verbrauch", "Wohneinheiten", "Nicht umlagefähig"],
        state="readonly",
        width=37
    )
    umlage_box.set("")
    umlage_box.grid(row=row, column=1, padx=10, pady=6, sticky="w")
    row += 1

    # ===== BETRAG =====
    tk.Label(content, text="Betrag (€)", bg=BG_COLOR, fg=TEXT_DARK).grid(row=row, column=0, padx=10, pady=6, sticky="e")
    betrag_entry = tk.Entry(content, width=40, validate="key", validatecommand=vcmd)
    betrag_entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")
    row += 1

    # ===== BESCHREIBUNG =====
    tk.Label(content, text="Beschreibung", bg=BG_COLOR, fg=TEXT_DARK).grid(row=row, column=0, padx=10, pady=6, sticky="e")
    beschreibung_entry = tk.Entry(content, width=40)
    beschreibung_entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")
    row += 1

    # ===== BELEG =====
    tk.Label(content, text="Beleg", bg=BG_COLOR, fg=TEXT_DARK).grid(row=row, column=0, padx=10, pady=6, sticky="e")
    beleg_frame = tk.Frame(content, bg=BG_COLOR)
    beleg_frame.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    beleg_entry = tk.Entry(beleg_frame, width=28)
    beleg_entry.pack(side="left", padx=2)

    def beleg_auswaehlen():
        file_path = filedialog.askopenfilename(
            title="Beleg auswählen",
            filetypes=[
                ("PDF Dateien", "*.pdf"),
                ("Text Dateien", "*.txt"),
                ("PNG Bilder", "*.png"),
                ("JPG Bilder", "*.jpg"),
                ("JPEG Bilder", "*.jpeg"),
                ("HEIC Bilder", "*.heic"),
                ("Alle Dateien", "*.*")
            ]
        )
        if file_path:
            beleg_entry.delete(0, tk.END)
            beleg_entry.insert(0, file_path)

    app_button(beleg_frame, "📎", beleg_auswaehlen, width=4).pack(side="left", padx=2)
    row += 1

    # ===== BETROFFENE WOHNUNGEN =====
    tk.Label(content, text="Verteilen auf", bg=BG_COLOR, fg=TEXT_DARK).grid(row=row, column=0, padx=10, pady=6, sticky="ne")
    wohnungen_frame = tk.Frame(content, bg=BG_COLOR)
    wohnungen_frame.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    wohnung_vars = {}
    for w in wohnungen:
        var = tk.BooleanVar(value=True)
        wohnung_vars[w["id"]] = var
        text = f"Wohnung {w['nummer']} ({w['flaeche']} m²)"
        tk.Checkbutton(wohnungen_frame, text=text, variable=var, bg=BG_COLOR, fg=TEXT_DARK, activebackground=BG_COLOR).pack(anchor="w")
    row += 1

    umlage_bestaetigt = tk.BooleanVar(value=False)
    tk.Checkbutton(
        content,
        text="Ich habe Umlagefähigkeit und Verteilung geprüft und bestätige die Auswahl.",
        variable=umlage_bestaetigt,
        bg=BG_COLOR,
        fg=TEXT_DARK,
        activebackground=BG_COLOR,
        wraplength=460,
        justify="left",
    ).grid(row=row, column=1, padx=10, pady=4, sticky="w")
    row += 1

    # ===== AI ERGEBNIS / VORSCHAU =====
    ai_card = tk.Frame(content, bg="#F2FBFA", bd=1, relief="solid")
    ai_card.grid(row=row, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    tk.Label(
        ai_card,
        text="🤖 AI-Ergebnis",
        font=("Arial", 11, "bold"),
        bg="#F2FBFA",
        fg=TEXT_DARK
    ).pack(anchor="w", padx=12, pady=(10, 4))

    ai_summary_label = tk.Label(
        ai_card,
        text="Noch keine Rechnung analysiert.",
        wraplength=500,
        justify="left",
        bg="#F2FBFA",
        fg=TEXT_DARK
    )
    ai_summary_label.pack(anchor="w", padx=12, pady=4)

    ai_distribution_label = tk.Label(
        ai_card,
        text="",
        wraplength=500,
        justify="left",
        bg="#F2FBFA",
        fg=TEXT_DARK,
        font=("Consolas", 9)
    )
    ai_distribution_label.pack(anchor="w", padx=12, pady=(4, 10))
    row += 1

    # Letzte analysierte Rechnung zwischenspeichern, damit bestätigte Korrekturen gelernt werden können.
    ai_state = {"rechnung_text": "", "result": None}

    def ml_erklaeren():
        """Zeigt, wie das eigene ML-Modell die Rechnung bewertet."""

        text = ai_state.get("rechnung_text", "").strip()

        if not text:
            show_status("Bitte zuerst eine Rechnung analysieren.")
            return

        try:
            debug = ml_debug_vorhersage(
                text,
                top_n=10
            )

            if debug.get("fehler"):
                show_status(debug["fehler"])
                return

            fenster = tk.Toplevel(root)
            fenster.title("HausFlow – ML erklären")
            fenster.configure(bg=BG_COLOR)

            center_window(
                fenster,
                700,
                700
            )

            set_window_icon(fenster)

            # ===== TITEL =====
            tk.Label(
                fenster,
                text="🧠 Eigenes ML-Modell",
                font=("Arial", 18, "bold"),
                bg=BG_COLOR,
                fg=TEXT_DARK
            ).pack(pady=(20, 5))

            tk.Label(
                fenster,
                text="Warum wurde diese Kostenart gewählt?",
                font=("Arial", 11),
                bg=BG_COLOR,
                fg="gray"
            ).pack(pady=(0, 15))

            # ===== ERGEBNIS =====
            kostenart = debug.get(
                "kostenart",
                "—"
            )

            # ===== BESCHREIBUNG =====

            result = ai_state.get("result") or {}

            beschreibung = result.get(
                "beschreibung",
                "—"
            )

            beschreibung_quelle = result.get(
                "beschreibung_quelle",
                "Unbekannt"
            )


            confidence = (
                float(
                    debug.get(
                        "confidence",
                        0
                    )
                )
                * 100
            )

            ergebnis_frame = tk.Frame(
                fenster,
                bg="#F2FBFA",
                bd=1,
                relief="solid"
            )

            ergebnis_frame.pack(
                fill="x",
                padx=30,
                pady=10
            )

            tk.Label(
                ergebnis_frame,
                text=f"Vorhersage: {kostenart}",
                font=("Arial", 13, "bold"),
                bg="#F2FBFA",
                fg=TEXT_DARK
            ).pack(
                anchor="w",
                padx=15,
                pady=(12, 4)
            )

            tk.Label(
                ergebnis_frame,
                text=f"Konfidenz: {confidence:.1f} %",
                font=("Arial", 11),
                bg="#F2FBFA",
                fg=TEXT_DARK
            ).pack(
                anchor="w",
                padx=15,
                pady=(0, 12)
            )

            tk.Label(
                ergebnis_frame,
                text=f"Beschreibung: {beschreibung}",
                font=("Arial", 11, "bold"),
                bg="#F2FBFA",
                fg=TEXT_DARK,
                wraplength=600,
                justify="left"
            ).pack(
                anchor="w",
                padx=15,
                pady=(5, 3)
            )

            tk.Label(
                ergebnis_frame,
                text=f"Quelle der Beschreibung: {beschreibung_quelle}",
                font=("Arial", 11),
                bg="#F2FBFA",
                fg=TEXT_DARK
            ).pack(
                anchor="w",
                padx=15,
                pady=(0, 12)
            )

            # ===== WICHTIGSTE WÖRTER =====
            tk.Label(
                fenster,
                text="Wichtigste Wörter / Wortkombinationen",
                font=("Arial", 12, "bold"),
                bg=BG_COLOR,
                fg=TEXT_DARK
            ).pack(
                anchor="w",
                padx=30,
                pady=(10, 5)
            )

            wort_text = tk.Text(
                fenster,
                width=70,
                height=10,
                font=("Consolas", 10)
            )

            wort_text.pack(
                fill="x",
                padx=30
            )

            wichtige_woerter = debug.get(
                "wichtigste_woerter",
                []
            )

            if wichtige_woerter:

                for wort, beitrag in wichtige_woerter:

                    wort_text.insert(
                        "end",
                        f"{wort:<35} {beitrag:+.4f}\n"
                    )

            else:

                wort_text.insert(
                    "end",
                    "Keine relevanten Wörter gefunden."
                )

            wort_text.config(
                state="disabled"
            )

                        # ===== WAHRSCHEINLICHKEITEN KOSTENART =====

            tk.Label(
                fenster,
                text="Wahrscheinlichkeiten der Kostenarten",
                font=("Arial", 12, "bold"),
                bg=BG_COLOR,
                fg=TEXT_DARK
            ).pack(
                anchor="w",
                padx=30,
                pady=(15, 5)
            )

            probability_text = tk.Text(
                fenster,
                width=70,
                height=10,
                font=("Consolas", 10)
            )

            probability_text.pack(
                fill="x",
                padx=30
            )

            wahrscheinlichkeiten = debug.get(
                "wahrscheinlichkeiten",
                {}
            )

            sortiert = sorted(
                wahrscheinlichkeiten.items(),
                key=lambda item: item[1],
                reverse=True
            )

            for klasse, probability in sortiert:

                probability_text.insert(
                    "end",
                    f"{klasse:<45} {probability * 100:6.1f} %\n"
                )

            probability_text.config(
                state="disabled"
            )


            # ==========================================================
            # MODELL 2 - BESCHREIBUNG
            # ==========================================================

            tk.Label(
                fenster,
                text="Beschreibung – eigenes ML",
                font=("Arial", 12, "bold"),
                bg=BG_COLOR,
                fg=TEXT_DARK
            ).pack(
                anchor="w",
                padx=30,
                pady=(20, 5)
            )

            beschreibung_ml = debug.get(
                "beschreibung_ml"
            )

            beschreibung_text = tk.Text(
                fenster,
                width=70,
                height=12,
                font=("Consolas", 10)
            )

            beschreibung_text.pack(
                fill="both",
                expand=True,
                padx=30,
                pady=(0, 10)
            )

            if beschreibung_ml:

                gewaehlte_zeile = beschreibung_ml.get(
                    "beschreibung",
                    "—"
                )

                beschreibung_confidence = float(
                    beschreibung_ml.get(
                        "confidence",
                        0
                    )
                )

                gefunden = beschreibung_ml.get(
                    "gefunden",
                    False
                )

                beschreibung_text.insert(
                    "end",
                    "GEWÄHLTE ZEILE AUS DER AKTUELLEN RECHNUNG\n"
                )

                beschreibung_text.insert(
                    "end",
                    f"{gewaehlte_zeile}\n\n"
                )

                beschreibung_text.insert(
                    "end",
                    f"Confidence: {beschreibung_confidence * 100:.1f} %\n"
                )

                if gefunden:

                    beschreibung_text.insert(
                        "end",
                        "Entscheidung: Eigenes ML – aktuelle Rechnung\n\n"
                    )

                else:

                    beschreibung_text.insert(
                        "end",
                        "Entscheidung: Confidence zu niedrig → Ollama-Fallback\n\n"
                    )

                beschreibung_text.insert(
                    "end",
                    "BEWERTETE ZEILEN DER RECHNUNG\n\n"
                )

                kandidaten = beschreibung_ml.get(
                    "kandidaten",
                    []
                )

                for kandidat in kandidaten:

                    zeile = kandidat.get(
                        "zeile",
                        ""
                    )

                    score = float(
                        kandidat.get(
                            "confidence",
                            0
                        )
                    )

                    beschreibung_text.insert(
                        "end",
                        f"{score * 100:6.1f} %   {zeile}\n"
                    )

            else:

                beschreibung_text.insert(
                    "end",
                    "Beschreibung-Modell hat kein Ergebnis geliefert.\n"
                )

            beschreibung_text.config(
                state="disabled"
            )


            # ===== SCHLIESSEN =====

            app_button(
                fenster,
                "Schließen",
                fenster.destroy,
                width=20
            ).pack(pady=20)

        except Exception as e:

            show_status(
                f"ML-Erklärung fehlgeschlagen: {e}"
            )


    def verteilung_vorschau():
        """Aktuelle Auswahl der Wohnungen mit dem gewählten Umlageschlüssel berechnen."""

        try:
            betrag = float(
                betrag_entry.get().replace(",", ".")
            )

        except ValueError:
            return (
                "Noch kein gültiger Betrag "
                "für die Verteilung vorhanden."
            )


        aktive_wohnungen = [
            w
            for w in wohnungen
            if wohnung_vars[w["id"]].get()
        ]

        umlage = umlage_box.get()


        if not umlage:
            return "Prüfung erforderlich: Umlageschlüssel auswählen."


        if umlage == "Nicht umlagefähig":

            return (
                "Nicht umlagefähig → "
                "0,00 € werden auf Wohnungen verteilt."
            )


        if not aktive_wohnungen:

            return (
                "Keine Wohnung für die Verteilung ausgewählt."
            )


        if umlage in [
            "Verbrauch",
            "Personenanzahl"
        ]:

            return (
                f"{umlage}: betroffene Wohnungen wurden erkannt, "
                "aber für die exakte Berechnung fehlen aktuell "
                "Verbrauchs- bzw. Personendaten in HausFlow."
            )


        werte = {}


        if umlage == "Wohnfläche":

            gesamt = sum(
                float(
                    str(
                        w["flaeche"]
                    ).replace(",", ".")
                )
                for w in aktive_wohnungen
            )

            if gesamt <= 0:

                return (
                    "Wohnfläche kann nicht berechnet werden."
                )


            for w in aktive_wohnungen:

                basis = float(
                    str(
                        w["flaeche"]
                    ).replace(",", ".")
                )

                werte[
                    w["nummer"]
                ] = (
                    betrag
                    *
                    basis
                    /
                    gesamt
                )


        elif umlage == "Miteigentumsanteile":

            gesamt = sum(
                float(
                    str(
                        w["miteigentumsanteile"]
                    ).replace(",", ".")
                )
                for w in aktive_wohnungen
            )

            if gesamt <= 0:

                return (
                    "Miteigentumsanteile "
                    "können nicht berechnet werden."
                )


            for w in aktive_wohnungen:

                basis = float(
                    str(
                        w["miteigentumsanteile"]
                    ).replace(",", ".")
                )

                werte[
                    w["nummer"]
                ] = (
                    betrag
                    *
                    basis
                    /
                    gesamt
                )


        else:

            anteil = (
                betrag
                /
                len(
                    aktive_wohnungen
                )
            )

            for w in aktive_wohnungen:

                werte[
                    w["nummer"]
                ] = anteil


        zeilen = [
            f"Voraussichtliche Verteilung ({umlage}):"
        ]


        for nummer, kosten in werte.items():

            zeilen.append(
                f"  Wohnung {nummer:<8} {kosten:>9.2f} €"
            )


        zeilen.append(
            f"  {'SUMME':<16} "
            f"{sum(werte.values()):>9.2f} €"
        )


        return "\n".join(
            zeilen
        )


    def ai_vorschau_aktualisieren(event=None):

        ai_distribution_label.config(
            text=verteilung_vorschau()
        )


    # Manuelle Änderungen sollen die Vorschau ebenfalls aktualisieren

    def umlage_auswahl_geaendert(event=None):
        umlage_bestaetigt.set(False)
        if umlage_box.get() == "Nicht umlagefähig":
            for var in wohnung_vars.values():
                var.set(False)
        ai_vorschau_aktualisieren()

    umlage_box.bind(
        "<<ComboboxSelected>>",
        umlage_auswahl_geaendert,
        add="+"
    )

    betrag_entry.bind(
        "<KeyRelease>",
        ai_vorschau_aktualisieren
    )


    for var in wohnung_vars.values():

        var.trace_add(
            "write",
            lambda *args: (
                umlage_bestaetigt.set(False),
                ai_vorschau_aktualisieren()
            )
        )


    def ai_rechnung_analysieren():

        umlage_bestaetigt.set(False)
        umlage_box.set("")
        for var in wohnung_vars.values():
            var.set(False)

        path = beleg_entry.get().strip()


        if not path:

            show_status(
                "Bitte zuerst eine Rechnung auswählen."
            )

            return


        ai_summary_label.config(
            text="🤖 Rechnung wird analysiert ..."
        )

        ai_distribution_label.config(
            text=""
        )

        root.update_idletasks()


        try:

            text = rechnungstext_lesen(
                path
            )


            result = rechnung_analysieren(
                text,
                wohnungen
            )


            ai_state[
                "rechnung_text"
            ] = text


            ai_state[
                "result"
            ] = result


                       # ===== DATUM =====

            datum_raw = str(
                result.get("datum", "")
                or ""
            ).strip()
            
            # Für die spätere Anzeige im AI-Ergebnis
            datum = datum_raw

            datum_obj = None

            # Поддерживаем несколько форматов даты.
            for fmt in (
                "%Y-%m-%d",
                "%d.%m.%Y",
                "%d/%m/%Y",
                "%d-%m-%Y"
            ):
                try:
                    datum_obj = datetime.strptime(
                        datum_raw,
                        fmt
                    )
                    break
                except ValueError:
                    pass

            if datum_obj is not None:

                y = datum_obj.strftime("%Y")
                m = datum_obj.strftime("%m")
                d = datum_obj.strftime("%d")

                # Проверяем диапазон года.
                if y not in jahr_box["values"]:
                    print(
                        "[HausFlow GUI] "
                        f"Datum erkannt, aber Jahr {y} "
                        "ist nicht in der Datumsauswahl."
                    )

                else:
                    jahr_box.set(y)
                    monat_box.set(m)
                    tag_box.set(d)

                    print(
                        "[HausFlow GUI] "
                        f"Datum in Formular gesetzt: "
                        f"{d}.{m}.{y}"
                    )

            elif datum_raw:

                print(
                    "[HausFlow GUI] "
                    f"Datum konnte nicht in Formular "
                    f"übernommen werden: {datum_raw!r}"
                )

            else:

                print(
                    "[HausFlow GUI] "
                    "AI hat kein Datum geliefert."
                )

            # ===== KOSTENART =====

            kostenart = result.get(
                "kostenart",
                "Sonstiges"
            )


            if kostenart in kostenart_box["values"]:

                kostenart_box.set(
                    kostenart
                )

                kostenart_info_anzeigen()


            # ===== UMLAGESCHLÜSSEL =====

            umlage_vorschlag = result.get("umlageschluessel_vorschlag")
            umlage_box.set("")


            # ===== BETRAG =====

            betrag = result.get(
                "betrag"
            )


            if (
                isinstance(
                    betrag,
                    (int, float)
                )
                and
                betrag >= 0
            ):

                betrag_entry.delete(
                    0,
                    tk.END
                )

                betrag_entry.insert(
                    0,
                    f"{betrag:.2f}"
                )


            # ===== BESCHREIBUNG =====

            beschreibung = (
                result.get(
                    "beschreibung"
                )
                or
                result.get(
                    "firma"
                )
                or
                ""
            )


            beschreibung_entry.delete(
                0,
                tk.END
            )


            beschreibung_entry.insert(
                0,
                beschreibung
            )


            # ===== WOHNUNGSVERTEILUNG =====

            # AI-Verteilung bleibt ein Vorschlag. Die Form verlangt eine
            # neue ausdrückliche Auswahl und Bestätigung durch den Benutzer.
            for var in wohnung_vars.values():
                var.set(False)


            # ===== ANZEIGEDATEN =====

            confidence = float(
                result.get(
                    "confidence",
                    0
                )
            ) * 100


            begruendung = result.get(
                "begruendung",
                ""
            )


            entscheidungsquelle = result.get(
                "entscheidungsquelle",
                "—"
            )

            datum_quelle = result.get(
                "datum_quelle",
                "—"
            )

            datum_confidence = float(
                result.get(
                    "datum_confidence",
                    0
                )
            ) * 100

            beschreibung_quelle = result.get(
                "beschreibung_quelle",
                "—"
            )


            beschreibung_confidence = float(
                result.get(
                    "beschreibung_confidence",
                    0
                )
            ) * 100


            ml_info = result.get(
                "ml_status",
                {}
            )


            firma = (
                result.get(
                    "firma",
                    ""
                )
                or
                "—"
            )


            umlagefaehig_wert = result.get("umlagefaehig")
            if umlagefaehig_wert is None:
                umlagefaehig = "Prüfung erforderlich"
            else:
                umlagefaehig = (
                    "Prüfung erforderlich – AI-Vorschlag: Ja"
                    if umlagefaehig_wert is True
                    else "Prüfung erforderlich – AI-Vorschlag: Nein"
                )
            umlage_status = result.get("umlagespruefung", {}).get("status", "pruefen")
            warnungen = result.get("warnungen", [])
            warnungen_text = "\n".join(warnungen) if warnungen else "Keine zusätzlichen Hinweise."


            aktive_nummern = [
                str(
                    w["nummer"]
                )
                for w in wohnungen
                if wohnung_vars[
                    w["id"]
                ].get()
            ]


            wohnungs_text = (
                ", ".join(
                    aktive_nummern
                )
                if aktive_nummern
                else
                "keine"
            )


            ml_aktiv = (
                "aktiv"
                if ml_info.get(
                    "aktiv"
                )
                else
                "noch nicht trainiert"
            )


            beschreibung_ml_aktiv = (
                "aktiv"
                if ml_info.get(
                    "beschreibung_aktiv"
                )
                else
                "noch nicht trainiert"
            )


            trained_at = (
                ml_info.get(
                    "trained_at"
                )
                or
                "—"
            )


            beschreibung_trained_at = (
                ml_info.get(
                    "beschreibung_trained_at"
                )
                or
                "—"
            )


            # ===== AI SUMMARY =====

            ai_summary_label.config(

                text=(

                    f"Datum: {datum}\n"

                    f"Quelle Datum: {datum_quelle}\n"

                    f"Konfidenz Datum-ML: {datum_confidence:.1f}%\n"

                    f"Firma: {firma}\n"

                    f"Kostenart: {kostenart}\n"

                    f"Umlagefähig: {umlagefaehig}\n"

                    f"Umlageschlüssel-Vorschlag: {umlage_vorschlag or 'keiner'}\n"
                    f"Umlage-Status: {umlage_status}\n"
                    f"Warnungen: {warnungen_text}\n"

                    f"Betroffene Wohnungen: {wohnungs_text}\n"

                    f"Konfidenz Kostenart: {confidence:.0f}%\n"

                    f"Entscheidungsquelle Kostenart: "
                    f"{entscheidungsquelle}\n\n"

                    f"Beschreibung: {beschreibung}\n"

                    f"Quelle Beschreibung: "
                    f"{beschreibung_quelle}\n"

                    f"Konfidenz Beschreibung: "
                    f"{beschreibung_confidence:.0f}%\n\n"

                    f"Kostenart-Modell: {ml_aktiv}\n"

                    f"Beschreibung-Modell: "
                    f"{beschreibung_ml_aktiv}\n"

                    f"Trainingsbeispiele: "
                    f"{ml_info.get('beispiele', lerndaten_anzahl())}\n"

                    f"Trainierte Klassen: "
                    f"{ml_info.get('klassen', 0)}\n"

                    f"Letztes Kostenart-Training: "
                    f"{trained_at}\n"

                    f"Letztes Beschreibung-Training: "
                    f"{beschreibung_trained_at}\n\n"

                    f"Begründung: {begruendung}\n\n"

                    "AI-Vorschlag – bestätigte Korrekturen "
                    "trainieren die eigenen ML-Modelle automatisch neu."
                )
            )


            ai_vorschau_aktualisieren()


            show_status(
                "AI-Rechnungsanalyse abgeschlossen."
            )


        except Exception as e:

            ai_summary_label.config(
                text=(
                    f"AI-Analyse fehlgeschlagen: {e}"
                )
            )

            ai_distribution_label.config(
                text=""
            )

            show_status(
                "AI-Analyse fehlgeschlagen."
            )
        
    # ===== AI RECHNUNG ANALYSIEREN =====
    app_button(
        content,
        "🤖 AI Rechnung analysieren",
        ai_rechnung_analysieren,
        width=30
    ).grid(
        row=row,
        column=0,
        columnspan=2,
        pady=(5, 5)
    )
    row += 1


    # ===== ML ERKLÄREN =====
    app_button(
        content,
        "🧠 ML erklären",
        ml_erklaeren,
        width=30
    ).grid(
        row=row,
        column=0,
        columnspan=2,
        pady=(5, 10)
    )
    row += 1

    # ===== SPEICHERN =====
    def speichern():
        umlageschluessel = umlage_box.get()
        betroffene_wohnungen = [
            wohnung_id for wohnung_id, var in wohnung_vars.items() if var.get()
        ]
        if not umlage_bestaetigt.get():
            show_status("Prüfung erforderlich: Bitte Umlagefähigkeit und Verteilung ausdrücklich bestätigen.")
            return
        if not umlageschluessel:
            show_status("Bitte einen Umlageschlüssel ausdrücklich auswählen.")
            return
        if umlageschluessel != "Nicht umlagefähig" and not betroffene_wohnungen:
            show_status("Bitte mindestens eine Wohnung für die Verteilung auswählen.")
            return

        try:
            betrag = float(betrag_entry.get().replace(",", "."))
        except ValueError:
            show_status("Ungültiger Betrag.")
            return

        datum = f"{jahr_box.get()}-{monat_box.get()}-{tag_box.get()}"
        if umlageschluessel == "Nicht umlagefähig":
            betroffene_wohnungen = []

        eintrag = {
            "gebaeude_id": gebaeude["id"],
            "datum": datum,
            "typ": typ_box.get(),
            "kostenart": kostenart_box.get(),
            "umlageschluessel": umlageschluessel,
            "betrag": betrag,
            "beschreibung": beschreibung_entry.get().strip(),
            "beleg_pfad": beleg_speichern(beleg_entry.get().strip()),
            "betroffene_wohnungen": betroffene_wohnungen
        }

        # Benutzerkorrekturen nach AI-Analyse als bestätigtes Lernbeispiel speichern.
        if ai_state["rechnung_text"]:
            if umlage_box.get() == "Nicht umlagefähig":
                verteilung = "NICHT_UMLAGEFAEHIG"
                umlagefaehig = False
            elif len(betroffene_wohnungen) == len(wohnungen):
                verteilung = "ALLE"
                umlagefaehig = True
            else:
                verteilung = "AUSWAHL"
                umlagefaehig = True

            lern_result = lernbeispiel_speichern(
                ai_state["rechnung_text"],
                {
                    "kostenart": kostenart_box.get(),
                    "umlageschluessel": umlage_box.get(),
                    "umlagefaehig": umlagefaehig,
                    "verteilung": verteilung,
                    "beschreibung": beschreibung_entry.get().strip(),
                    "datum": datum
                }
            )
        else:
            lern_result = None

        add_kontobewegung(eintrag)
        if lern_result and lern_result.get("training", {}).get("trainiert"):
            show_status(f"Kontobewegung gespeichert. ML neu trainiert ({lern_result.get('beispiele', 0)} Beispiele).")
        elif lern_result:
            show_status(f"Kontobewegung gespeichert. Trainingsbeispiel gespeichert ({lern_result.get('beispiele', 0)} insgesamt).")
        else:
            show_status("Kontobewegung gespeichert.")
        gebaeude_detail_fenster(gebaeude)

    app_button(content, "Speichern", speichern, width=25).grid(row=row, column=0, columnspan=2, pady=20)

    app_button(main_frame, "Zurück", lambda: gebaeude_detail_fenster(gebaeude), width=25).pack(pady=5)

###############################################################################################
#NEBENKOSTEN BERECHNEN
###############################################################################################
def nebenkosten_berechnen(gebaeude):
    clear_main_frame()
    show_header("Nebenkosten")

    wohnungen = get_wohnungen_by_gebaeude(gebaeude["id"])
    bewegungen = get_kontobewegungen_by_gebaeude(gebaeude["id"])

    if not wohnungen:
        tk.Label(main_frame, text="Keine Wohnungen vorhanden.", bg=BG_COLOR, fg=TEXT_DARK).pack(pady=10)
        app_button(main_frame, "← Zurück", lambda: gebaeude_detail_fenster(gebaeude), width=25).pack(pady=20)
        return

    if not bewegungen:
        tk.Label(main_frame, text="Keine Kontobewegungen vorhanden.", bg=BG_COLOR, fg=TEXT_DARK).pack(pady=10)
        app_button(main_frame, "← Zurück", lambda: gebaeude_detail_fenster(gebaeude), width=25).pack(pady=20)
        return

    # Gesamtsummen berechnen
    gesamt_flaeche = sum(float(str(w["flaeche"]).replace(",", ".")) for w in wohnungen)
    gesamt_mea = sum(float(str(w["miteigentumsanteile"]).replace(",", ".")) for w in wohnungen)

    # Ergebnis vorbereiten: Wohnung -> Kostenart -> Betrag
    ergebnis = {w["nummer"]: {} for w in wohnungen}
    gesamt_kosten = 0

    for b in bewegungen:
        if b["typ"] != "Ausgabe":
            continue

        betrag = float(str(b["betrag"]).replace(",", "."))
        gesamt_kosten += betrag

        umlage = b["umlageschluessel"]
        kostenart = b["kostenart"]

        betroffene_ids = b.get("betroffene_wohnungen", [])
        aktive_wohnungen = [w for w in wohnungen if not betroffene_ids or w["id"] in betroffene_ids]

        if not aktive_wohnungen:
            continue

        aktive_flaeche = sum(float(str(w["flaeche"]).replace(",", ".")) for w in aktive_wohnungen)
        aktive_mea = sum(float(str(w["miteigentumsanteile"]).replace(",", ".")) for w in aktive_wohnungen)

        for w in aktive_wohnungen:
            if umlage == "Wohnfläche":
                anteil = float(str(w["flaeche"]).replace(",", ".")) / aktive_flaeche
                kosten = betrag * anteil

            elif umlage == "Miteigentumsanteile":
                anteil = float(str(w["miteigentumsanteile"]).replace(",", ".")) / aktive_mea
                kosten = betrag * anteil

            elif umlage == "Wohneinheiten":
                kosten = betrag / len(aktive_wohnungen)

            elif umlage == "Nicht umlagefähig":
                kosten = 0

            else:
                # Standard: unbekannte Umlageschlüssel nach Wohnfläche verteilen
                anteil = float(str(w["flaeche"]).replace(",", ".")) / aktive_flaeche
                kosten = betrag * anteil

            if kostenart not in ergebnis[w["nummer"]]:
                ergebnis[w["nummer"]][kostenart] = 0

            ergebnis[w["nummer"]][kostenart] += kosten

    # Gesamt pro Wohnung berechnen
    gesamt_pro_wohnung = {}

    for nummer, kostenarten in ergebnis.items():
        gesamt_pro_wohnung[nummer] = sum(kostenarten.values())

    # PDF-Zeilen vorbereiten
    pdf_zeilen = []
    pdf_zeilen.append(f"Gebäude {gebaeude['id']}")
    pdf_zeilen.append(f"Gesamtkosten: {gesamt_kosten:.2f} EUR")
    pdf_zeilen.append("")

    # UI: Gesamtkosten
    tk.Label(
        main_frame,
        text=f"Gesamtkosten: {gesamt_kosten:.2f} €",
        font=("Arial", 14, "bold"),
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack(pady=10)

    # UI: Kosten pro Wohnung mit Kostenarten
    for nummer, kostenarten in ergebnis.items():
        pdf_zeilen.append(f"Wohnung {nummer}")

        frame = tk.Frame(main_frame, bg="white", bd=1, relief="solid")
        frame.pack(padx=20, pady=8, fill="x")

        tk.Label(
            frame,
            text=f"Wohnung {nummer}",
            font=("Arial", 12, "bold"),
            bg="white",
            fg=TEXT_DARK
        ).pack(anchor="w", padx=10, pady=5)

        for art, betrag in kostenarten.items():
            pdf_zeilen.append(f"  {art}: {betrag:.2f} EUR")

            tk.Label(
                frame,
                text=f"{art}: {betrag:.2f} €",
                bg="white",
                fg="gray"
            ).pack(anchor="w", padx=20)

        pdf_zeilen.append(f"  Gesamt: {gesamt_pro_wohnung[nummer]:.2f} EUR")
        pdf_zeilen.append("")

        tk.Label(
            frame,
            text=f"Gesamt: {gesamt_pro_wohnung[nummer]:.2f} €",
            font=("Arial", 11, "bold"),
            bg="white",
            fg=TEXT_DARK
        ).pack(anchor="w", padx=10, pady=(5, 8))

    def pdf_speichern():
        dateipfad = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Datei", "*.pdf")],
            title="Nebenkosten PDF speichern"
        )

        if not dateipfad:
            return

        nebenkosten_pdf_erstellen(
            dateipfad,
            gebaeude,
            gesamt_kosten,
            ergebnis
        )

        show_status("PDF wurde erstellt.")
        os.startfile(dateipfad)

    app_button(
        main_frame,
        "PDF erstellen",
        pdf_speichern,
        width=25
    ).pack(pady=10)

    app_button(
        main_frame,
        "← Zurück",
        lambda: gebaeude_detail_fenster(gebaeude),
        width=25
    ).pack(pady=20)
################################################################################################
# GEBÄUDELISTE + SUCHE
################################################################################################

def gebaeude_anzeigen_gui():
    clear_main_frame()
    show_header("Gebäudeübersicht")

    gebaeude_liste = load_gebaeude()

    tk.Label(
        main_frame,
        text="Suche nach Stadt / PLZ / Straße / Hausnummer:",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack()

    search_frame = tk.Frame(main_frame, bg=BG_COLOR)
    search_frame.pack(pady=5)

    search_entry = tk.Entry(search_frame, width=35)
    search_entry.pack(side="left", padx=5)

    result_frame = tk.Frame(main_frame, bg=BG_COLOR)
    result_frame.pack(fill="both", expand=True)

    def zeige_liste(liste_daten):
        for widget in result_frame.winfo_children():
            widget.destroy()

        if not liste_daten:
            tk.Label(
                result_frame,
                text="Keine Treffer",
                bg=BG_COLOR,
                fg=TEXT_DARK
            ).pack()
            return

        for g in liste_daten:
            adr = g["adresse"]

            button_text = (
                f"ID {g['id']} | "
                f"{adr['plz']} {adr['stadt']}, "
                f"{adr['strasse']} {adr['hausnummer']}"
            )

            app_button(
                result_frame,
                button_text,
                lambda geb=g: gebaeude_detail_fenster(geb),
                width=65
            ).pack(pady=4)

    def suchen():
        such = search_entry.get().lower().strip()

        if not such:
            zeige_liste(gebaeude_liste)
            return

        gefiltert = []

        for g in gebaeude_liste:
            adr = g["adresse"]
            suchtext = f"{adr['plz']} {adr['stadt']} {adr['strasse']} {adr['hausnummer']}".lower()

            if such in suchtext:
                gefiltert.append(g)

        zeige_liste(gefiltert)

    app_button(
        search_frame,
        "Suchen",
        suchen,
        width=15
    ).pack(side="left")

    zeige_liste(gebaeude_liste)

    app_button(
        main_frame,
        "Zurück",
        show_dashboard,
        width=25
    ).pack(pady=10)

################################################################################################
# DETAILFENSTER FÜR EIN GEBÄUDE
################################################################################################

def gebaeude_detail_fenster(gebaeude):
    clear_main_frame()
    show_header(f"Gebäude {gebaeude['id']}")

    adr = gebaeude["adresse"]

    info = (
        f"Adresse: {adr['plz']} {adr['stadt']}, {adr['strasse']} {adr['hausnummer']}\n"
        f"Fläche: {gebaeude['flaeche']}\n"
        f"MEA: {gebaeude['miteigentumsanteile']}\n"
        f"Energieausweis bis: {gebaeude['energieausweis_bis']}\n"
        f"Legionellenprüfung bis: {gebaeude['legionellenpruefung_bis']}"
    )

    tk.Label(
        main_frame,
        text=info,
        justify="center",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack(pady=10)
    # ===== BUTTON =====

    app_button(
        main_frame,
        "Wohnungen anzeigen",
        lambda: wohnungen_anzeigen(gebaeude)
    ).pack(pady=5)

    app_button(
        main_frame,
        "Wohnung hinzufügen",
        lambda: wohnung_hinzufuegen(gebaeude)
    ).pack(pady=5)

    app_button(
        main_frame,
        "Neue Meldung",
        lambda: neue_meldung(gebaeude)
    ).pack(pady=5)

    app_button(
        main_frame,
        "Meldungen anzeigen",
        lambda: meldungen_anzeigen(gebaeude)
    ).pack(pady=5)

    app_button(
        main_frame,
        "Kontobewegungen anzeigen",
        lambda: kontobewegungen_anzeigen(gebaeude)
    ).pack(pady=5)

    app_button(
        main_frame,
        "Kontobewegung hinzufügen",
        lambda: kontobewegung_hinzufuegen(gebaeude)
    ).pack(pady=5)

    app_button(
        main_frame,
        "Nebenkosten berechnen",
        lambda: nebenkosten_berechnen(gebaeude)
    ).pack(pady=5)


    app_button(
        main_frame,
        "Bearbeiten",
        lambda: gebaeude_bearbeiten(gebaeude)
    ).pack(pady=5)

    # ===== УДАЛЕНИЕ =====

    app_button(
        main_frame,
        "Gebäude löschen",
        lambda: gebaeude_loeschen(gebaeude),
        width=30
    ).pack(pady=10)

    # ===== НАЗАД =====

    app_button(
    main_frame,
    "Zurück",
    show_dashboard
).pack(pady=20)

################################################################################################
# WOHNUNGEN ANZEIGEN
################################################################################################

def wohnungen_anzeigen(gebaeude):
    clear_main_frame()
    show_header(f"Wohnungen Gebäude {gebaeude['id']}")

    wohnungen = get_wohnungen_by_gebaeude(gebaeude["id"])

    if not wohnungen:
        tk.Label(
            main_frame,
            text="Keine Wohnungen vorhanden.",
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=10)

        app_button(
            main_frame,
            "Zurück",
            lambda: gebaeude_detail_fenster(gebaeude),
            width=25
        ).pack(pady=20)

        return

    for w in wohnungen:
        text = (
            f"Wohnung: {w['nummer']}\n"
            f"Fläche: {w['flaeche']}\n"
            f"MEA: {w['miteigentumsanteile']}\n"
            "-----------------------------"
        )

        tk.Label(
            main_frame,
            text=text,
            justify="left",
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=5)

    app_button(
        main_frame,
        "Zurück",
        lambda: gebaeude_detail_fenster(gebaeude),
        width=25
    ).pack(pady=20)

################################################################################################
# WOHNUNG HINZUFÜGEN
################################################################################################

def wohnung_hinzufuegen(gebaeude):
    clear_main_frame()
    show_header("Wohnung hinzufügen")

    # Validierungsfunktion für Zahlenfelder registrieren
    vcmd = (root.register(only_numbers), "%P")

    content = tk.Frame(main_frame, bg=BG_COLOR)
    content.pack(pady=10)

    fields = {}

    adr = gebaeude["adresse"]
    gebaeude_adresse = f"{adr['plz']} {adr['stadt']}, {adr['strasse']} {adr['hausnummer']}"

    tk.Label(
        content,
        text="Wohnungsdaten",
        font=("Arial", 12, "bold"),
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=0, column=0, columnspan=2, pady=(10, 5))

    labels = [
        "Wohnungsnummer",
        "Fläche",
        "Miteigentumsanteile"
    ]

    row = 1

    for label in labels:
        tk.Label(
            content,
            text=label,
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).grid(row=row, column=0, padx=10, pady=5, sticky="e")

        if label in ["Fläche", "Miteigentumsanteile"]:
            entry = tk.Entry(
                content,
                width=40,
                validate="key",
                validatecommand=vcmd
            )
        else:
            entry = tk.Entry(content, width=40)

        entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        fields[label] = entry
        row += 1

    personen_fields = {}
    personen = ["Eigentümer", "Mieter"]

    for person in personen:
        tk.Label(
            content,
            text=person,
            font=("Arial", 12, "bold"),
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).grid(row=row, column=0, columnspan=2, pady=(15, 5))

        row += 1
        personen_fields[person] = {}

        for feld in ["Nachname", "Vorname", "Adresse", "Telefonnummer", "Email"]:
            tk.Label(
                content,
                text=feld,
                bg=BG_COLOR,
                fg=TEXT_DARK
            ).grid(row=row, column=0, padx=10, pady=4, sticky="e")

            entry = tk.Entry(content, width=40)
            entry.grid(row=row, column=1, padx=10, pady=4, sticky="w")

            personen_fields[person][feld] = entry
            row += 1

        def fill_adresse(p=person):
            personen_fields[p]["Adresse"].delete(0, tk.END)
            personen_fields[p]["Adresse"].insert(0, gebaeude_adresse)

        app_button(
            content,
            "Adresse wie Gebäude",
            fill_adresse,
            width=25
        ).grid(row=row, column=1, pady=4, sticky="w")

        row += 1

    def speichern():
        nummer = fields["Wohnungsnummer"].get().strip()
        flaeche = fields["Fläche"].get().strip()
        mea = fields["Miteigentumsanteile"].get().strip()

        eigentuemer = {
            "nachname": personen_fields["Eigentümer"]["Nachname"].get().strip(),
            "vorname": personen_fields["Eigentümer"]["Vorname"].get().strip(),
            "adresse": personen_fields["Eigentümer"]["Adresse"].get().strip(),
            "telefonnummer": personen_fields["Eigentümer"]["Telefonnummer"].get().strip(),
            "email": personen_fields["Eigentümer"]["Email"].get().strip()
        }

        mieter = {
            "nachname": personen_fields["Mieter"]["Nachname"].get().strip(),
            "vorname": personen_fields["Mieter"]["Vorname"].get().strip(),
            "adresse": personen_fields["Mieter"]["Adresse"].get().strip(),
            "telefonnummer": personen_fields["Mieter"]["Telefonnummer"].get().strip(),
            "email": personen_fields["Mieter"]["Email"].get().strip()
        }

        if not nummer:
            show_status("Wohnungsnummer fehlt.")
            return

        if not flaeche:
            show_status("Fläche fehlt.")
            return

        if not mea:
            show_status("Miteigentumsanteile fehlen.")
            return

        if not eigentuemer["nachname"] or not eigentuemer["vorname"]:
            show_status("Eigentümer Nachname und Vorname fehlen.")
            return

        wohnung = {
            "gebaeude_id": gebaeude["id"],
            "nummer": nummer,
            "flaeche": flaeche,
            "miteigentumsanteile": mea,
            "eigentuemer": eigentuemer,
            "mieter": mieter
        }

        neue_wohnung = add_wohnung(wohnung)

        show_status(
            f"Wohnung {neue_wohnung['nummer']} wurde zu Gebäude {gebaeude['id']} hinzugefügt."
        )

        gebaeude_detail_fenster(gebaeude)

    app_button(
        content,
        "Speichern",
        speichern,
        width=25
    ).grid(row=row, column=0, columnspan=2, pady=20)

    app_button(
        main_frame,
        "Zurück",
        lambda: gebaeude_detail_fenster(gebaeude),
        width=25
    ).pack(pady=5)

################################################################################################
# NEUES GEBÄUDE FORMULAR
################################################################################################

def neues_gebaeude_form():
    clear_main_frame()
    show_header("Neues Gebäude")

    # Validierungsfunktionen registrieren
    vcmd = (root.register(only_numbers), "%P")
    vcmd_plz = (root.register(only_plz), "%P")

    content = tk.Frame(main_frame, bg=BG_COLOR)
    content.pack(pady=10)

    fields = {}

    labels = [
        "PLZ",
        "Stadt",
        "Straße",
        "Hausnummer",
        "Miteigentumsanteile",
        "Fläche"
    ]

    row = 0

    for label in labels:
        tk.Label(
            content,
            text=label,
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

        if label == "PLZ":
            entry = tk.Entry(
                content,
                width=35,
                validate="key",
                validatecommand=vcmd_plz
            )
        elif label in ["Fläche", "Miteigentumsanteile"]:
            entry = tk.Entry(
                content,
                width=35,
                validate="key",
                validatecommand=vcmd
            )
        else:
            entry = tk.Entry(content, width=35)

        entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")
        fields[label] = entry
        row += 1

    tk.Label(
        content,
        text="Energieausweis bis",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    date_frame_e = tk.Frame(content, bg=BG_COLOR)
    date_frame_e.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    tag_e = ttk.Combobox(date_frame_e, values=[str(d).zfill(2) for d in range(1, 32)], width=5, state="readonly")
    monat_e = ttk.Combobox(date_frame_e, values=[str(m).zfill(2) for m in range(1, 13)], width=5, state="readonly")
    jahr_e = ttk.Combobox(date_frame_e, values=[str(y) for y in range(2024, 2035)], width=8, state="readonly")

    tag_e.set("01")
    monat_e.set("01")
    jahr_e.set("2026")

    tag_e.pack(side="left", padx=2)
    monat_e.pack(side="left", padx=2)
    jahr_e.pack(side="left", padx=2)

    row += 1

    tk.Label(
        content,
        text="Legionellenprüfung bis",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    date_frame_l = tk.Frame(content, bg=BG_COLOR)
    date_frame_l.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    tag_l = ttk.Combobox(date_frame_l, values=[str(d).zfill(2) for d in range(1, 32)], width=5, state="readonly")
    monat_l = ttk.Combobox(date_frame_l, values=[str(m).zfill(2) for m in range(1, 13)], width=5, state="readonly")
    jahr_l = ttk.Combobox(date_frame_l, values=[str(y) for y in range(2024, 2035)], width=8, state="readonly")

    tag_l.set("01")
    monat_l.set("01")
    jahr_l.set("2026")

    tag_l.pack(side="left", padx=2)
    monat_l.pack(side="left", padx=2)
    jahr_l.pack(side="left", padx=2)

    row += 1

    def speichern():
        plz = fields["PLZ"].get().strip()
        stadt = fields["Stadt"].get().strip()
        strasse = fields["Straße"].get().strip()
        hausnummer = fields["Hausnummer"].get().strip()

        if not plz or not stadt or not strasse or not hausnummer:
            show_status("Adresse fehlt.")
            return

        if len(plz) != 5:
            show_status("PLZ muss 5-stellig sein.")
            return

        gebaeude = {
            "plz": plz,
            "stadt": stadt,
            "strasse": strasse,
            "hausnummer": hausnummer,
            "flaeche": fields["Fläche"].get(),
            "mea": fields["Miteigentumsanteile"].get(),
            "energieausweis_bis": f"{jahr_e.get()}-{monat_e.get()}-{tag_e.get()}",
            "legionellenpruefung_bis": f"{jahr_l.get()}-{monat_l.get()}-{tag_l.get()}"
        }

        neues_gebaeude = add_gebaeude(gebaeude)

        show_status(f"Gebäude {neues_gebaeude['id']} erstellt.")
        show_dashboard()

    app_button(
        content,
        "Speichern",
        speichern,
        width=25
    ).grid(row=row, column=0, columnspan=2, pady=20)

    app_button(
        main_frame,
        "Zurück",
        show_dashboard,
        width=25
    ).pack(pady=5)

##############################################################################################
#GEBÄUDE BEARBEITEN
##############################################################################################
def gebaeude_bearbeiten(gebaeude):
    clear_main_frame()
    show_header("Gebäude bearbeiten")

    content = tk.Frame(main_frame, bg=BG_COLOR)
    content.pack(pady=10)

    fields = {}

    adr = gebaeude["adresse"]

    data_map = {
        "PLZ": adr["plz"],
        "Stadt": adr["stadt"],
        "Straße": adr["strasse"],
        "Hausnummer": adr["hausnummer"],
        "Fläche": gebaeude["flaeche"],
        "Miteigentumsanteile": gebaeude["miteigentumsanteile"]
    }

    row = 0

    for label, value in data_map.items():
        tk.Label(content, text=label, bg=BG_COLOR, fg=TEXT_DARK).grid(
            row=row, column=0, padx=10, pady=5, sticky="e"
        )

        entry = tk.Entry(content, width=35)
        entry.insert(0, str(value))
        entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")

        fields[label] = entry
        row += 1

    def speichern():
        data = {
            "plz": fields["PLZ"].get().strip(),
            "stadt": fields["Stadt"].get().strip(),
            "strasse": fields["Straße"].get().strip(),
            "hausnummer": fields["Hausnummer"].get().strip(),
            "flaeche": fields["Fläche"].get().strip(),
            "mea": fields["Miteigentumsanteile"].get().strip(),
            "energieausweis_bis": gebaeude["energieausweis_bis"],
            "legionellenpruefung_bis": gebaeude["legionellenpruefung_bis"]
        }

        update_gebaeude(gebaeude["id"], data)

        show_status("Gebäude aktualisiert")

        # Aktualisierte Gebäudedaten neu laden
        aktuelle_gebaeude_liste = load_gebaeude()

        for g in aktuelle_gebaeude_liste:
            if g["id"] == gebaeude["id"]:
                gebaeude_detail_fenster(g)
                return

        show_dashboard()

    buttons_frame = tk.Frame(main_frame, bg=BG_COLOR)
    buttons_frame.pack(pady=20)

    # КНОПКА СОХРАНИТЬ
    app_button(
        content,
        "Speichern",
        speichern,
        width=25
    ).grid(row=row, column=0, columnspan=2, pady=(20, 5))

    row += 1

    # КНОПКА НАЗАД ВНИЗУ
    app_button(
        content,
        "← Zurück",
        lambda: gebaeude_detail_fenster(gebaeude),
        width=25
    ).grid(row=row, column=0, columnspan=2, pady=(5, 20))



################################################################################################
# NEUE MELDUNG ERSTELLEN
################################################################################################

def neue_meldung(gebaeude):
    clear_main_frame()
    show_header("Neue Meldung")

    wohnungen = get_wohnungen_by_gebaeude(gebaeude["id"])

    tk.Label(
        main_frame,
        text="Bereich",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack()

    wohnung_values = ["Ganzes Haus"]

    for w in wohnungen:
        wohnung_values.append(f"{w['id']} - Wohnung {w['nummer']}")

    wohnung_box = ttk.Combobox(
        main_frame,
        values=wohnung_values,
        state="readonly",
        width=40
    )
    wohnung_box.set("Ganzes Haus")
    wohnung_box.pack(pady=5)

    tk.Label(
        main_frame,
        text="Kategorie",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack()

    kategorie_box = ttk.Combobox(
        main_frame,
        values=["Wasser", "Heizung", "Elektrik", "Aufzug", "Reinigung", "Sonstiges"],
        state="readonly",
        width=40
    )
    kategorie_box.set("Wasser")
    kategorie_box.pack(pady=5)

    tk.Label(
        main_frame,
        text="Beschreibung",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack()

    beschreibung = tk.Entry(main_frame, width=43)
    beschreibung.pack(pady=5)

    tk.Label(
        main_frame,
        text="Priorität",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack()

    prio_box = ttk.Combobox(
        main_frame,
        values=["niedrig", "mittel", "hoch"],
        state="readonly",
        width=40
    )
    prio_box.set("mittel")
    prio_box.pack(pady=5)

    def speichern():
        bereich = wohnung_box.get()

        if bereich == "Ganzes Haus":
            wohnung_id = None
        else:
            wohnung_id = int(bereich.split(" - ")[0])

        if not beschreibung.get().strip():
            show_status("Beschreibung fehlt.")
            return

        meldung = {
            "gebaeude_id": gebaeude["id"],
            "wohnung_id": wohnung_id,
            "kategorie": kategorie_box.get(),
            "beschreibung": beschreibung.get().strip(),
            "prioritaet": prio_box.get(),
            "status": "offen",
            "erstellt_am": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        add_meldung(meldung)
        show_status("Meldung erstellt.")
        gebaeude_detail_fenster(gebaeude)

    app_button(
        main_frame,
        "Speichern",
        speichern,
        width=25
    ).pack(pady=20)

    app_button(
        main_frame,
        "Zurück",
        lambda: gebaeude_detail_fenster(gebaeude),
        width=25
    ).pack(pady=5)

################################################################################################
# MELDUNGEN ANZEIGEN
################################################################################################

def meldungen_anzeigen(gebaeude):
    clear_main_frame()
    show_header("Meldungen")

    meldungen = get_meldungen_by_gebaeude(gebaeude["id"])

    if not meldungen:
        tk.Label(
            main_frame,
            text="Keine Meldungen vorhanden",
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=10)

        app_button(
            main_frame,
            "Zurück",
            lambda: gebaeude_detail_fenster(gebaeude),
            width=25
        ).pack(pady=20)

        return

    for m in meldungen:
        text = (
            f"ID: {m['id']} | "
            f"Wohnung: {m['wohnung_id'] if m['wohnung_id'] else 'Ganzes Haus'} | "
            f"{m['kategorie']} | "
            f"{m['status']} | "
            f"{m['erstellt_am']}"
        )

        tk.Label(
            main_frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=2)

    app_button(
        main_frame,
        "Zurück",
        lambda: gebaeude_detail_fenster(gebaeude),
        width=25
    ).pack(pady=20)


################################################################################################
# ANALYTICS
################################################################################################

def analytics_anzeigen():
    # Die Data-Science-Bibliotheken werden erst geladen, wenn der Benutzer
    # den Analytics-Bereich tatsächlich öffnet. So bleibt der normale
    # Programmstart unabhängig von Pandas, Matplotlib und scikit-learn.
    import pandas as pd
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from sklearn.ensemble import IsolationForest

    """
    Zeigt das Data-Science-Dashboard von HausFlow.

    Die Funktion liest die Kontobewegungen direkt aus SQLite, bereitet die
    Daten mit Pandas auf und erzeugt Kennzahlen sowie fünf Visualisierungen.
    Zusätzlich werden mögliche Duplikate und auffällige Rechnungsbeträge
    markiert. Alle Analysen werden beim Wechsel des Jahres neu berechnet.
    """

    clear_main_frame()
    show_header("📊 Analytics")

    # =====================================================================
    # 1. DATEN AUS SQLITE LADEN
    # =====================================================================
    # Die Analytics-Seite arbeitet direkt mit der aktuellen HausFlow-Datenbank.
    # Dadurch werden neue Kontobewegungen automatisch in den Auswertungen berücksichtigt.
    db_path = os.path.join(BASE_DIR, "data", "hausflow.db")

    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(
                "SELECT * FROM kontobewegungen",
                conn
            )
    except Exception as e:
        show_status(f"Analytics konnte nicht geladen werden: {e}")
        return

    if df.empty:
        tk.Label(
            main_frame,
            text="Keine Daten für die Analyse vorhanden.",
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=20)

        app_button(
            main_frame,
            "Zurück",
            show_dashboard,
            width=25
        ).pack(pady=20)
        return

    # =====================================================================
    # 2. DATEN VORBEREITEN
    # =====================================================================
    # Ungültige Datumswerte werden zu NaT. Beträge werden sicher in Zahlen
    # umgewandelt. So kann ein einzelner fehlerhafter Datensatz den Dashboard
    # nicht komplett stoppen.
    df["datum"] = pd.to_datetime(
        df["datum"],
        errors="coerce"
    )

    df["betrag"] = pd.to_numeric(
        df["betrag"],
        errors="coerce"
    )

    # Für die Finanzanalyse interessieren hier nur Ausgaben mit gültigem Datum
    # und gültigem Betrag.
    ausgaben = df[
        (df["typ"] == "Ausgabe")
        & df["datum"].notna()
        & df["betrag"].notna()
    ].copy()

    if ausgaben.empty:
        tk.Label(
            main_frame,
            text="Keine gültigen Ausgaben für die Analyse vorhanden.",
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=20)

        app_button(
            main_frame,
            "Zurück",
            show_dashboard,
            width=25
        ).pack(pady=20)
        return

    # Vorhandene Jahre aus den echten Daten bestimmen.
    # Dadurch ist der Dashboard nicht fest auf 2026 programmiert.
    jahre = sorted(
        ausgaben["datum"].dt.year.dropna().astype(int).unique(),
        reverse=True
    )

    # Standardmäßig das neueste Jahr anzeigen.
    aktuelles_jahr = 2026 if 2026 in jahre else jahre[0]

    # =====================================================================
    # 3. JAHR AUSWÄHLEN
    # =====================================================================
    filter_frame = tk.Frame(
        main_frame,
        bg=BG_COLOR
    )
    filter_frame.pack(pady=(5, 10))

    tk.Label(
        filter_frame,
        text="Analysejahr:",
        font=("Arial", 11, "bold"),
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack(side="left", padx=(0, 8))

    jahr_var = tk.StringVar(
        value=str(aktuelles_jahr)
    )

    jahr_box = ttk.Combobox(
        filter_frame,
        textvariable=jahr_var,
        values=[str(jahr) for jahr in jahre],
        state="readonly",
        width=10
    )
    jahr_box.pack(side="left")

    # Dieser Frame enthält alle Kennzahlen und Diagramme.
    # Beim Wechsel des Jahres wird nur dieser Bereich neu aufgebaut.
    dashboard_frame = tk.Frame(
        main_frame,
        bg=BG_COLOR
    )
    dashboard_frame.pack(
        fill="both",
        expand=True
    )

    def dashboard_aktualisieren(event=None):
        """Berechnet Kennzahlen neu und zeichnet alle Diagramme."""

        # Alte Dashboard-Elemente entfernen, damit beim Jahreswechsel
        # keine Diagramme übereinander liegen.
        for widget in dashboard_frame.winfo_children():
            widget.destroy()

        # Das im Auswahlfeld gewählte Jahr wird als Ganzzahl benötigt,
        # damit es mit dem Jahr aus der Datumsspalte verglichen werden kann.
        jahr = int(jahr_var.get())

        # Für alle folgenden Berechnungen wird nur das ausgewählte Jahr verwendet.
        ausgaben_jahr = ausgaben[
            ausgaben["datum"].dt.year == jahr
        ].copy()

        if ausgaben_jahr.empty:
            tk.Label(
                dashboard_frame,
                text=f"Für {jahr} sind keine Ausgaben vorhanden.",
                bg=BG_COLOR,
                fg=TEXT_DARK
            ).pack(pady=20)
            return

        # =================================================================
        # 4. KPI-KENNZAHLEN
        # =================================================================
        gesamt = float(
            ausgaben_jahr["betrag"].sum()
        )

        anzahl = len(
            ausgaben_jahr
        )

        durchschnitt = float(
            ausgaben_jahr["betrag"].mean()
        )

        # -------------------------------------------------------------
        # Mögliche Duplikate
        # -------------------------------------------------------------
        # Gleicher Tag + Gebäude + Betrag + Beschreibung ist ein Hinweis
        # auf einen möglichen doppelten Datensatz. Es ist aber kein Beweis.
        duplikat_spalten = [
            "datum",
            "gebaeude_id",
            "betrag",
            "beschreibung"
        ]

        duplikat_mask = ausgaben_jahr.duplicated(
            subset=duplikat_spalten,
            keep=False
        )

        duplikate = int(
            duplikat_mask.sum()
        )

        # -------------------------------------------------------------
        # Anomalien mit Isolation Forest
        # -------------------------------------------------------------
        # Das einfache Modell verwendet bewusst nur den Rechnungsbetrag.
        # Es markiert ungefähr 5 % der Werte als ungewöhnlich. Die Treffer
        # sind Prüfhinweise und dürfen nicht automatisch als Fehler gelten.
        ausgaben_jahr["anomalie"] = False

        if len(ausgaben_jahr) >= 10:
            modell = IsolationForest(
                contamination=0.05,
                random_state=42
            )

            vorhersage = modell.fit_predict(
                ausgaben_jahr[["betrag"]]
            )

            ausgaben_jahr["anomalie"] = (
                vorhersage == -1
            )

        anomalien = int(
            ausgaben_jahr["anomalie"].sum()
        )

        tk.Label(
            dashboard_frame,
            text=f"Übersicht {jahr}",
            font=("Arial", 14, "bold"),
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=(10, 12))

        cards = tk.Frame(
            dashboard_frame,
            bg=BG_COLOR
        )
        cards.pack(pady=5)

        kennzahlen = [
            ("Gesamtausgaben", f"{gesamt:,.2f} €"),
            ("Rechnungen", str(anzahl)),
            ("Ø Betrag", f"{durchschnitt:,.2f} €"),
            ("Anomalien", str(anomalien)),
            ("mögl. Duplikate", str(duplikate))
        ]

        # Fünf Karten in zwei Zeilen, damit sie auch in einem 700px-Fenster
        # gut lesbar bleiben.
        for index, (titel, wert) in enumerate(kennzahlen):
            row = index // 3
            column = index % 3

            card = tk.Frame(
                cards,
                bg="#F2FBFA",
                width=190,
                height=88,
                bd=1,
                relief="solid"
            )
            card.grid(
                row=row,
                column=column,
                padx=5,
                pady=5
            )
            card.grid_propagate(False)

            tk.Label(
                card,
                text=titel,
                bg="#F2FBFA",
                fg="gray"
            ).pack(pady=(12, 4))

            tk.Label(
                card,
                text=wert,
                font=("Arial", 12, "bold"),
                bg="#F2FBFA",
                fg=TEXT_DARK
            ).pack()

        # =================================================================
        # 5. DIAGRAMM 1 – KOSTEN NACH KOSTENART
        # =================================================================
        tk.Label(
            dashboard_frame,
            text="Kosten nach Kostenart",
            font=("Arial", 14, "bold"),
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=(25, 5))

        # Die Beträge werden je Kostenart addiert. Für das horizontale
        # Balkendiagramm wird aufsteigend sortiert, damit die größte Kategorie
        # oben bzw. am Ende der Achse gut erkennbar ist.
        kostenarten = (
            ausgaben_jahr
            .groupby("kostenart")["betrag"]
            .sum()
            .sort_values(ascending=True)
        )

        fig1 = Figure(
            figsize=(6.2, 4.1),
            dpi=100
        )
        ax1 = fig1.add_subplot(111)

        ax1.barh(
            kostenarten.index,
            kostenarten.values,
            color=BRAND_COLOR
        )

        ax1.set_xlabel("Euro")
        ax1.grid(
            axis="x",
            alpha=0.2
        )
        fig1.tight_layout()

        chart1 = FigureCanvasTkAgg(
            fig1,
            master=dashboard_frame
        )
        chart1.draw()
        chart1.get_tk_widget().pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # =================================================================
        # 6. DIAGRAMM 2 – MONATLICHE KOSTENENTWICKLUNG
        # =================================================================
        tk.Label(
            dashboard_frame,
            text=f"Monatliche Ausgaben {jahr}",
            font=("Arial", 14, "bold"),
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=(25, 5))

        # Gruppierung nach Kalendermonat. Es werden nur Monate dargestellt,
        # für die tatsächlich Buchungen existieren. Fehlende Monate werden
        # bewusst nicht automatisch als 0 Euro interpretiert.
        monatliche_kosten = (
            ausgaben_jahr
            .groupby(ausgaben_jahr["datum"].dt.month)["betrag"]
            .sum()
            .sort_index()
        )

        monatsnamen = {
            1: "Jan",
            2: "Feb",
            3: "Mär",
            4: "Apr",
            5: "Mai",
            6: "Jun",
            7: "Jul",
            8: "Aug",
            9: "Sep",
            10: "Okt",
            11: "Nov",
            12: "Dez"
        }

        labels = [
            monatsnamen[int(monat)]
            for monat in monatliche_kosten.index
        ]

        fig2 = Figure(
            figsize=(6.2, 3.3),
            dpi=100
        )
        ax2 = fig2.add_subplot(111)

        ax2.plot(
            labels,
            monatliche_kosten.values,
            marker="o",
            color=BRAND_COLOR
        )

        ax2.set_ylabel("Euro")
        ax2.grid(alpha=0.2)
        fig2.tight_layout()

        chart2 = FigureCanvasTkAgg(
            fig2,
            master=dashboard_frame
        )
        chart2.draw()
        chart2.get_tk_widget().pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # =================================================================
        # 7. DIAGRAMM 3 – ANTEIL DER KOSTENARTEN
        # =================================================================
        tk.Label(
            dashboard_frame,
            text="Anteil der Kostenarten",
            font=("Arial", 14, "bold"),
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=(25, 5))

        # Ein Donut-Diagramm mit allen kleinen Kategorien wäre schwer lesbar.
        # Deshalb werden die sechs größten Kostenarten einzeln dargestellt.
        # Alle übrigen Kategorien werden unter "Weitere" zusammengefasst.
        kostenarten_absteigend = kostenarten.sort_values(
            ascending=False
        )

        if len(kostenarten_absteigend) > 6:
            donut_daten = kostenarten_absteigend.iloc[:6].copy()
            weitere_summe = kostenarten_absteigend.iloc[6:].sum()
            donut_daten.loc["Weitere"] = weitere_summe
        else:
            donut_daten = kostenarten_absteigend.copy()

        fig3 = Figure(
            figsize=(6.2, 4.0),
            dpi=100
        )
        ax3 = fig3.add_subplot(111)

        ax3.pie(
            donut_daten.values,
            labels=donut_daten.index,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.78,
            wedgeprops={
                "width": 0.42,
                "edgecolor": "white"
            },
            textprops={
                "fontsize": 8
            }
        )

        ax3.axis("equal")
        fig3.tight_layout()

        chart3 = FigureCanvasTkAgg(
            fig3,
            master=dashboard_frame
        )
        chart3.draw()
        chart3.get_tk_widget().pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # =================================================================
        # 8. DIAGRAMM 4 – VERTEILUNG DER RECHNUNGSBETRÄGE
        # =================================================================
        tk.Label(
            dashboard_frame,
            text="Verteilung der Rechnungsbeträge",
            font=("Arial", 14, "bold"),
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=(25, 5))

        fig4 = Figure(
            figsize=(6.2, 2.5),
            dpi=100
        )
        ax4 = fig4.add_subplot(111)

        # Der Boxplot zeigt Median, Streuung und mögliche Extremwerte.
        # Er ist besonders hilfreich, weil einzelne sehr große Rechnungen
        # in HausFlow den Durchschnitt deutlich beeinflussen können.
        ax4.boxplot(
            ausgaben_jahr["betrag"].dropna(),
            vert=False
        )

        ax4.set_xlabel("Euro")
        ax4.set_yticks([])
        ax4.grid(
            axis="x",
            alpha=0.2
        )
        fig4.tight_layout()

        chart4 = FigureCanvasTkAgg(
            fig4,
            master=dashboard_frame
        )
        chart4.draw()
        chart4.get_tk_widget().pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # =================================================================
        # 9. DIAGRAMM 5 – ANOMALIEN-VISUALISIERUNG
        # =================================================================
        tk.Label(
            dashboard_frame,
            text="Anomalieerkennung mit Isolation Forest",
            font=("Arial", 14, "bold"),
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=(25, 5))

        # Für die Darstellung sortieren wir die Rechnungen chronologisch.
        # Die x-Achse ist nur die laufende Position der Rechnung im Jahr.
        anomalie_plot = ausgaben_jahr.sort_values(
            "datum"
        ).reset_index(drop=True)

        # Für die Visualisierung werden normale und vom Modell markierte
        # Rechnungen getrennt, damit beide Gruppen unterschiedlich dargestellt
        # und direkt miteinander verglichen werden können.
        normal = anomalie_plot[
            ~anomalie_plot["anomalie"]
        ]

        auffaellig = anomalie_plot[
            anomalie_plot["anomalie"]
        ]

        fig5 = Figure(
            figsize=(6.2, 3.4),
            dpi=100
        )
        ax5 = fig5.add_subplot(111)

        ax5.scatter(
            normal.index,
            normal["betrag"],
            s=24,
            alpha=0.65,
            label="Normal"
        )

        if not auffaellig.empty:
            ax5.scatter(
                auffaellig.index,
                auffaellig["betrag"],
                s=55,
                marker="x",
                linewidths=2,
                label="Anomalie"
            )

        ax5.set_xlabel("Rechnungen im Zeitverlauf")
        ax5.set_ylabel("Betrag in Euro")
        ax5.grid(alpha=0.2)
        ax5.legend()
        fig5.tight_layout()

        chart5 = FigureCanvasTkAgg(
            fig5,
            master=dashboard_frame
        )
        chart5.draw()
        chart5.get_tk_widget().pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # =================================================================
        # 10. DATENQUALITÄT – ERKLÄRUNG
        # =================================================================
        tk.Label(
            dashboard_frame,
            text="Datenqualität",
            font=("Arial", 14, "bold"),
            bg=BG_COLOR,
            fg=TEXT_DARK
        ).pack(pady=(25, 5))

        quality_card = tk.Frame(
            dashboard_frame,
            bg="#F2FBFA",
            bd=1,
            relief="solid"
        )
        quality_card.pack(
            padx=40,
            pady=5,
            fill="x"
        )

        tk.Label(
            quality_card,
            text=(
                f"Isolation Forest erkennt {anomalien} mögliche Anomalien.\n"
                f"Die Duplikatprüfung markiert {duplikate} Datensätze als mögliche Duplikate.\n\n"
                "Die Anomalieerkennung verwendet aktuell nur den Rechnungsbetrag. "
                "Die Ergebnisse sind deshalb Prüfhinweise und nicht automatisch Fehler."
            ),
            bg="#F2FBFA",
            fg=TEXT_DARK,
            justify="left",
            wraplength=560
        ).pack(
            anchor="w",
            padx=15,
            pady=15
        )

    # Bei einer neuen Jahresauswahl den kompletten Dashboard neu berechnen.
    jahr_box.bind(
        "<<ComboboxSelected>>",
        dashboard_aktualisieren
    )

    # Dashboard beim Öffnen sofort anzeigen.
    dashboard_aktualisieren()

    # Zurück zur normalen HausFlow-Startseite.
    app_button(
        main_frame,
        "Zurück",
        show_dashboard,
        width=25
    ).pack(pady=30)


################################################################################################
# HAUPTFENSTER
################################################################################################

# Tabellen initialisieren
init_gebaeude_table()
init_wohnungen_table()
init_meldungen_table()
init_konto_table()

# Eigene Windows-App-ID setzen,
# damit in der Taskleiste das HausFlow-Icon angezeigt wird.
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "HausFlow.App"
    )
except Exception:
    pass

# Hauptfenster erstellen
root = tk.Tk()
root.title("HausFlow")
root.configure(bg=BG_COLOR)
center_window(root, 700, 800)

# Icon für das Hauptfenster setzen
set_window_icon(root)

# Logo laden
logo_path = os.path.join(BASE_DIR, "assets", "images", "logo.png")
logo = PhotoImage(file=logo_path)
logo = logo.subsample(2, 2)

# Referenz speichern
root.logo = logo

# Gebäude-Bild laden
building_path = os.path.join(BASE_DIR, "assets", "images", "building.png")
building_img = PhotoImage(file=building_path)
building_img = building_img.subsample(4, 4)

# Referenz speichern
root.building_img = building_img
# Hauptbereich für alle Screens
# Scrollbarer Hauptbereich
container = tk.Frame(root)
container.pack(fill="both", expand=True)

canvas = tk.Canvas(container, bg=BG_COLOR, highlightthickness=0)
scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)

scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")
    )
)

#Mitte
canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def resize_frame(event):
    canvas.itemconfig(canvas_window, width=event.width)

canvas.bind("<Configure>", resize_frame)

canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# ЭТО ВАЖНО 👇
main_frame = scrollable_frame

#Maus scroll
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

canvas.bind_all("<MouseWheel>", _on_mousewheel)


# Statusmeldung
status_var = tk.StringVar()
status_var.set("Bereit.")

status_label = tk.Label(
    root,
    textvariable=status_var,
    bg=BG_COLOR,
    fg=TEXT_DARK,
    font=("Arial", 10)
)
status_label.pack(pady=10)

# Startscreen anzeigen
show_dashboard()



################################################################################################
# MAINLOOP BEREICH
################################################################################################

def start_gui():
    # GUI starten
    root.mainloop()


if __name__ == "__main__":
    start_gui()
