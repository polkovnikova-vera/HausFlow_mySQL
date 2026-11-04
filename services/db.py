import os
import sqlite3

# Basisordner des Projekts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Datenordner
DATA_DIR = os.path.join(BASE_DIR, "data")

# Falls der Datenordner nicht existiert, wird er erstellt
os.makedirs(DATA_DIR, exist_ok=True)

# Pfad zur SQLite-Datenbank
DB_PATH = os.path.join(DATA_DIR, "hausflow.db")


def get_connection():
    # Verbindung zur SQLite-Datenbank herstellen
    return sqlite3.connect(DB_PATH)