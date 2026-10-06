"""
Konstanten, Farbpaletten und das Theme-/DPI-System.

Die Farbnamen (BG, FG, ACCENT …), FONT, ICON_FONT und SCALE sind veränderliche
Modul-Globals. Beim Theme-Wechsel ruft die App set_palette() auf, das die neue
Palette in dieses Modul schreibt UND per _broadcast() in die Namensräume aller
Module verteilt, die sich mit subscribe(globals()) registriert haben. So lesen
alle Module die Farben weiterhin über den bloßen Namen (z. B. ``BG``) und der
Wechsel zwischen Hell und Dunkel schlägt überall sofort durch.
"""
import datetime as dt
import os

__all__ = [
    "APP_NAME", "DATA_DIR", "DATA_FILE", "STARTUP_FILE",
    "GRACE", "LOG_DAYS", "DAYS", "DAYS_LONG", "MONTHS", "COLORS", "PALETTES",
    "BG", "CARD", "HOVER", "BORDER", "FG", "MUTED", "ACCENT", "DANGER",
    "FONT", "ICON_FONT", "SCALE",
    "px", "set_palette", "set_scale", "set_icon_font", "subscribe",
]

APP_NAME = "TaskWidgets"
DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
DATA_FILE = os.path.join(DATA_DIR, "data.json")
STARTUP_FILE = os.path.join(
    os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup", APP_NAME + ".vbs"
)

GRACE = dt.timedelta(minutes=30)  # verpasste Erinnerungen werden bis zu 30 min nachgeholt
LOG_DAYS = 7                      # Verlauf zeigt die letzten 7 Tage
DAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
DAYS_LONG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]
COLORS = ["#5B9BFF", "#34C38F", "#F7B84B", "#F46A6A", "#A66CFF", "#3DD5E0"]

# Farbpaletten für dunkel und hell. set_palette() kopiert eine davon in die globalen Namen.
PALETTES = {
    "dark": dict(BG="#1C1D22", CARD="#26282F", HOVER="#30333C", BORDER="#3A3D47",
                 FG="#ECEDF2", MUTED="#9093A0", ACCENT="#5B9BFF", DANGER="#F46A6A"),
    "light": dict(BG="#F3F4F7", CARD="#FFFFFF", HOVER="#E7EAF0", BORDER="#D3D7E0",
                  FG="#1D1E24", MUTED="#5F636E", ACCENT="#2F6BE0", DANGER="#D64545"),
}
BG = CARD = HOVER = BORDER = FG = MUTED = ACCENT = DANGER = "#000000"
FONT = "Segoe UI"
ICON_FONT = "Segoe Fluent Icons"
SCALE = 1.0

# Namensräume (module globals()) der Module, die Theme-Werte über bloße Namen lesen.
_subscribers = []
_THEME_NAMES = ("BG", "CARD", "HOVER", "BORDER", "FG", "MUTED", "ACCENT", "DANGER",
                "FONT", "ICON_FONT", "SCALE")


def _snapshot():
    g = globals()
    return {k: g[k] for k in _THEME_NAMES}


def _broadcast():
    snap = _snapshot()
    for ns in _subscribers:
        ns.update(snap)


def subscribe(ns):
    """``ns`` ist das globals()-Dict eines Moduls. Es bekommt die aktuellen Theme-Werte
    und wird bei jedem späteren Wechsel automatisch aktualisiert."""
    _subscribers.append(ns)
    ns.update(_snapshot())


def set_palette(name):
    globals().update(PALETTES.get(name, PALETTES["dark"]))
    _broadcast()


def set_scale(scale):
    global SCALE
    SCALE = scale
    _broadcast()


def set_icon_font(name):
    global ICON_FONT
    ICON_FONT = name
    _broadcast()


set_palette("dark")


def px(v):
    return int(round(v * SCALE))
