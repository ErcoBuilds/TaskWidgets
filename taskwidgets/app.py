"""Das Haupt-Widget (Uhr + Aufgabenliste) und die zentrale App-Steuerung."""
import datetime as dt
import json
import os
import queue
import tkinter as tk
import tkinter.font as tkfont
import uuid
from tkinter import filedialog, messagebox

from taskwidgets import config
from taskwidgets.config import *  # noqa: F401,F403
from taskwidgets.storage import load_data, migrate_task, save_data
from taskwidgets.recurrence import (day_label, fmt_countdown, is_day_done, is_done,
                                    is_skipped, next_occurrence, occ_key, occurrences_on,
                                    repeat_text, single_per_day, task_times)
from taskwidgets.platform_win import (autostart_enabled, create_desktop_shortcut, resource,
                                      round_corners, set_autostart, set_dpi_awareness,
                                      windows_wants_light, work_area)
from taskwidgets.winapi import Tray, single_instance
from taskwidgets.widgets import icon_button, label, text_button
from taskwidgets.reminder import Reminder
from taskwidgets.editor import TaskEditor
from taskwidgets.lists import History, TaskList
from taskwidgets.settings_dialogs import SettingsDialog, SetupDialog

config.subscribe(globals())


class App:
    def __init__(self):
        self.data = load_data()
        self.tasks = self.data["tasks"]
        self.settings = self.data["settings"]
        for k, v in (("topmost", False), ("sound", True), ("alpha", 0.94), ("max_items", 6),
                     ("visible", True), ("theme", "dark")):
            self.settings.setdefault(k, v)
        self.settings.setdefault("quiet", {"mode": "off", "from": "22:00", "to": "07:00"})
        self.settings.setdefault("recent_colors", [])
        self.snoozes = []
        self.reminders = []
        self.pending = []           # im Ruhemodus zurückgehaltene Erinnerungen
        self.editor = None
        self.task_list = None
        self.history = None
        self.settings_win = None
        self._sig = None
        self._countdowns = []
        self.closing = False
        self._quiet_prev = False
        self._theme_check = 0
        self.visible = self.settings["visible"]
        self.events = queue.Queue()
        self.tray = Tray(self.events, lambda: {"visible": self.visible, "autostart": autostart_enabled()})

        self._applied = self.effective_theme()
        config.set_palette(self._applied)

        self.root = root = tk.Tk()
        config.set_scale(root.winfo_fpixels("1i") / 96)
        if config.ICON_FONT not in tkfont.families(root):
            config.set_icon_font("Segoe MDL2 Assets")
        root.title(APP_NAME)
        if os.path.exists(resource("icon.ico")):
            root.iconbitmap(default=resource("icon.ico"))
        root.overrideredirect(True)
        root.configure(bg=BORDER)
        root.attributes("-alpha", self.settings["alpha"])
        root.attributes("-topmost", self.settings["topmost"])

        self.v_topmost = tk.BooleanVar(value=self.settings["topmost"])
        self.v_sound = tk.BooleanVar(value=self.settings["sound"])
        self.v_alpha = tk.DoubleVar(value=self.settings["alpha"])
        self.v_autostart = tk.BooleanVar(value=autostart_enabled())
        self.v_theme = tk.StringVar(value=self.settings["theme"])
        self.v_quiet = tk.StringVar(value=self.settings["quiet"]["mode"])
        self.v_max_items = tk.IntVar(value=self.settings["max_items"])

        self.build()
        self.place()
        if not self.visible:
            root.withdraw()
        root.after(50, lambda: round_corners(root))
        self.tray.start()
        self.tick()
        self.poll_events()
        self.ensure_rendered()
        root.after(900, self.first_run_shortcut)

    # ---- Aufbau
    def build(self):
        self.inner = inner = tk.Frame(self.root, bg=BG, padx=px(14), pady=px(12))
        inner.pack(padx=1, pady=1, fill="both", expand=True)
        self.spacer = tk.Frame(inner, bg=BG, height=0)
        self.spacer.pack()
        inner.bind("<Motion>", self.edge_cursor)
        inner.bind("<ButtonPress-1>", self.edge_start)
        inner.bind("<B1-Motion>", self.edge_move)
        inner.bind("<ButtonRelease-1>", self.edge_end)

        head = tk.Frame(inner, bg=BG)
        head.pack(fill="x")
        clockbox = tk.Frame(head, bg=BG)
        clockbox.pack(side="left")
        self.clock = tk.Label(clockbox, font=("Segoe UI Light", 26), fg=FG, bg=BG)
        self.clock.pack(anchor="w")
        self.date_lbl = label(clockbox, "", 9, fg=MUTED)
        self.date_lbl.pack(anchor="w")

        btns = tk.Frame(head, bg=BG)
        btns.pack(side="right", anchor="n")
        icon_button(btns, "", self.show_menu).pack(side="right")
        icon_button(btns, "", self.open_history).pack(side="right")
        icon_button(btns, "", self.open_list).pack(side="right")
        icon_button(btns, "", self.open_editor).pack(side="right")

        for w in (head, clockbox, self.clock, self.date_lbl):
            w.bind("<ButtonPress-1>", self.drag_start)
            w.bind("<B1-Motion>", self.drag_move)
            w.bind("<ButtonRelease-1>", self.drag_end)
            w.configure(cursor="arrow")

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(px(10), px(8)))
        self.list_frame = tk.Frame(inner, bg=BG)
        self.list_frame.pack(fill="both", expand=True)

        self.build_menu()
        self.root.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))

    def build_menu(self):
        self.menu = m = tk.Menu(self.root, tearoff=False)
        m.add_command(label="Neue Aufgabe", command=self.open_editor)
        m.add_command(label="Alle Aufgaben", command=self.open_list)
        m.add_command(label="Verlauf", command=self.open_history)
        m.add_separator()
        m.add_command(label="Einstellungen …", command=self.open_settings)
        m.add_separator()
        m.add_command(label="Aufgaben exportieren …", command=self.export_tasks)
        m.add_command(label="Aufgaben importieren …", command=self.import_tasks)
        m.add_separator()
        m.add_command(label="Verknüpfung auf dem Desktop erstellen", command=self.make_desktop_shortcut)
        m.add_command(label="Größe zurücksetzen", command=self.reset_size)
        m.add_command(label="Widget ausblenden (bleibt im Infobereich)", command=lambda: self.set_visible(False))
        m.add_command(label="Beenden", command=self.quit)

    def place(self):
        left, top, right, _ = work_area()
        pos = self.settings.get("pos")
        if pos:
            x, y = pos
        else:
            x, y = right - self.width - px(24), top + px(24)
        self.apply_size(x, y)

    # ---- Design
    def effective_theme(self):
        t = self.settings["theme"]
        if t == "auto":
            return "light" if windows_wants_light() else "dark"
        return t

    def apply_theme(self):
        self.settings["theme"] = self.v_theme.get()
        save_data(self.data)
        self.retheme()

    def retheme(self):
        eff = self.effective_theme()
        config.set_palette(eff)
        self._applied = eff
        self.root.configure(bg=BORDER)
        self.inner.destroy()
        self.build()
        self.root.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self._sig = None
        self.apply_size()
        self.render_list(force=True)
        for win, cls in ((self.task_list, TaskList), (self.history, History)):
            if win is not None:
                win.destroy()
        if self.task_list is not None:
            self.task_list = TaskList(self)
        if self.history is not None:
            self.history = History(self)
        if self.settings_win is not None:
            self.settings_win._commit_quiet()
            self.settings_win._commit_max_items()
            self.settings_win.destroy()
            self.settings_win = SettingsDialog(self)

    # ---- Ruhemodus
    def apply_quiet(self):
        self.settings["quiet"]["mode"] = self.v_quiet.get()
        save_data(self.data)

    def quiet_now(self, now):
        q = self.settings["quiet"]
        if q["mode"] == "off":
            return False
        if q["mode"] == "on":
            return True
        fr = dt.datetime.strptime(q["from"], "%H:%M").time()
        to = dt.datetime.strptime(q["to"], "%H:%M").time()
        t = now.time()
        return fr <= t < to if fr <= to else (t >= fr or t < to)

    def flush_pending(self):
        for task, occ in self.pending:
            if task.get("test") or any(x is task for x in self.tasks):
                self.show_reminder(task, occ)
                self.log(task, "erinnert", "nachgeholt")
        self.pending.clear()

    # ---- Größe
    MIN_W, MIN_H = 260, 170
    EDGE_CURSORS = {"n": "size_ns", "s": "size_ns", "e": "size_we", "w": "size_we",
                    "ne": "size_ne_sw", "sw": "size_ne_sw", "nw": "size_nw_se", "se": "size_nw_se"}

    @property
    def width(self):
        return self.settings.get("width") or px(330)

    @property
    def fixed_height(self):
        return self.settings.get("height")

    @property
    def content_width(self):
        return self.width - 2 - 2 * px(14)

    def apply_size(self, x=None, y=None):
        self.spacer.config(width=self.content_width)
        if x is None:
            x, y = self.root.winfo_x(), self.root.winfo_y()
        if self.fixed_height:
            self.root.pack_propagate(False)
            self.root.geometry(f"{self.width}x{self.fixed_height}+{x}+{y}")
        else:
            self.root.pack_propagate(True)
            self.root.geometry("")
            self.root.geometry(f"+{x}+{y}")

    def reset_size(self):
        right = self.root.winfo_x() + self.root.winfo_width()
        self.settings.pop("width", None)
        self.settings.pop("height", None)
        self.settings["pos"] = [right - self.width, self.root.winfo_y()]
        self.apply_size(*self.settings["pos"])
        self.render_list(force=True)
        save_data(self.data)

    def edge_at(self, e):
        g = px(8)
        x, y = e.x_root - self.root.winfo_rootx(), e.y_root - self.root.winfo_rooty()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        return ("n" if y < g else "s" if y > h - g else "") + ("w" if x < g else "e" if x > w - g else "")

    def edge_cursor(self, e):
        self.inner.config(cursor=self.EDGE_CURSORS.get(self.edge_at(e), "arrow"))

    def edge_start(self, e):
        self._edge = self.edge_at(e)
        if not self._edge:
            return self.drag_start(e)
        r = self.root
        self._start = (e.x_root, e.y_root, r.winfo_x(), r.winfo_y(), r.winfo_width(), r.winfo_height())
        self._geom = self._start[2:]
        r.pack_propagate(False)

    def edge_move(self, e):
        if not self._edge:
            return self.drag_move(e)
        sx, sy, x, y, w, h = self._start
        dx, dy = e.x_root - sx, e.y_root - sy
        min_w, min_h = px(self.MIN_W), px(self.MIN_H)
        if "e" in self._edge:
            w = max(min_w, w + dx)
        if "w" in self._edge:
            nw = max(min_w, w - dx)
            x, w = x + w - nw, nw
        if "s" in self._edge:
            h = max(min_h, h + dy)
        if "n" in self._edge:
            nh = max(min_h, h - dy)
            y, h = y + h - nh, nh
        self._geom = (x, y, w, h)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def edge_end(self, e):
        if not self._edge:
            return self.drag_end(e)
        x, y, w, h = self._geom
        self.settings["width"] = w
        if "n" in self._edge or "s" in self._edge:
            self.settings["height"] = h
        self.settings["pos"] = [x, y]
        self.apply_size(x, y)
        self.render_list(force=True)
        save_data(self.data)

    # ---- Ziehen
    def drag_start(self, e):
        self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def drag_move(self, e):
        dx, dy = self._drag
        self.root.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")

    def drag_end(self, e):
        self.settings["pos"] = [self.root.winfo_x(), self.root.winfo_y()]
        save_data(self.data)

    # ---- Liste im Widget
    def upcoming(self, now):
        items = []
        today = now.date()
        for t in self.tasks:
            if not t.get("enabled", True):
                continue
            occs_today = occurrences_on(t, today)
            if occs_today and single_per_day(t) and all(is_done(t, o) for o in occs_today):
                items.append((dt.datetime.combine(today, dt.time(23, 59)), t, "done"))
                continue
            occ = next_occurrence(t, now)
            if occ:
                items.append((occ, t, None))
        for s in self.snoozes:
            items.append((s["at"], s["task"], s))
        items.sort(key=lambda i: (i[2] == "done", i[0]))
        return items[: 30 if self.fixed_height else self.settings["max_items"]]

    def render_list(self, force=False):
        now = dt.datetime.now()
        items = self.upcoming(now)
        # Struktur-Signatur OHNE Countdown: ändert sich nur der Countdown-Text (jede Minute),
        # werden die vorhandenen Labels in place aktualisiert statt alle Zeilen neu zu bauen
        # (Zerstören + Neuaufbau lässt das Fenster kurz schrumpfen = sichtbares Blinken).
        sig = tuple((id(t), occ, t["title"], t.get("color"), day_label(occ, now), occ.date() == now.date(),
                     kind if isinstance(kind, str) else id(kind)) for occ, t, kind in items)
        if not force and sig == self._sig:
            self.update_countdowns(now)
            return
        self._sig = sig
        self._countdowns = []
        for w in self.list_frame.winfo_children():
            w.destroy()
        if not items:
            label(self.list_frame, "Keine anstehenden Aufgaben.\nKlicke auf  +  um eine anzulegen.",
                  9, fg=MUTED, justify="left").pack(anchor="w", pady=px(4))
            self.tray.set_tip(f"{APP_NAME}\nKeine anstehenden Aufgaben")
        else:
            nxt = next((i for i in items if i[2] != "done"), None)
            if nxt:
                self.tray.set_tip(f"{APP_NAME}\nNächste: {day_label(nxt[0], now)} – {nxt[1]['title']}")
        for occ, t, kind in items:
            self.make_row(occ, t, kind, now)
        if self.fixed_height:
            self.fit_rows()

    def update_countdowns(self, now):
        """Nur Countdown-Text/-Farbe der vorhandenen Zeilen ändern; keine Layout-Änderung der Struktur."""
        for lbl, occ in getattr(self, "_countdowns", ()):
            try:
                soon = (occ - now) <= dt.timedelta(minutes=15)
                txt = fmt_countdown(occ, now)
                fg = ACCENT if soon else MUTED
                font = (FONT, 9, "bold" if soon else "normal")
                if lbl.cget("text") != txt:
                    lbl.config(text=txt)
                if str(lbl.cget("fg")) != fg:
                    lbl.config(fg=fg)
                if getattr(lbl, "_tw_bold", None) != soon:
                    lbl.config(font=font)
                    lbl._tw_bold = soon
            except tk.TclError:
                pass

    def ensure_rendered(self, attempts=12):
        """Nach Start/Einblenden einmal sauber zeichnen. Solange das Fenster seine echte
        Höhe noch nicht hat, in kurzen Abständen erneut versuchen (begrenzt, keine Schleife)."""
        if self.closing:
            return
        self.render_list(force=True)
        if self.visible and self.fixed_height and self.list_frame.winfo_height() <= 1 and attempts > 0:
            self.root.after(60, lambda: self.ensure_rendered(attempts - 1))

    def fit_rows(self):
        self.root.update_idletasks()
        avail = self.list_frame.winfo_height()
        if avail <= 1:  # Fenster ist noch nicht fertig aufgebaut – nichts verstecken
            return
        rows = self.list_frame.winfo_children()
        used = 0
        for i, row in enumerate(rows):
            used += row.winfo_reqheight() + px(6)
            if used - px(6) > avail:
                for r in rows[i:]:
                    r.pack_forget()
                hidden = len(rows) - i
                more = label(self.list_frame, f"+ {hidden} weitere", 8, fg=MUTED)
                if i > 0 and used - row.winfo_reqheight() - px(6) + more.winfo_reqheight() > avail:
                    rows[i - 1].pack_forget()
                    more.config(text=f"+ {hidden + 1} weitere")
                more.pack(anchor="w")
                break

    def end_snooze(self, snooze):
        if snooze in self.snoozes:
            self.snoozes.remove(snooze)
        self.render_list(force=True)

    def make_row(self, occ, task, kind, now):
        snoozed = isinstance(kind, dict)
        done = kind == "done"
        test = task.get("test")
        today = occ.date() == now.date()
        show_check = (not test) and (not snoozed) and today and single_per_day(task)

        row = tk.Frame(self.list_frame, bg=CARD, cursor="hand2")
        row.pack(fill="x", pady=(0, px(6)))
        tk.Frame(row, bg=task.get("color") or ACCENT, width=px(4)).pack(side="left", fill="y")

        check = None
        if show_check:
            glyph = "" if done else ""
            check = icon_button(row, glyph, lambda: self.toggle_done(task, occ, whole_day=done),
                                bg=CARD, fg=(task.get("color") or ACCENT) if done else MUTED, size=12)
            check.pack(side="left", padx=(px(4), 0))

        soon = (occ - now) <= dt.timedelta(minutes=15)
        if snoozed:
            icon_button(row, "", lambda: self.end_snooze(kind), bg=CARD, size=10).pack(
                side="right", padx=(0, px(4)))
        right_txt = "erledigt" if done else fmt_countdown(occ, now)
        right = label(row, right_txt, 9, fg=MUTED if done else (ACCENT if soon else MUTED), bg=CARD,
                      padx=px(10) if not snoozed else px(4), bold=soon and not done)
        right.pack(side="right")
        right._tw_bold = soon and not done
        if not done:
            self._countdowns.append((right, occ))

        body = tk.Frame(row, bg=CARD, padx=px(8), pady=px(7))
        body.pack(side="left", fill="both", expand=True)
        style = "bold overstrike" if done else "bold"
        title = tk.Label(body, text=task["title"], font=(FONT, 10, style), bg=CARD,
                         fg=MUTED if done else FG, anchor="w", justify="left",
                         wraplength=max(px(110), self.content_width - px(140)))
        title.pack(fill="x")
        if done:
            sub_txt = "heute erledigt"
        elif snoozed:
            sub_txt = f"{day_label(occ, now)} · geschlummert"
        else:
            n = len(task_times(task))
            extra = f" · {n}×/Tag" if n > 1 and single_per_day(task) else ""
            sub_txt = f"{day_label(occ, now)} · {repeat_text(task)}{extra}"
        sub = label(body, sub_txt, 8, fg=MUTED, bg=CARD, anchor="w")
        sub.pack(fill="x")

        parts = [row, body, title, sub, right]

        def enter(_):
            for p in parts:
                p.config(bg=HOVER)
            if check:
                check.config(bg=HOVER)

        def leave(_):
            w = self.root.winfo_containing(*self.root.winfo_pointerxy())
            if w is not None and str(w).startswith(str(row)):
                return
            for p in parts:
                p.config(bg=CARD)
            if check:
                check.config(bg=CARD)

        if not test:
            def click(_):
                self.open_editor(task)
            menu = self.row_menu(task)

            def popup(e):
                menu.tk_popup(e.x_root, e.y_root)
        elif snoozed:
            def click(_):
                self.end_snooze(kind)
                self.show_reminder(task, dt.datetime.now())
            popup = None
        else:
            click = popup = None

        for p in parts:
            p.bind("<Enter>", enter)
            p.bind("<Leave>", leave)
            if click:
                p.bind("<Button-1>", click)
            if popup:
                p.bind("<Button-3>", popup)

    def row_menu(self, task):
        m = tk.Menu(self.root, tearoff=False)
        m.add_command(label="Bearbeiten", command=lambda: self.open_editor(task))
        m.add_command(label="Nächsten Termin überspringen", command=lambda: self.skip_next(task))
        today = dt.date.today()
        if is_day_done(task, today):
            m.add_command(label="Heute doch nicht erledigt",
                          command=lambda: self.clear_done_day(task, today))
        m.add_separator()
        m.add_command(label="Löschen", command=lambda: self.confirm_delete(task))
        return m

    # ---- Aktionen
    def toggle_done(self, task, occ, whole_day=False):
        if whole_day:
            self.clear_done_day(task, occ.date())
        elif is_done(task, occ):
            self.set_undone(task, occ)
        else:
            self.mark_done(task, occ, log=True)

    def set_undone(self, task, occ):
        """Einen einzelnen abgehakten Termin wieder öffnen."""
        key, d = occ_key(occ), occ.date().isoformat()
        task["done_days"] = [k for k in (task.get("done_days") or []) if k not in (key, d)]
        tid = task.get("id")
        self.data["log"] = [e for e in self.data["log"] if not (
            e.get("action") == "erledigt" and e.get("task_id") == tid and e.get("day") in (key, d))]
        self._after_state_change()

    def clear_done_day(self, task, day):
        """Alle an diesem Tag abgehakten Termine der Aufgabe wieder öffnen."""
        diso = day.isoformat()
        task["done_days"] = [k for k in (task.get("done_days") or []) if not str(k).startswith(diso)]
        tid = task.get("id")
        self.data["log"] = [e for e in self.data["log"] if not (
            e.get("action") == "erledigt" and e.get("task_id") == tid
            and str(e.get("day") or "").startswith(diso))]
        self._after_state_change()

    def _after_state_change(self):
        save_data(self.data)
        if self.history is not None:
            self.history.rebuild()
        self.render_list(force=True)
        if self.task_list is not None:
            self.task_list.rebuild()

    def mark_done(self, task, occ, log=False):
        key = occ_key(occ)
        dd = task.setdefault("done_days", [])
        if key not in dd:
            dd.append(key)
        # nur die Erinnerung(en) dieses Termins schließen (andere Uhrzeiten bleiben offen)
        for r in [r for r in self.reminders if r.task is task and occ_key(r.when) == key]:
            r.destroy()
            self.reminders.remove(r)
        self.layout_reminders()
        if log:
            # alten „erledigt“-Eintrag desselben Termins ersetzen (kein Doppeln beim erneuten Haken)
            tid = task.get("id")
            self.data["log"] = [e for e in self.data["log"] if not (
                e.get("action") == "erledigt" and e.get("task_id") == tid and e.get("day") == key)]
            self.log(task, "erledigt", day=key)
        self.changed()

    def skip_next(self, task):
        occ = next_occurrence(task, dt.datetime.now())
        if not occ:
            return
        key = occ_key(occ)
        sk = task.setdefault("skip_days", [])
        if key not in sk:
            sk.append(key)
        self.log(task, "übersprungen", occ.strftime("%d.%m. %H:%M"))
        self.changed()

    def confirm_delete(self, task):
        if messagebox.askyesno("Löschen", f"„{task['title']}“ wirklich löschen?"):
            self.delete_task(task)

    def log(self, task, action, extra="", day=None):
        self.data["log"].append({"ts": dt.datetime.now().isoformat(timespec="seconds"),
                                 "title": task["title"], "color": task.get("color"),
                                 "action": action, "extra": extra,
                                 "task_id": task.get("id"), "day": day})
        cutoff = (dt.datetime.now() - dt.timedelta(days=LOG_DAYS)).isoformat()
        self.data["log"] = [e for e in self.data["log"] if e["ts"] >= cutoff]
        save_data(self.data)
        if self.history is not None:
            self.history.rebuild()

    # ---- Export / Import
    def export_tasks(self):
        self.root.attributes("-topmost", False)
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Aufgaben exportieren", defaultextension=".json",
            initialfile="TaskWidgets-Aufgaben.json", filetypes=[("TaskWidgets-Datei", "*.json")])
        self.root.attributes("-topmost", self.settings["topmost"])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"app": APP_NAME, "version": 2, "tasks": self.tasks}, f,
                          ensure_ascii=False, indent=2)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Export fehlgeschlagen:\n{e}")
            return
        messagebox.showinfo(APP_NAME, f"{len(self.tasks)} Aufgabe(n) exportiert.")

    def import_tasks(self):
        self.root.attributes("-topmost", False)
        path = filedialog.askopenfilename(parent=self.root, title="Aufgaben importieren",
                                          filetypes=[("TaskWidgets-Datei", "*.json"), ("Alle Dateien", "*.*")])
        self.root.attributes("-topmost", self.settings["topmost"])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            imported = data["tasks"] if isinstance(data, dict) else data
            if not isinstance(imported, list):
                raise ValueError
        except (OSError, ValueError, KeyError):
            messagebox.showerror(APP_NAME, "Die Datei konnte nicht gelesen werden.")
            return
        if not imported:
            messagebox.showinfo(APP_NAME, "Die Datei enthält keine Aufgaben.")
            return
        if not messagebox.askyesno(APP_NAME, f"{len(imported)} Aufgabe(n) hinzufügen?"):
            return
        now = dt.datetime.now().isoformat(timespec="seconds")
        for t in imported:
            if not isinstance(t, dict) or "title" not in t:
                continue
            t["id"] = uuid.uuid4().hex
            t.setdefault("enabled", True)
            t["armed_from"] = now
            for k in ("last_fired", "last_warned"):
                t.pop(k, None)
            migrate_task(t)
            self.tasks.append(t)
        self.changed()
        messagebox.showinfo(APP_NAME, "Import abgeschlossen.")

    # ---- Takt & Erinnerungen
    def tick(self):
        now = dt.datetime.now()
        ct = now.strftime("%H:%M")
        if self.clock.cget("text") != ct:
            self.clock.config(text=ct)
        dtxt = f"{DAYS_LONG[now.weekday()]}, {now.day}. {MONTHS[now.month - 1]}"
        if self.date_lbl.cget("text") != dtxt:
            self.date_lbl.config(text=dtxt)
        self._theme_check += 1
        if self.settings["theme"] == "auto" and self._theme_check % 3 == 0:
            if self.effective_theme() != self._applied:
                self.retheme()
        self.check_due(now)
        self.render_list()
        self.root.after(1000 - now.microsecond // 1000 + 10, self.tick)

    def check_due(self, now):
        quiet = self.quiet_now(now)
        if self._quiet_prev and not quiet:
            self.flush_pending()
        self._quiet_prev = quiet
        changed = False
        for t in self.tasks:
            if not t.get("enabled", True):
                continue
            armed = dt.datetime.fromisoformat(t["armed_from"]) if t.get("armed_from") else dt.datetime.min
            warn = t.get("warn", 0)
            for day in (now.date() - dt.timedelta(days=1), now.date()):
                for occ in occurrences_on(t, day):
                    if occ < armed:
                        continue
                    if is_skipped(t, occ) or is_done(t, occ):
                        continue
                    key = occ_key(occ)
                    if occ <= now < occ + GRACE and key > t.get("last_fired", ""):
                        t["last_fired"] = key
                        changed = True
                        if quiet:
                            self.pending.append((t, occ))
                        else:
                            self.show_reminder(t, occ)
                            self.log(t, "erinnert")
                    if warn and not quiet:
                        wat = occ - dt.timedelta(minutes=warn)
                        if wat >= armed and wat <= now < min(occ, wat + GRACE) \
                                and key > t.get("last_warned", ""):
                            t["last_warned"] = key
                            changed = True
                            self.show_reminder(t, occ, pre=warn)
        for s in [s for s in self.snoozes if s["at"] <= now]:
            self.snoozes.remove(s)
            t = s["task"]
            if t.get("test") or any(x is t for x in self.tasks):
                self.show_reminder(t, s["at"])
        if changed:
            save_data(self.data)

    def show_reminder(self, task, when, pre=0):
        if any(r.task is task and r.pre == pre for r in self.reminders):
            return
        self.reminders.append(Reminder(self, task, when, pre=pre))
        self.layout_reminders()

    def layout_reminders(self):
        _, _, right, bottom = work_area()
        y = bottom - px(16)
        for r in self.reminders:
            if not r.winfo_exists():
                continue
            r.update_idletasks()
            y -= r.winfo_reqheight()
            r.geometry(f"+{right - r.winfo_reqwidth() - px(16)}+{y}")
            y -= px(10)

    # ---- Fenster & Einstellungen
    def open_editor(self, task=None):
        if self.editor is not None:
            self.editor.close()
        self.editor = TaskEditor(self, task)

    def open_list(self):
        if self.task_list is None:
            self.task_list = TaskList(self)
        else:
            self.task_list.lift()
            self.task_list.focus_force()

    def open_history(self):
        if self.history is None:
            self.history = History(self)
        else:
            self.history.lift()
            self.history.focus_force()

    def open_settings(self):
        if self.settings_win is None:
            self.settings_win = SettingsDialog(self)
        else:
            self.settings_win.lift()
            self.settings_win.focus_force()

    def show_menu(self):
        x = self.root.winfo_rootx() + self.root.winfo_width() - px(10)
        y = self.root.winfo_rooty() + px(40)
        self.menu.tk_popup(x, y)

    def delete_task(self, task):
        self.tasks[:] = [t for t in self.tasks if t is not task]
        self.snoozes[:] = [s for s in self.snoozes if s["task"] is not task]
        self.changed()

    def changed(self):
        save_data(self.data)
        self.render_list(force=True)
        if self.task_list is not None:
            self.task_list.rebuild()

    def apply_settings(self):
        self.settings["topmost"] = self.v_topmost.get()
        self.settings["sound"] = self.v_sound.get()
        self.settings["alpha"] = self.v_alpha.get()
        self.root.attributes("-topmost", self.settings["topmost"])
        self.root.attributes("-alpha", self.settings["alpha"])
        save_data(self.data)

    def toggle_autostart(self):
        try:
            set_autostart(self.v_autostart.get())
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Autostart konnte nicht geändert werden:\n{e}")
        self.v_autostart.set(autostart_enabled())

    def make_desktop_shortcut(self, announce=True):
        try:
            create_desktop_shortcut()
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Verknüpfung konnte nicht erstellt werden:\n{e}")
            return
        if announce:
            messagebox.showinfo(APP_NAME, "Verknüpfung auf dem Desktop erstellt.")

    def first_run_shortcut(self):
        """Beim ersten Start den Einrichtungs-Assistenten zeigen."""
        if self.closing or self.settings.get("setup_done"):
            return
        SetupDialog(self)

    # ---- Infobereich
    def poll_events(self):
        if self.closing:
            return
        actions = {"toggle": lambda: self.set_visible(not self.visible),
                   "show": lambda: self.set_visible(True),
                   "new": self.open_editor, "list": self.open_list, "history": self.open_history,
                   "autostart": self.tray_autostart, "quit": self.quit}
        try:
            while True:
                actions[self.events.get_nowait()]()
                if self.closing:
                    return
        except queue.Empty:
            pass
        self.root.after(150, self.poll_events)

    def set_visible(self, visible):
        self.visible = self.settings["visible"] = visible
        if visible:
            self.root.deiconify()
            self.root.attributes("-topmost", self.settings["topmost"])
            self.root.lift()
            self.root.after(50, lambda: round_corners(self.root))
            self.ensure_rendered()
        else:
            self.root.withdraw()
        save_data(self.data)

    def tray_autostart(self):
        self.v_autostart.set(not autostart_enabled())
        self.toggle_autostart()

    def quit(self):
        self.closing = True
        save_data(self.data)
        self.tray.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    set_dpi_awareness()
    single_instance()
    App().run()
