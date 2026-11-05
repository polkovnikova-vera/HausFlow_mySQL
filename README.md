# HausFlow – Projektwoche

REST-API zur Verwaltung von Gebäuden, Schadensmeldungen und Rechnungen.

## 1. Projektbeschreibung

HausFlow ist ein Python-basiertes Backend für die digitale Hausverwaltung.

Die Anwendung ermöglicht die Verwaltung von Schadensmeldungen und Rechnungen unter Berücksichtigung unterschiedlicher Benutzerrollen und gebäudebezogener Zugriffsrechte.

### Funktionen

* Benutzeranmeldung und Abmeldung mit Bearer-Token
* Rollenbasierte Zugriffskontrolle (`tenant`, `staff`, `admin`)
* Zuordnung von Benutzern zu Gebäuden
* Erstellung und Bearbeitung von Schadensmeldungen
* Übernahme und Abschluss von Meldungen
* Erstellung und Verwaltung von Rechnungen
* Kennzeichnung von Rechnungen als bezahlt
* Verknüpfung von Meldungen und Rechnungen über eine M:N-Beziehung
* Validierung von Eingabedaten mit Pydantic
* Automatische API-Dokumentation mit OpenAPI

## 2. Verwendete Technologien

| Technologie    | Verwendung               |
| -------------- | ------------------------ |
| Python         | Programmiersprache       |
| FastAPI        | REST-API                 |
| Pydantic       | Datenvalidierung         |
| SQLAlchemy     | ORM und Datenbankzugriff |
| MySQL 8.4      | Relationale Datenbank    |
| PyMySQL        | MySQL-Treiber            |
| Docker Compose | Datenbankumgebung        |
| Alembic        | Datenbankmigrationen     |
| pytest         | Automatisierte Tests     |
| Postman        | Manuelles API-Testing    |

## 3. Projektstruktur

```text
HausFlow/
├── alembic/
│   └── versions/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── health.py
│   │   │   ├── invoices.py
│   │   │   └── reports.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── dependencies.py
│   │   ├── main.py
│   │   ├── passwords.py
│   │   ├── schemas.py
│   │   └── security.py
│   ├── tests/
│   └── requirements.txt
├── database/
│   ├── connection.py
│   └── models.py
├── compose.yaml
├── alembic.ini
├── pytest.ini
├── seed.py
├── .env.example
└── README.md
```

## 4. Installation

### Voraussetzungen

* Python
* Docker Desktop
* Git

Repository klonen und in das Projektverzeichnis wechseln.

Virtuelle Umgebung erstellen:

```powershell
python -m venv .venv
```

Virtuelle Umgebung unter Windows aktivieren:

```powershell
.\.venv\Scripts\Activate.ps1
```

Abhängigkeiten installieren:

```powershell
python -m pip install -r backend/requirements.txt
```

## 5. Umgebungsvariablen

Die Datei `.env.example` als `.env` kopieren:

```powershell
Copy-Item .env.example .env
```

Anschließend die Platzhalter für die Passwörter durch eigene Werte ersetzen.

Benötigte Variablen:

```dotenv
MYSQL_PASSWORD=CHANGE_ME
MYSQL_ROOT_PASSWORD=CHANGE_ME_ROOT

HAUSFLOW_DB_HOST=127.0.0.1
HAUSFLOW_DB_PORT=3308
HAUSFLOW_DB_NAME=hv
HAUSFLOW_DB_USER=hv_user
HAUSFLOW_DB_PASSWORD=CHANGE_ME

HAUSFLOW_SEED_PASSWORD=CHANGE_ME_SEED

HAUSFLOW_CORS_ORIGINS=
```

`MYSQL_PASSWORD` und `HAUSFLOW_DB_PASSWORD` müssen übereinstimmen.

Die Datei `.env` enthält vertrauliche Informationen und darf nicht in Git eingecheckt werden.

## 6. MySQL mit Docker starten

Datenbankcontainer starten:

```powershell
docker compose up -d
```

Status überprüfen:

```powershell
docker compose ps
```

Die MySQL-Datenbank läuft auf:

```text
Host: 127.0.0.1
Port: 3308
Datenbank: hv
```

Die Daten werden in einem Docker-Volume gespeichert.

## 7. Datenbankmigrationen

