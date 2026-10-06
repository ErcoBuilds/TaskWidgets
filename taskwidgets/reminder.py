"""Die Erinnerungs-Pop-ups unten rechts und der Dialog für eine eigene Schlummerzeit."""
import datetime as dt
import tkinter as tk
import winsound

from taskwidgets import config
from taskwidgets.config import *  # noqa: F401,F403
from taskwidgets.widgets import entry_style, label, text_button
from taskwidgets.platform_win import round_corners, show_themed

config.subscribe(globals())


class Reminder(tk.Toplevel):
    def __init__(self, app, task, when, pre=0):
        super().__init__(app.root)
        self.app, self.task, self.when, self.pre = app, task, when, pre
        self.color = task.get("color") or ACCENT
        self.flash_state = False
        self.rings_left = 0 if pre else 6

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=self.color)

        inner = tk.Frame(self, bg=BG, padx=px(16), pady=px(14))
        inner.pack(padx=2, pady=2)
        tk.Frame(inner, bg=BG, width=px(320), height=0).pack()

        top = tk.Frame(inner, bg=BG)
        top.pack(fill="x")
        head = f"VORWARNUNG · IN {pre} MIN" if pre else "ERINNERUNG"
        label(top, head, 8, fg=self.color, bold=True).pack(side="left")
        label(top, f"{when:%H:%M}", 9, fg=MUTED).pack(side="right")

        label(inner, task["title"], 14, bold=True, anchor="w", justify="left",
              wraplength=px(320)).pack(fill="x", pady=(px(4), 0))
        if task.get("note"):
            label(inner, task["note"], 10, fg=MUTED, anchor="w", justify="left",
                  wraplength=px(320)).pack(fill="x", pady=(px(2), 0))

        btns = tk.Frame(inner, bg=BG)
        btns.pack(fill="x", pady=(px(12), 0))
        text_button(btns, "Erledigt", self.done, bg=self.color, fg="#101114",
                    hover=FG, bold=True).pack(side="left")
        for mins in (5, 15, 30):
            text_button(btns, f"+{mins} Min", lambda m=mins: self.snooze(m),
                        padx=9).pack(side="left", padx=(px(6), 0))
        text_button(btns, "+", self.custom_snooze, bold=True, padx=10).pack(side="left", padx=(px(6), 0))

        self.after(50, lambda: round_corners(self))
        if self.rings_left:
            self.after(100, self.ring)
        self.after(600, self.flash)

    def ring(self):
        if not self.winfo_exists() or self.rings_left <= 0:
            return
        if self.app.settings["sound"] and self.task.get("sound", True):
            try:
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except RuntimeError:
                winsound.MessageBeep()
        self.rings_left -= 1
        self.after(5000, self.ring)

    def flash(self):
        if not self.winfo_exists():
            return
        self.flash_state = not self.flash_state
        self.configure(bg=BORDER if self.flash_state else self.color)
        self.after(600, self.flash)

    def done(self):
        if not self.task.get("test"):
            self.app.mark_done(self.task, self.when, log=True)
        self.close()

    def snooze(self, minutes):
        self.snooze_until(dt.datetime.now().replace(second=0, microsecond=0) + dt.timedelta(minutes=minutes))

    def snooze_until(self, at):
        self.app.snoozes.append({"task": self.task, "at": at})
        if not self.task.get("test"):
            self.app.log(self.task, "verschoben", f"bis {at:%H:%M}")
        self.close()

    def custom_snooze(self):
        SnoozeDialog(self)

    def close(self):
        if self in self.app.reminders:
            self.app.reminders.remove(self)
        self.destroy()
        self.app.layout_reminders()
        self.app.render_list(force=True)


class SnoozeDialog(tk.Toplevel):
    """Eigene Schlummerzeit: Minuten (z. B. 45) oder eine Uhrzeit (z. B. 14:30)."""

    def __init__(self, reminder):
        super().__init__(reminder)
        self.withdraw()
        self.reminder = reminder
        self.title("Schlummern")
        self.configure(bg=BG, padx=px(22), pady=px(18))
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.attributes("-toolwindow", True)

        label(self, "Erneut erinnern in …", 12, bold=True).pack(anchor="w")
        label(self, "Schnell wählen oder eigene Zeit eingeben", 9, fg=MUTED).pack(anchor="w", pady=(px(1), 0))

        qrow = tk.Frame(self, bg=BG)
        qrow.pack(anchor="w", pady=(px(12), px(6)))
        for mins in (5, 15, 30, 60):
            text_button(qrow, f"+{mins}", lambda m=mins: self.reminder.snooze(m),
                        padx=13).pack(side="left", padx=(0, px(6)))

        label(self, "Minuten (z. B. 45) oder Uhrzeit (z. B. 14:30)", 9, fg=MUTED).pack(anchor="w", pady=(px(6), px(3)))
        self.v = tk.StringVar(value="10")
        erow = tk.Frame(self, bg=BG)
        erow.pack(anchor="w", fill="x")
        entry = tk.Entry(erow, textvariable=self.v, width=9, justify="center",
                         **{**entry_style(), "font": (FONT, 14)})
        entry.pack(side="left", ipady=px(5))
        text_button(erow, "Schlummern", self.ok, bg=ACCENT, bold=True, padx=16).pack(side="left", padx=(px(8), 0))
        self.err = label(self, "", 9, fg=DANGER)
        self.err.pack(anchor="w", pady=(px(4), 0))
        brow = tk.Frame(self, bg=BG)
        brow.pack(fill="x", pady=(px(8), 0))
        text_button(brow, "Abbrechen", self.destroy, padx=16).pack(side="right")
        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = reminder.winfo_rootx() + reminder.winfo_width() - self.winfo_reqwidth()
        y = reminder.winfo_rooty() - self.winfo_reqheight() - px(40)
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        show_themed(self, self.reminder.app.effective_theme() == "dark")
        self.after(50, lambda: (self.focus_force(), entry.focus_set(), entry.select_range(0, "end")))

    def ok(self):
        txt = self.v.get().strip().replace(".", ":")
        now = dt.datetime.now().replace(second=0, microsecond=0)
        try:
            if ":" in txt:
                h, m = map(int, txt.split(":"))
                at = now.replace(hour=h, minute=m)
                if at <= now:
                    at += dt.timedelta(days=1)
            else:
                mins = int(txt)
                if not 1 <= mins <= 7 * 24 * 60:
                    raise ValueError
                at = now + dt.timedelta(minutes=mins)
        except ValueError:
            self.err.config(text="Bitte Minuten oder eine Uhrzeit wie 14:30 eingeben.")
            return
        self.reminder.snooze_until(at)
