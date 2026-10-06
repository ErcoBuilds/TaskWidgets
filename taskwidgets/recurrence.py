"""Wiederholungs-Logik: Termine berechnen, Erledigt/Übersprungen prüfen, Texte bilden."""
import calendar
import datetime as dt
import math

from taskwidgets.config import DAYS


def get_repeat(task):
    return task.get("repeat") or {"type": "weekly", "days": list(range(7))}


def task_time(task):
    r = get_repeat(task)
    return task.get("time") or r.get("from") or "00:00"


def task_times(task):
    """Alle Uhrzeiten der Aufgabe als sortierte Liste "HH:MM". Für Intervall-Aufgaben
    ist nur die Startzeit relevant; sonst die Liste ``times`` (Fallback: einzelne ``time``)."""
    if get_repeat(task)["type"] == "interval":
        return [task_time(task)]
    times = task.get("times")
    if times:
        return sorted(set(times))
    return [task_time(task)]


def occ_key(occ):
    """Eindeutiger Schlüssel eines Termins (Tag + Uhrzeit) für Erledigt/Übersprungen."""
    return occ.strftime("%Y-%m-%d %H:%M")


def is_skipped(task, occ):
    """Übersprungen? Erkennt sowohl termingenaue Schlüssel als auch alte, rein
    tagesbezogene Einträge (für Aufgaben mit nur einer Uhrzeit)."""
    sk = task.get("skip_days") or []
    return occ_key(occ) in sk or occ.date().isoformat() in sk


def is_done(task, occ):
    dd = task.get("done_days") or []
    return occ_key(occ) in dd or occ.date().isoformat() in dd


def is_day_done(task, day):
    """Ist an diesem Tag mindestens ein Termin abgehakt?"""
    diso = day.isoformat()
    return any(str(k).startswith(diso) for k in (task.get("done_days") or []))


def single_per_day(task):
    return get_repeat(task)["type"] != "interval"


def occurrences_on(task, day):
    """Alle geplanten Zeitpunkte der Aufgabe an diesem Tag (ohne Berücksichtigung von
    Überspringen/Erledigt)."""
    r = get_repeat(task)
    t = r["type"]
    until = r.get("until")
    if until and t != "once":
        try:
            if day > dt.date.fromisoformat(until):
                return []
        except ValueError:
            pass

    def at(timestr):
        h, m = map(int, timestr.split(":"))
        return dt.datetime.combine(day, dt.time(h, m))

    def times():
        return [at(ts) for ts in task_times(task)]

    if t == "once":
        return times() if day.isoformat() == r.get("date") else []
    if t == "weekly":
        return times() if day.weekday() in r.get("days", []) else []
    if t == "monthly":
        last = calendar.monthrange(day.year, day.month)[1]
        return times() if day.day == min(r.get("day", 1), last) else []
    if t == "biweekly":
        if day.weekday() not in r.get("days", []):
            return []
        anchor = dt.date.fromisoformat(r["anchor"])
        wa = anchor - dt.timedelta(days=anchor.weekday())
        wd = day - dt.timedelta(days=day.weekday())
        return times() if ((wd - wa).days // 7) % 2 == 0 else []
    if t == "interval":
        if r.get("days") and day.weekday() not in r["days"]:
            return []
        fh, fm = map(int, r["from"].split(":"))
        th, tm = map(int, r["to"].split(":"))
        start = dt.datetime.combine(day, dt.time(fh, fm))
        end = dt.datetime.combine(day, dt.time(th, tm))
        step = dt.timedelta(minutes=max(5, int(round(r.get("hours", 1) * 60))))
        out, cur = [], start
        while cur <= end:
            out.append(cur)
            cur += step
        return out
    return []


def next_occurrence(task, now, respect_state=True):
    """Nächster Zeitpunkt nach now. Überspringt bei respect_state übersprungene und
    bereits erledigte Tage."""
    for i in range(0, 400):
        day = now.date() + dt.timedelta(days=i)
        for occ in occurrences_on(task, day):
            if occ <= now:
                continue
            if respect_state and (is_skipped(task, occ) or is_done(task, occ)):
                continue
            return occ
    return None


def repeat_text(task):
    r = get_repeat(task)
    t = r["type"]
    if t == "once":
        return dt.date.fromisoformat(r["date"]).strftime("%d.%m.%Y")
    if t == "weekly":
        days = sorted(r.get("days", []))
        if days == list(range(7)):
            base = "täglich"
        elif days == list(range(5)):
            base = "werktags"
        elif days == [5, 6]:
            base = "Wochenende"
        else:
            base = ", ".join(DAYS[d] for d in days) or "–"
    elif t == "monthly":
        base = f"monatlich am {r.get('day', 1)}."
    elif t == "biweekly":
        base = "alle 2 Wochen · " + ", ".join(DAYS[d] for d in sorted(r.get("days", [])))
    elif t == "interval":
        h = r.get("hours", 1)
        h = int(h) if float(h).is_integer() else h
        base = f"alle {h} h · {r['from']}–{r['to']}"
    else:
        return ""
    until = r.get("until")
    if until:
        try:
            base += " · bis " + dt.date.fromisoformat(until).strftime("%d.%m.%y")
        except ValueError:
            pass
    return base


def day_label(occ, now):
    diff = (occ.date() - now.date()).days
    prefix = {0: "Heute", 1: "Morgen"}.get(diff, DAYS[occ.weekday()])
    return f"{prefix} {occ:%H:%M}"


def fmt_countdown(occ, now):
    mins = math.ceil((occ - now).total_seconds() / 60)
    if mins <= 0:
        return "jetzt"
    if mins < 60:
        return f"in {mins} min"
    h, m = divmod(mins, 60)
    if h < 24:
        return f"in {h} h {m:02d}"
    days = (occ.date() - now.date()).days
    return "morgen" if days == 1 else f"in {days} Tagen"
