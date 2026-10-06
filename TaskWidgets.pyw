"""
TaskWidgets – Startdatei (Doppelklick, läuft mit pythonw ohne Konsole).

Diese Datei liegt neben dem Paketordner ``taskwidgets`` und startet die App.
Der eigentliche Code steckt in den Modulen unter ``taskwidgets/`` – siehe
taskwidgets/__init__.py für die Übersicht.
"""
import os
import sys

# Den Ordner dieser Datei auf den Importpfad legen, damit "taskwidgets" gefunden
# wird – egal aus welchem Arbeitsverzeichnis gestartet wird.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from taskwidgets.app import main

if __name__ == "__main__":
    main()
