"""Laden, Speichern und Migrieren der Aufgaben-/Einstellungsdatei (data.json)."""
import datetime as dt
import json
import os

from taskwidgets.config import DATA_DIR, DATA_FILE


def load_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data.setdefault("tasks", [])
    data.setdefault("settings", {})
    data.setdefault("log", [])
    for t in data["tasks"]:
        migrate_task(t)
    return data


def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def migrate_task(t):
    """Ältere Aufgaben (mit days/date) auf das neue repeat-Format bringen und Listen kürzen."""
    if "repeat" not in t:
        if t.get("date"):
            t["repeat"] = {"type": "once", "date": t["date"]}
        else:
            days = t.get("days") or list(range(7))
            t["repeat"] = {"type": "weekly", "days": days}
    t.pop("date", None)
    t.pop("days", None)
    t.setdefault("warn", 0)
    # Übersprungene/erledigte Tage, die älter als 30 Tage sind, entfernen
    cutoff = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    for key in ("skip_days", "done_days"):
        if t.get(key):
            t[key] = [d for d in t[key] if d >= cutoff]
