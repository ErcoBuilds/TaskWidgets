"""
TaskWidgets – Erinnerungs-Widget für den Windows-11-Desktop (modularer Aufbau).

Paket-Übersicht:
    config            Konstanten, Farbpaletten, Theme-/DPI-System (set_palette, px …)
    storage           data.json laden/speichern/migrieren
    recurrence        Wiederholungen und Termin-Berechnung
    platform_win      Windows-Helfer: DPI, Titelleiste, Ecken, Pipette, Autostart, Verknüpfung
    winapi            Infobereich-Symbol (Tray) und Einzelinstanz-Prüfung
    widgets           Wiederverwendbare tkinter-Bausteine im Programmdesign
    reminder          Erinnerungs-Pop-ups und Schlummer-Dialog
    colorpicker       Eigener Farbwähler mit Pipette
    editor            Aufgaben-Editor
    lists             Fenster „Alle Aufgaben" und „Verlauf"
    settings_dialogs  Ruhezeiten, Einstellungsfenster, Erststart-Assistent
    app               Haupt-Widget und App-Steuerung (main)

Start:  python -m taskwidgets   (oder TaskWidgets.pyw im übergeordneten Ordner)
Keine externen Pakete nötig – nur Python 3 mit tkinter.
"""

__version__ = "1.0"