HausFlow verwendet Alembic zur Verwaltung der Datenbankstruktur.

Migrationen ausführen:

```powershell
python -m alembic upgrade head
```

Aktuelle Version anzeigen:

```powershell
python -m alembic current
```

Datenbankschema überprüfen:

```powershell
python -m alembic check
```

Die aktuelle Basismigration lautet `0001`.

## 8. Testdaten erstellen

Das Skript `seed.py` erstellt:

* 10 Benutzer
* 5 Gebäude
* Benutzer-Gebäude-Zuordnungen

Ausführen:

```powershell
python seed.py
```

Das Skript prüft vor dem Anlegen, ob die jeweiligen Benutzer, Gebäude und Zuordnungen bereits existieren.

Die Passwörter der Testbenutzer werden über `HAUSFLOW_SEED_PASSWORD` festgelegt und mit Argon2 gehasht.

**Hinweis:** Die Seed-Daten sind ausschließlich für die lokale Entwicklungs- und Demonstrationsumgebung vorgesehen.

## 9. FastAPI starten

Im Projektverzeichnis:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Falls Port 8000 bereits belegt ist, kann alternativ Port 8001 verwendet werden.

### API-Dokumentation

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI JSON:

```text
http://127.0.0.1:8000/openapi.json
```

Bei Verwendung von Port 8001 muss die Portnummer entsprechend angepasst werden.

## 10. API-Endpunkte

### Authentifizierung

| Methode | Endpoint | Beschreibung |
|---|---|---|
| POST | `/api/v1/auth/register` | Neuen Benutzer registrieren |
| POST | `/api/v1/auth/login` | Benutzer anmelden |
| GET | `/api/v1/auth/me` | Aktuellen Benutzer anzeigen |
| POST | `/api/v1/auth/logout` | Benutzer abmelden |
| GET | `/api/v1/auth/staff-check` | Mitarbeiterberechtigung prüfen |
| GET | `/api/v1/auth/admin-check` | Administratorberechtigung prüfen |

#### Benutzerregistrierung

Neue Benutzer können über den Endpoint
`POST /api/v1/auth/register` registriert werden.

Beispiel:

