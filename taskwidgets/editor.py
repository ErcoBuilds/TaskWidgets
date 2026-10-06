"""Der Aufgaben-Editor (Neue Aufgabe / Aufgabe bearbeiten)."""
import datetime as dt
import tkinter as tk
import uuid
from tkinter import messagebox

from taskwidgets import config
from taskwidgets.config import *  # noqa: F401,F403
from taskwidgets.widgets import (_hoverable, day_pills, entry_style, icon_button,
                                 label, segmented, stepper, text_button, toggle)
from taskwidgets.recurrence import get_repeat, occurrences_on, task_times
from taskwidgets.storage import save_data
from taskwidgets.colorpicker import ColorPicker
from taskwidgets.platform_win import show_themed

config.subscribe(globals())

REPEAT_TYPES = [("daily", "Täglich"), ("weekdays", "Werktags"), ("weekend", "Wochenende"),
                ("custom", "Bestimmte Wochentage"), ("interval", "Alle paar Stunden"),
                ("monthly", "Monatlich"), ("biweekly", "Alle 2 Wochen"), ("once", "Einmalig")]
REPEAT_LABEL = dict(REPEAT_TYPES)
REPEAT_KEY = {v: k for k, v in REPEAT_TYPES}


class TaskEditor(tk.Toplevel):
    def __init__(self, app, task=None):
        super().__init__(app.root)
        self.withdraw()
        self.app, self.task = app, task
        self.title("Aufgabe bearbeiten" if task else "Neue Aufgabe")
        self.configure(bg=BG, padx=px(20), pady=px(14))
        self.resizable(False, False)
        self.attributes("-topmost", bool(self.app.settings["topmost"]))
        self.attributes("-toolwindow", True)
        self.protocol("WM_DELETE_WINDOW", self.close)

        now = dt.datetime.now()
        t = task or {}
        r = get_repeat(task) if task else {"type": "daily"}
        default_time = (now + dt.timedelta(hours=1)).strftime("%H:00")
        base_times = task_times(task) if task else [default_time]
        days = sorted(r.get("days", []))

        # Startwerte
        self.v_title = tk.StringVar(value=t.get("title", ""))
        # Mehrere Uhrzeiten: je Eintrag ein (Stunde, Minute)-Paar von StringVars
        self.time_vars = []
        for ts in base_times:
            hh, mm = ts.split(":")
            self.time_vars.append((tk.StringVar(value=hh), tk.StringVar(value=mm)))
        self.v_note = tk.StringVar(value=t.get("note", ""))
        self.v_sound = tk.BooleanVar(value=bool(t.get("sound", True)))
        date = dt.date.fromisoformat(r["date"]) if r["type"] == "once" else now.date()
        self.v_date = tk.StringVar(value=date.strftime("%d.%m.%Y"))
        self.v_monthday = tk.StringVar(value=str(r.get("day", now.day)))
        fh, fm = (r.get("from", "08:00")).split(":")
        th, tm = (r.get("to", "18:00")).split(":")
        self.v_fh, self.v_fm, self.v_th, self.v_tm = (tk.StringVar(value=x) for x in (fh, fm, th, tm))
        self.v_ihours = tk.StringVar(value=str(r.get("hours", 2)))
        default_days = days or ([0, 1, 2, 3, 4] if r["type"] in ("weekdays",) else list(range(7)))
        self.v_days = [tk.IntVar(value=int(i in default_days)) for i in range(7)]
        self.color = t.get("color") or COLORS[len(app.tasks) % len(COLORS)]

        # Wiederholungs-Startauswahl bestimmen
        init = r["type"]
        if init == "weekly":
            init = {tuple(range(7)): "daily", tuple(range(5)): "weekdays",
                    (5, 6): "weekend"}.get(tuple(days), "custom")
        self.v_type = tk.StringVar(value=REPEAT_LABEL.get(init, "Täglich"))

        warn = t.get("warn", 0)
        self.v_warn = tk.StringVar(value={0: "none", 15: "15", 30: "30"}.get(warn, "custom"))
        self.v_warn_custom = tk.StringVar(value=str(warn if warn not in (0, 15, 30) else 10))

        # Enddatum für Wiederholungen (optional)
        until = r.get("until")
        self.v_has_until = tk.BooleanVar(value=bool(until))
        default_until = (now.date() + dt.timedelta(days=30))
        until_date = dt.date.fromisoformat(until) if until else default_until
        self.v_until = tk.StringVar(value=until_date.strftime("%d.%m.%Y"))

        def section(text):
            label(self, text, 9, fg=MUTED).pack(anchor="w", pady=(px(9), px(3)))

        section("Aufgabe")
        e_title = tk.Entry(self, textvariable=self.v_title, width=36, **entry_style())
        e_title.pack(fill="x", ipady=px(4))

        section("Wiederholung")
        om = tk.OptionMenu(self, self.v_type, *[lbl for _, lbl in REPEAT_TYPES],
                           command=lambda _=None: self.update_mode())
        om.config(bg=CARD, fg=FG, activebackground=HOVER, activeforeground=FG, relief="flat",
                  highlightthickness=1, highlightbackground=BORDER, font=(FONT, 10), anchor="w")
        om["menu"].config(bg=CARD, fg=FG, activebackground=ACCENT, activeforeground="#101114")
        om.pack(fill="x")

        # Unterbereiche je nach Wiederholung
        self.days_box = tk.Frame(self, bg=BG)
        self.days_hint = label(self.days_box, "", 9, fg=MUTED)
        self.days_hint.pack(anchor="w")
        drow = tk.Frame(self.days_box, bg=BG)
        drow.pack(anchor="w", pady=(px(4), 0))
        day_pills(drow, self.v_days).pack(anchor="w")

        self.date_box = tk.Frame(self, bg=BG)
        label(self.date_box, "Datum (TT.MM.JJJJ)", 9, fg=MUTED).pack(side="left")
        tk.Entry(self.date_box, textvariable=self.v_date, width=12,
                 **entry_style()).pack(side="left", padx=(px(8), 0), ipady=px(2))

        self.month_box = tk.Frame(self, bg=BG)
        label(self.month_box, "am", 10).pack(side="left")
        stepper(self.month_box, self.v_monthday, 1, 31).pack(side="left", padx=px(6))
        label(self.month_box, ". Tag des Monats", 10).pack(side="left")

        self.interval_box = tk.Frame(self, bg=BG)
        label(self.interval_box, "alle", 10).pack(side="left")
        stepper(self.interval_box, self.v_ihours, 1, 12).pack(side="left", padx=px(5))
        label(self.interval_box, "Std von", 10).pack(side="left")
        self._time_spin(self.interval_box, self.v_fh, self.v_fm, fh, fm)
        label(self.interval_box, "bis", 10).pack(side="left", padx=(px(6), 0))
        self._time_spin(self.interval_box, self.v_th, self.v_tm, th, tm)

        self.time_box = tk.Frame(self, bg=BG)
        thead = tk.Frame(self.time_box, bg=BG)
        thead.pack(fill="x", pady=(px(9), px(3)))
        self.time_lbl = label(thead, "Uhrzeiten", 9, fg=MUTED)
        self.time_lbl.pack(side="left")
        # Ton pro Aufgabe (gilt für alle Uhrzeiten), rechts neben dem Uhrzeiten-Abschnitt
        toggle(thead, self.v_sound).pack(side="right")
        label(thead, "Ton", 9, fg=MUTED).pack(side="right", padx=(0, px(6)))
        self.times_rows = tk.Frame(self.time_box, bg=BG)
        self.times_rows.pack(anchor="w")
        self.add_time_btn = text_button(self.time_box, "+ weitere Uhrzeit", self.add_time_row,
                                        fg=ACCENT)
        self.add_time_btn.pack(anchor="w", pady=(px(4), 0))
        self.rebuild_time_rows()

        # Enddatum für Wiederholungen (bei allen außer „Einmalig")
        self.until_box = tk.Frame(self, bg=BG)
        label(self.until_box, "Enddatum", 9, fg=MUTED).pack(anchor="w", pady=(px(9), px(3)))
        urow = tk.Frame(self.until_box, bg=BG)
        urow.pack(anchor="w")
        label(urow, "Endet am", 10).pack(side="left", padx=(0, px(8)))
        toggle(urow, self.v_has_until, command=self.update_until).pack(side="left")
        self.until_entry = tk.Entry(urow, textvariable=self.v_until, width=12, **entry_style())
        self.until_entry.pack(side="left", padx=(px(6), 0), ipady=px(2))
        label(urow, "TT.MM.JJJJ", 9, fg=MUTED).pack(side="left", padx=(px(6), 0))

        self.anchor = tk.Frame(self, bg=BG)
        self.anchor.pack()

        section("Vorwarnung")
        segmented(self, self.v_warn,
                  (("none", "Keine"), ("15", "15 Min"), ("30", "30 Min"), ("custom", "Eigene")),
                  command=self.update_mode).pack(anchor="w")
        self.warn_box = tk.Frame(self, bg=BG)
        stepper(self.warn_box, self.v_warn_custom, 1, 1440, width=4).pack(side="left")
        label(self.warn_box, "Minuten vorher", 10).pack(side="left", padx=(px(6), 0))
        self.warn_anchor = tk.Frame(self, bg=BG)  # legt fest, wo das Vorwarn-Feld einfügt
        self.warn_anchor.pack()

        section("Notiz (optional)")
        tk.Entry(self, textvariable=self.v_note, width=36, **entry_style()).pack(fill="x", ipady=px(4))

        section("Farbe")
        self.crow = tk.Frame(self, bg=BG)
        self.crow.pack(anchor="w")
        self.build_color_row()

        brow = tk.Frame(self, bg=BG)
        brow.pack(fill="x", pady=(px(16), 0))
        text_button(brow, "Speichern", self.save, bg=ACCENT, fg="#101114", hover=FG,
                    bold=True).pack(side="right")
        text_button(brow, "Abbrechen", self.close).pack(side="right", padx=(0, px(6)))
        text_button(brow, "Testen", self.test).pack(side="left")
        if task:
            text_button(brow, "Löschen", self.delete, fg=DANGER).pack(side="left", padx=(px(6), 0))

        self.update_mode()
        self.bind("<Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.close())
        self.update_idletasks()
        sw_, sh_ = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw_ - self.winfo_reqwidth()) // 2}+{(sh_ - self.winfo_reqheight()) // 4}")
        show_themed(self, self.app.effective_theme() == "dark")
        self.after(50, lambda: (self.focus_force(), e_title.focus_set()))

    def _time_spin(self, parent, vh, vm, h, m, big=False):
        vh.set(h)
        vm.set(m)
        stepper(parent, vh, 0, 23, wrap=True, pad=True).pack(side="left")
        label(parent, ":", 13 if big else 11).pack(side="left", padx=px(2))
        stepper(parent, vm, 0, 59, wrap=True, pad=True).pack(side="left")

    # ---- Mehrere Uhrzeiten
    def rebuild_time_rows(self):
        for w in self.times_rows.winfo_children():
            w.destroy()
        for idx, (vh, vm) in enumerate(self.time_vars):
            rowf = tk.Frame(self.times_rows, bg=BG)
            rowf.pack(anchor="w", pady=(0, px(4)))
            stepper(rowf, vh, 0, 23, wrap=True, pad=True).pack(side="left")
            label(rowf, ":", 13).pack(side="left", padx=px(2))
            stepper(rowf, vm, 0, 59, wrap=True, pad=True).pack(side="left")
            if len(self.time_vars) > 1:
                rm = tk.Label(rowf, text="✕", font=(FONT, 11), bg=BG, fg=MUTED, cursor="hand2",
                              padx=px(6))
                _hoverable(rm, BG, HOVER, MUTED, DANGER)
                rm.bind("<Button-1>", lambda e, i=idx: self.remove_time_row(i))
                rm.pack(side="left", padx=(px(4), 0))

    def add_time_row(self):
        last_h = self.time_vars[-1][0].get() if self.time_vars else "08"
        self.time_vars.append((tk.StringVar(value=last_h), tk.StringVar(value="00")))
        self.rebuild_time_rows()

    def remove_time_row(self, idx):
        if len(self.time_vars) > 1:
            del self.time_vars[idx]
            self.rebuild_time_rows()

    def update_until(self):
        self.until_entry.config(state="normal" if self.v_has_until.get() else "disabled")

    def build_color_row(self):
        for w in self.crow.winfo_children():
            w.destroy()
        recents = [c for c in self.app.settings.get("recent_colors", []) if c not in COLORS]
        shown = list(COLORS) + recents
        if self.color not in shown:
            shown.append(self.color)
        for c in shown:
            sw = tk.Label(self.crow, bg=c, width=3, height=1, cursor="hand2", highlightthickness=2,
                          highlightbackground=FG if c == self.color else BG)
            sw.pack(side="left", padx=(0, px(6)))
            sw.bind("<Button-1>", lambda e, c=c: self.pick_color(c))
        add = tk.Label(self.crow, text="+", bg=CARD, fg=FG, width=3, height=1, cursor="hand2",
                       font=(FONT, 12, "bold"), highlightthickness=2, highlightbackground=BORDER)
        add.pack(side="left", padx=(px(2), 0))
        add.bind("<Button-1>", lambda e: self.choose_custom())

    def pick_color(self, c):
        self.color = c
        self.build_color_row()

    def choose_custom(self):
        ColorPicker(self, self.color, self._custom_chosen)

    def _custom_chosen(self, hexcol):
        self.add_recent(hexcol)
        self.pick_color(hexcol)

    def add_recent(self, c):
        if not (isinstance(c, str) and c.startswith("#")) or c in COLORS:
            return
        rc = self.app.settings.setdefault("recent_colors", [])
        if c in rc:
            rc.remove(c)
        rc.insert(0, c)
        del rc[1:]
        save_data(self.app.data)

    def key(self):
        return REPEAT_KEY.get(self.v_type.get(), "daily")

    def update_mode(self):
        key = self.key()
        for box in (self.days_box, self.date_box, self.month_box, self.interval_box,
                    self.time_box, self.until_box):
            box.pack_forget()
        if key in ("custom", "biweekly", "interval"):
            self.days_hint.config(text="nur an diesen Tagen (optional)" if key == "interval"
                                  else "an diesen Wochentagen")
            self.days_box.pack(anchor="w", pady=(px(6), 0), before=self.anchor)
        if key == "once":
            self.date_box.pack(anchor="w", pady=(px(6), 0), before=self.anchor)
        if key == "monthly":
            self.month_box.pack(anchor="w", pady=(px(6), 0), before=self.anchor)
        if key == "interval":
            self.interval_box.pack(anchor="w", pady=(px(8), 0), before=self.anchor)
        else:
            self.time_box.pack(anchor="w", fill="x", before=self.anchor)
        if key != "once":  # Enddatum ergibt nur bei Wiederholungen Sinn
            self.until_box.pack(anchor="w", before=self.anchor)
        self.update_until()
        self.warn_box.pack_forget()
        if self.v_warn.get() == "custom":
            self.warn_box.pack(anchor="w", pady=(px(4), 0), before=self.warn_anchor)

    def _time_str(self, vh, vm):
        return f"{int(vh.get()):02d}:{int(vm.get()):02d}"

    def collect(self):
        def fail(msg):
            messagebox.showerror("Ungültige Eingabe", msg, parent=self)
            return None

        title = self.v_title.get().strip()
        if not title:
            return fail("Bitte gib einen Titel ein.")
        key = self.key()
        selected = [i for i, v in enumerate(self.v_days) if v.get()]
        times = None
        try:
            if key == "interval":
                hours = float(self.v_ihours.get().replace(",", "."))
                if hours <= 0:
                    raise ValueError
                frm, to = self._time_str(self.v_fh, self.v_fm), self._time_str(self.v_th, self.v_tm)
                if to < frm:
                    return fail("Die Endzeit muss nach der Startzeit liegen.")
                repeat = {"type": "interval", "hours": hours, "from": frm, "to": to, "days": selected}
                time = frm
            else:
                times = sorted({self._time_str(vh, vm) for vh, vm in self.time_vars})
                time = times[0]
                if key == "once":
                    date = dt.datetime.strptime(self.v_date.get().strip(), "%d.%m.%Y").date()
                    repeat = {"type": "once", "date": date.isoformat()}
                elif key == "daily":
                    repeat = {"type": "weekly", "days": list(range(7))}
                elif key == "weekdays":
                    repeat = {"type": "weekly", "days": list(range(5))}
                elif key == "weekend":
                    repeat = {"type": "weekly", "days": [5, 6]}
                elif key == "custom":
                    if not selected:
                        return fail("Bitte wähle mindestens einen Wochentag.")
                    repeat = {"type": "weekly", "days": selected}
                elif key == "monthly":
                    repeat = {"type": "monthly", "day": int(self.v_monthday.get())}
                elif key == "biweekly":
                    if not selected:
                        return fail("Bitte wähle mindestens einen Wochentag.")
                    monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
                    anchor = (self.task.get("repeat", {}).get("anchor") if self.task else None) or monday.isoformat()
                    repeat = {"type": "biweekly", "days": selected, "anchor": anchor}
        except ValueError:
            return fail("Bitte prüfe Uhrzeit, Datum und Zahlenfelder.")

        if key != "once" and self.v_has_until.get():
            try:
                until = dt.datetime.strptime(self.v_until.get().strip(), "%d.%m.%Y").date()
            except ValueError:
                return fail("Bitte ein gültiges Enddatum (TT.MM.JJJJ) eingeben.")
            if until < dt.date.today():
                return fail("Das Enddatum liegt in der Vergangenheit.")
            repeat["until"] = until.isoformat()

        warn = {"none": 0, "15": 15, "30": 30}.get(self.v_warn.get())
        if warn is None:
            try:
                warn = int(self.v_warn_custom.get())
                if warn < 1:
                    raise ValueError
            except ValueError:
                return fail("Die eigene Vorwarnzeit muss eine Zahl ab 1 sein.")
        return {"title": title, "time": time, "times": times, "note": self.v_note.get().strip(),
                "color": self.color, "repeat": repeat, "warn": warn,
                "sound": bool(self.v_sound.get())}

    def save(self):
        fields = self.collect()
        if not fields:
            return
        now = dt.datetime.now()
        probe = {**fields}
        if probe["repeat"]["type"] == "once":
            occs = occurrences_on(probe, dt.date.fromisoformat(probe["repeat"]["date"]))
            if not any(o > now for o in occs):
                messagebox.showerror("Ungültige Eingabe", "Dieser Zeitpunkt liegt in der Vergangenheit.",
                                     parent=self)
                return
        task = self.task
        if task is None:
            task = {"id": uuid.uuid4().hex, "enabled": True}
            self.app.tasks.append(task)
        task.update(fields)
        self.add_recent(self.color)
        task["armed_from"] = now.isoformat(timespec="seconds")
        for k in ("last_fired", "last_warned"):
            task.pop(k, None)
        self.app.changed()
        self.close()

    def test(self):
        fields = self.collect()
        if fields:
            fields["test"] = True
            self.app.show_reminder(fields, dt.datetime.now())

    def delete(self):
        if messagebox.askyesno("Löschen", f"„{self.task['title']}“ wirklich löschen?", parent=self):
            self.app.delete_task(self.task)
            self.close()

    def close(self):
        self.app.editor = None
        self.destroy()
