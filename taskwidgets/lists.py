"""Übersichtsfenster „Alle Aufgaben" und „Verlauf"."""
import datetime as dt
import tkinter as tk
from tkinter import messagebox

from taskwidgets import config
from taskwidgets.config import *  # noqa: F401,F403
from taskwidgets.widgets import icon_button, label, text_button
from taskwidgets.recurrence import next_occurrence, repeat_text, single_per_day, task_times
from taskwidgets.storage import save_data
from taskwidgets.platform_win import show_themed

config.subscribe(globals())


class TaskList(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.withdraw()
        self.app = app
        self.title("Alle Aufgaben")
        self.configure(bg=BG, padx=px(16), pady=px(14))
        self.attributes("-topmost", bool(self.app.settings["topmost"]))
        self.attributes("-toolwindow", True)
        self.protocol("WM_DELETE_WINDOW", self.close)

        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", pady=(0, px(10)))
        label(head, "Alle Aufgaben", 14, bold=True).pack(side="left")
        text_button(head, "+ Neu", app.open_editor, bg=ACCENT, fg="#101114", hover=FG,
                    bold=True).pack(side="right")

        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, width=px(500))
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=BG)
        self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.config(scrollregion=self.canvas.bbox("all")))
        self.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-e.delta // 120, "units"))
        self.bind("<Escape>", lambda e: self.close())
        self.rebuild()
        self.update_idletasks()
        sw_, sh_ = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw_ - self.winfo_reqwidth()) // 2}+{(sh_ - self.winfo_reqheight()) // 4}")
        show_themed(self, self.app.effective_theme() == "dark")

    def rebuild(self):
        for w in self.body.winfo_children():
            w.destroy()
        now = dt.datetime.now()
        tasks = sorted(self.app.tasks, key=lambda t: (next_occurrence(t, now) or dt.datetime.max))
        if not tasks:
            label(self.body, "Noch keine Aufgaben angelegt.", 10, fg=MUTED).pack(anchor="w", pady=px(8))
        for t in tasks:
            nxt = next_occurrence(t, now)
            enabled = t.get("enabled", True)
            row = tk.Frame(self.body, bg=CARD)
            row.pack(fill="x", pady=(0, px(6)))
            tk.Frame(row, bg=t.get("color") or ACCENT, width=px(4)).pack(side="left", fill="y")
            var = tk.IntVar(value=int(enabled))
            tk.Checkbutton(row, variable=var, bg=CARD, activebackground=CARD, selectcolor=CARD,
                           fg=FG, command=lambda t=t, v=var: self.toggle(t, v)).pack(side="left", padx=(px(6), 0))
            times = task_times(t)
            label(row, times[0], 12, bg=CARD, bold=True, width=5).pack(side="left", padx=(px(2), px(8)))
            mid = tk.Frame(row, bg=CARD, pady=px(6))
            mid.pack(side="left", fill="x", expand=True)
            fg = FG if enabled and nxt else MUTED
            label(mid, t["title"], 10, fg=fg, bg=CARD, bold=True, anchor="w", width=28).pack(anchor="w")
            sub = repeat_text(t)
            if len(times) > 1 and single_per_day(t):
                sub = "auch " + ", ".join(times[1:]) + " · " + sub
            if not nxt:
                sub += " · vorbei"
            elif not enabled:
                sub += " · pausiert"
            label(mid, sub, 8, fg=MUTED, bg=CARD, anchor="w").pack(anchor="w")
            icon_button(row, "", lambda t=t: self.delete(t), bg=CARD, size=10).pack(side="right", padx=(0, px(6)))
            icon_button(row, "", lambda t=t: self.app.open_editor(t), bg=CARD, size=10).pack(side="right")
            if nxt:
                icon_button(row, "", lambda t=t: self.skip(t), bg=CARD, size=10).pack(side="right")
        self.update_idletasks()
        self.canvas.config(height=min(self.body.winfo_reqheight(), px(460)))

    def toggle(self, task, var):
        task["enabled"] = bool(var.get())
        task["armed_from"] = dt.datetime.now().isoformat(timespec="seconds")
        self.app.changed()

    def skip(self, task):
        self.app.skip_next(task)

    def delete(self, task):
        if messagebox.askyesno("Löschen", f"„{task['title']}“ wirklich löschen?", parent=self):
            self.app.delete_task(task)

    def close(self):
        self.app.task_list = None
        self.destroy()


ACTION_GLYPH = {"erledigt": ("", "#34C38F"), "übersprungen": ("", "#9093A0"),
                "verschoben": ("", "#F7B84B"), "erinnert": ("", "#5B9BFF")}


class History(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.withdraw()
        self.app = app
        self.title("Verlauf")
        self.configure(bg=BG, padx=px(16), pady=px(14))
        self.attributes("-topmost", bool(self.app.settings["topmost"]))
        self.attributes("-toolwindow", True)
        self.protocol("WM_DELETE_WINDOW", self.close)

        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", pady=(0, px(8)))
        label(head, "Verlauf", 14, bold=True).pack(side="left")
        label(head, "letzte 7 Tage", 9, fg=MUTED).pack(side="left", padx=(px(8), 0), pady=(px(6), 0))
        text_button(head, "Leeren", self.clear, fg=DANGER).pack(side="right")

        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, width=px(440))
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=BG)
        self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.config(scrollregion=self.canvas.bbox("all")))
        self.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-e.delta // 120, "units"))
        self.bind("<Escape>", lambda e: self.close())
        self.rebuild()
        self.update_idletasks()
        sw_, sh_ = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw_ - self.winfo_reqwidth()) // 2}+{(sh_ - self.winfo_reqheight()) // 4}")
        show_themed(self, self.app.effective_theme() == "dark")

    def rebuild(self):
        for w in self.body.winfo_children():
            w.destroy()
        entries = sorted(self.app.data["log"], key=lambda e: e["ts"], reverse=True)
        if not entries:
            label(self.body, "Noch keine Einträge.", 10, fg=MUTED).pack(anchor="w", pady=px(8))
        last_day = None
        for e in entries:
            ts = dt.datetime.fromisoformat(e["ts"])
            day = ts.date()
            if day != last_day:
                last_day = day
                diff = (dt.date.today() - day).days
                head = {0: "Heute", 1: "Gestern"}.get(diff, f"{DAYS_LONG[day.weekday()]}, {day:%d.%m.}")
                label(self.body, head, 10, fg=ACCENT, bold=True).pack(anchor="w", pady=(px(8), px(3)))
            row = tk.Frame(self.body, bg=BG)
            row.pack(fill="x", pady=px(1))
            label(row, ts.strftime("%H:%M"), 9, fg=MUTED, width=6, anchor="w").pack(side="left")
            glyph, col = ACTION_GLYPH.get(e["action"], ("", MUTED))
            tk.Label(row, text=glyph, font=(ICON_FONT, 9), fg=col, bg=BG).pack(side="left", padx=(0, px(6)))
            txt = e["title"]
            if e.get("extra"):
                txt += f"  ({e['extra']})"
            label(row, f"{e['action']}: {txt}", 9, anchor="w", justify="left",
                  wraplength=px(330)).pack(side="left", fill="x")
        self.update_idletasks()
        self.canvas.config(height=min(max(self.body.winfo_reqheight(), px(60)), px(460)))

    def clear(self):
        if messagebox.askyesno("Verlauf leeren", "Den gesamten Verlauf löschen?", parent=self):
            self.app.data["log"].clear()
            save_data(self.app.data)
            self.rebuild()

    def close(self):
        self.app.history = None
        self.destroy()