```json
{
  "username": "testuser1",
  "password": "Test12345!"
}

### Schadensmeldungen

| Methode | Endpoint                               | Beschreibung                   |
| ------- | -------------------------------------- | ------------------------------ |
| POST    | `/api/v1/reports`                      | Meldung erstellen              |
| GET     | `/api/v1/reports`                      | Meldungen auflisten            |
| GET     | `/api/v1/reports/{report_id}`          | Einzelne Meldung anzeigen      |
| PATCH   | `/api/v1/reports/{report_id}`          | Meldung bearbeiten             |
| PATCH   | `/api/v1/reports/{report_id}/claim`    | Meldung übernehmen             |
| PATCH   | `/api/v1/reports/{report_id}/resolve`  | Meldung abschließen            |
| GET     | `/api/v1/reports/{report_id}/invoices` | Verknüpfte Rechnungen anzeigen |

### Rechnungen

| Methode | Endpoint                        | Beschreibung                   |
| ------- | ------------------------------- | ------------------------------ |
| POST    | `/api/v1/invoices`              | Rechnung erstellen             |
| GET     | `/api/v1/invoices`              | Rechnungen auflisten           |
| GET     | `/api/v1/invoices/{invoice_id}` | Einzelne Rechnung anzeigen     |
| PATCH   | `/api/v1/invoices/{invoice_id}` | Rechnung als bezahlt markieren |

### System

```http
GET /api/v1/health
```

## 11. Benutzerrollen und Sicherheit

HausFlow unterscheidet drei Benutzerrollen:

**Tenant**

Kann eigene Meldungen erstellen, anzeigen und unter den vorgesehenen Bedingungen bearbeiten.

**Staff**

Kann Meldungen und Rechnungen der zugeordneten Gebäude verwalten.

**Admin**

Besitzt erweiterte Berechtigungen zur Verwaltung von Meldungen und Rechnungen.

Die Authentifizierung erfolgt über Bearer-Token.

Zugriffsrechte werden serverseitig überprüft.

## 12. Pydantic-Validierung

Pydantic überprüft eingehende Daten vor der Verarbeitung.

Beispiele:

* Pflichtfelder dürfen nicht fehlen.
* Titel und Beschreibungen dürfen nicht leer sein.
* Titel aus ausschließlich Leerzeichen werden abgelehnt.
* Gebäude-IDs müssen positiv sein.
* Rechnungsbeträge müssen größer als null sein.
* Rechnungsbeträge dürfen maximal zwei Nachkommastellen enthalten.
* Rechnungsdaten müssen gültige Datumswerte sein.
* Verknüpfte Meldungs-IDs müssen positiv sein.

Ungültige Eingaben führen zu HTTP 422.

## 13. Automatisierte Tests

HausFlow verwendet pytest.

Die Tests befinden sich unter:

```text
backend/tests/
```

Alle Tests ausführen:

```powershell
python -m pytest -v
```

Kurze Ausgabe:

```powershell
python -m pytest -q
```

### Testergebnisse

| Testbereich         | Anzahl |
| ------------------- | -----: |
| Health              |      1 |
| Database            |      1 |
| Authentication      |      6 |
| Reports             |      7 |
| Invoices            |      9 |
| API Security        |      8 |
| Pydantic Validation |     17 |
| **Gesamt**          | **49** |

Letzter erfolgreicher Testlauf:

```text
49 passed
```

### Testdatenbank

Für Integrationstests wird die separate MySQL-Datenbank `hv_test` verwendet.

Die Test-Fixtures nutzen SQLAlchemy-Transaktionen und SAVEPOINTs, um Teständerungen nach dem jeweiligen Test zurückzurollen.

Die produktive Entwicklungsdatenbank `hv` wird nicht als Testdatenbank verwendet.

**Hinweis:** Vor der ersten Ausführung der vollständigen Integrationstests muss `hv_test` angelegt und mit dem erforderlichen Datenbankschema vorbereitet werden. Die Datenbank wird nicht automatisch durch Docker Compose erstellt.

## 14. SQL-Statistik

HausFlow enthält SQL-Abfragen zur Auswertung von Gebäuden.

Ermittelt werden:

* Anzahl der Meldungen pro Gebäude
* Anzahl der Rechnungen pro Gebäude
* Gesamtsumme der Rechnungen

Dafür werden unter anderem folgende SQL-Konstruktionen verwendet:

`LEFT JOIN`, `COUNT`, `SUM`, `GROUP BY` und `COALESCE`.

Durch getrennte Aggregation von Meldungen und Rechnungen wird eine Mehrfachzählung vermieden.

## 15. Postman

Die API wurde zusätzlich manuell mit Postman getestet.

Dabei wurden unter anderem folgende Abläufe überprüft:

1. Anmeldung
2. Meldung erstellen
3. Meldung bearbeiten
4. Meldung durch Mitarbeiter übernehmen
5. Meldung abschließen
6. Rechnung erstellen
7. Rechnung mit Meldung verknüpfen
8. Rechnung als bezahlt markieren
9. Zugriffsrechte überprüfen
10. Abmeldung

Die OpenAPI-Spezifikation kann über `/openapi.json` abgerufen und in Postman importiert werden.

## 16. Einsatz von KI

Während der Entwicklung wurde ChatGPT als unterstützendes Werkzeug eingesetzt.

Die Unterstützung umfasste insbesondere:

* Erklärung von Python-, SQL- und FastAPI-Konzepten
* Unterstützung bei der API-Implementierung
* Erstellung und Überarbeitung von Testfällen
* Analyse von Fehlermeldungen
* Unterstützung bei Pydantic-Validierungen
* Erklärung von SQL-Abfragen
* Strukturierung der Projektdokumentation

Die Anwendung wurde schrittweise lokal implementiert, ausgeführt und getestet.

## 17. Projektstatus

**Version:** 0.1.0

**Status:** Funktionsfähiges Backend für die Projektwoche.

Implementiert und getestet sind:

* REST-API
* Authentifizierung
* Rollenbasierte Zugriffsrechte
* Schadensmeldungen
* Rechnungsverwaltung
* M:N-Beziehungen
* Datenvalidierung
* Datenbankmigrationen
* Automatisierte Tests

Die Weiterentwicklung kann zusätzliche Verwaltungsfunktionen und eine grafische Benutzeroberfläche umfassen.
