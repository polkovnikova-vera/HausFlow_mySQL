################################################################################################
# HAUSFLOW GUI
################################################################################################

import tkinter as tk
import sys
import os
import shutil

from tkinter import ttk
from tkinter import filedialog
from datetime import datetime
from tkinter import PhotoImage
from tkinter import filedialog

# für PDF
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

################################################################################################
# PFAD-KONFIGURATION
################################################################################################

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    # Fenster-Icon setzen
    icon_path = os.path.join(BASE_DIR, "assets", "icons", "hausflow.ico")
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
    gebaeude_anzeigen_gui()

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

    tk.Label(
        content,
        text="Datum",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    date_frame = tk.Frame(content, bg=BG_COLOR)
    date_frame.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    tag_box = ttk.Combobox(
        date_frame,
        values=[str(d).zfill(2) for d in range(1, 32)],
        width=5,
        state="readonly"
    )
    monat_box = ttk.Combobox(
        date_frame,
        values=[str(m).zfill(2) for m in range(1, 13)],
        width=5,
        state="readonly"
    )
    jahr_box = ttk.Combobox(
        date_frame,
        values=[str(y) for y in range(2024, 2035)],
        width=8,
        state="readonly"
    )

    tag_box.set("01")
    monat_box.set("01")
    jahr_box.set("2026")

    tag_box.pack(side="left", padx=2)
    monat_box.pack(side="left", padx=2)
    jahr_box.pack(side="left", padx=2)

    row += 1

    tk.Label(
        content,
        text="Typ",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    typ_box = ttk.Combobox(
        content,
        values=["Einnahme", "Ausgabe"],
        state="readonly",
        width=37
    )
    typ_box.set("Ausgabe")
    typ_box.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    row += 1

    tk.Label(
        content,
        text="Kostenart",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    kostenart_box = ttk.Combobox(
        content,
        values=list(kostenarten_info.keys()),
        state="readonly",
        width=37
    )
    kostenart_box.set("Grundsteuer")
    kostenart_box.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    row += 1

    info_label = tk.Label(
        content,
        text=kostenarten_info["Grundsteuer"],
        wraplength=330,
        fg="gray",
        bg=BG_COLOR,
        justify="left"
    )
    info_label.grid(row=row, column=1, padx=10, pady=2, sticky="w")

    def kostenart_info_anzeigen(event):
        kostenart = kostenart_box.get()
        info_label.config(text=kostenarten_info.get(kostenart, ""))

    kostenart_box.bind("<<ComboboxSelected>>", kostenart_info_anzeigen)

    row += 1

    tk.Label(
        content,
        text="Umlageschlüssel",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    umlage_box = ttk.Combobox(
        content,
        values=[
            "Wohnfläche",
            "Miteigentumsanteile",
            "Personenanzahl",
            "Verbrauch",
            "Wohneinheiten",
            "Nicht umlagefähig"
        ],
        state="readonly",
        width=37
    )
    umlage_box.set("Wohnfläche")
    umlage_box.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    row += 1

    tk.Label(
        content,
        text="Betrag (€)",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    betrag_entry = tk.Entry(
        content,
        width=40,
        validate="key",
        validatecommand=vcmd
    )
    betrag_entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    row += 1

    tk.Label(
        content,
        text="Beschreibung",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    beschreibung_entry = tk.Entry(content, width=40)
    beschreibung_entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    row += 1

    tk.Label(
        content,
        text="Beleg",
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).grid(row=row, column=0, padx=10, pady=6, sticky="e")

    beleg_frame = tk.Frame(content, bg=BG_COLOR)
    beleg_frame.grid(row=row, column=1, padx=10, pady=6, sticky="w")

    beleg_entry = tk.Entry(beleg_frame, width=28)
    beleg_entry.pack(side="left", padx=2)

    def beleg_auswaehlen():
        # Beleg-Datei auswählen
        file_path = filedialog.askopenfilename(
            title="Beleg auswählen",
            filetypes=[
                ("PDF Dateien", "*.pdf"),
                ("Bild Dateien", "*.png *.jpg *.jpeg"),
                ("Alle Dateien", "*.*")
            ]
        )

        if file_path:
            beleg_entry.delete(0, tk.END)
            beleg_entry.insert(0, file_path)

    app_button(
        beleg_frame,
        "📎",
        beleg_auswaehlen,
        width=4
    ).pack(side="left", padx=2)

    row += 1

    def speichern():
        try:
            betrag = float(betrag_entry.get().replace(",", "."))
        except ValueError:
            show_status("Ungültiger Betrag.")
            return

        datum = f"{jahr_box.get()}-{monat_box.get()}-{tag_box.get()}"

        eintrag = {
            "gebaeude_id": gebaeude["id"],
            "datum": datum,
            "typ": typ_box.get(),
            "kostenart": kostenart_box.get(),
            "umlageschluessel": umlage_box.get(),
            "betrag": betrag,
            "beschreibung": beschreibung_entry.get().strip(),
            "beleg_pfad": beleg_speichern(beleg_entry.get().strip())
        }

        add_kontobewegung(eintrag)
        show_status("Kontobewegung gespeichert.")
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

        for w in wohnungen:
            if umlage == "Wohnfläche":
                anteil = float(str(w["flaeche"]).replace(",", ".")) / gesamt_flaeche
                kosten = betrag * anteil

            elif umlage == "Miteigentumsanteile":
                anteil = float(str(w["miteigentumsanteile"]).replace(",", ".")) / gesamt_mea
                kosten = betrag * anteil

            elif umlage == "Wohneinheiten":
                kosten = betrag / len(wohnungen)

            elif umlage == "Nicht umlagefähig":
                kosten = 0

            else:
                # Standard: unbekannte Umlageschlüssel nach Wohnfläche verteilen
                anteil = float(str(w["flaeche"]).replace(",", ".")) / gesamt_flaeche
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
# HAUPTFENSTER
################################################################################################

# Tabellen initialisieren
init_gebaeude_table()
init_wohnungen_table()
init_meldungen_table()
init_konto_table()

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