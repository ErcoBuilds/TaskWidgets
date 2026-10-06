"""Ruhezeiten-Dialog, gebündeltes Einstellungsfenster und der Erststart-Assistent."""
import tkinter as tk
from tkinter import messagebox

from taskwidgets import config
from taskwidgets.config import *  # noqa: F401,F403
from taskwidgets.widgets import (_spin_style, label, section_header, segmented,
                                 slider, stepper, text_button, toggle)
from taskwidgets.storage import save_data
from taskwidgets.platform_win import autostart_enabled, show_themed, windows_wants_light

config.subscribe(globals())


class QuietDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Ruhezeiten")
        self.configure(bg=BG, padx=px(20), pady=px(16))
        self.resizable(False, False)
        self.attributes("-topmost", bool(self.app.settings["topmost"]))
        self.attributes("-toolwindow", True)
        q = app.settings["quiet"]
        fh, fm = q["from"].split(":")
        th, tm = q["to"].split(":")
        self.v_fh, self.v_fm, self.v_th, self.v_tm = (tk.StringVar(value=x) for x in (fh, fm, th, tm))

        label(self, "Im Ruhemodus nach Zeitplan sind in diesem Zeitraum", 10).pack(anchor="w")
        label(self, "keine Töne und Pop-ups. Verpasstes kommt danach gesammelt.", 9, fg=MUTED).pack(anchor="w")
        row = tk.Frame(self, bg=BG)
        row.pack(anchor="w", pady=(px(12), 0))
        label(row, "von", 11).pack(side="left", padx=(0, px(6)))
        self._spin(row, self.v_fh, self.v_fm, fh, fm)
        label(row, "bis", 11).pack(side="left", padx=(px(10), px(6)))
        self._spin(row, self.v_th, self.v_tm, th, tm)
        brow = tk.Frame(self, bg=BG)
        brow.pack(fill="x", pady=(px(16), 0))
        text_button(brow, "Speichern", self.ok, bg=ACCENT, fg="#101114", hover=FG, bold=True).pack(side="right")
        text_button(brow, "Abbrechen", self.destroy).pack(side="right", padx=(0, px(6)))
        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        sw_, sh_ = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw_ - self.winfo_reqwidth()) // 2}+{(sh_ - self.winfo_reqheight()) // 3}")

    def _spin(self, parent, vh, vm, h, m):
        kw = dict(_spin_style(), width=3, justify="center", font=(FONT, 13), wrap=True)
        tk.Spinbox(parent, from_=0, to=23, textvariable=vh, **kw).pack(side="left", ipady=px(2))
        label(parent, ":", 13).pack(side="left")
        tk.Spinbox(parent, from_=0, to=59, textvariable=vm, **kw).pack(side="left", ipady=px(2))
        vh.set(h)
        vm.set(m)

    def ok(self):
        try:
            frm = f"{int(self.v_fh.get()):02d}:{int(self.v_fm.get()):02d}"
            to = f"{int(self.v_th.get()):02d}:{int(self.v_tm.get()):02d}"
        except ValueError:
            messagebox.showerror("Ungültig", "Bitte gültige Uhrzeiten eingeben.", parent=self)
            return
        self.app.settings["quiet"]["from"] = frm
        self.app.settings["quiet"]["to"] = to
        if self.app.settings["quiet"]["mode"] == "off":
            self.app.settings["quiet"]["mode"] = "schedule"
            self.app.v_quiet.set("schedule")
        save_data(self.app.data)
        self.destroy()


class SettingsDialog(tk.Toplevel):
    """Gebündeltes Einstellungsfenster. Alle Werte greifen sofort und werden gespeichert."""

    def __init__(self, app):
        super().__init__(app.root)
        self.withdraw()
        self.app = app
        self.title("Einstellungen")
        self.configure(bg=BG, padx=px(24), pady=px(20))
        self.resizable(False, False)
        self.attributes("-topmost", bool(self.app.settings["topmost"]))
        self.attributes("-toolwindow", True)
        self.protocol("WM_DELETE_WINDOW", self.close)

        q = app.settings["quiet"]
        fh, fm = q["from"].split(":")
        th, tm = q["to"].split(":")
        self.v_fh, self.v_fm, self.v_th, self.v_tm = (tk.StringVar(value=x) for x in (fh, fm, th, tm))

        def head(text, first=False):
            section_header(self, text).pack(anchor="w", pady=(px(2) if first else px(16), px(8)))

        def toggle_row(text, var, cmd):
            r = tk.Frame(self, bg=BG)
            r.pack(fill="x", pady=px(5))
            label(r, text, 11).pack(side="left")
            sw = toggle(r, var, cmd)
            sw.pack(side="right")
            return sw

        # ---- Design
        head("Design", first=True)
        segmented(self, app.v_theme, (("dark", "Dunkel"), ("light", "Hell"), ("auto", "Auto")),
                  app.apply_theme).pack(anchor="w")

        # ---- Erinnerungen
        head("Erinnerungen")
        toggle_row("Ton bei Erinnerung", app.v_sound, app.apply_settings)
        label(self, "Ruhemodus", 11).pack(anchor="w", pady=(px(8), px(5)))
        segmented(self, app.v_quiet, (("off", "Aus"), ("on", "An"), ("schedule", "Nach Zeitplan")),
                  app.apply_quiet).pack(anchor="w")
        qrow = tk.Frame(self, bg=BG)
        qrow.pack(anchor="w", pady=(px(10), 0))
        label(qrow, "Ruhezeit  von", 11, fg=MUTED).pack(side="left", padx=(0, px(8)))
        self._spin(qrow, self.v_fh, self.v_fm)
        label(qrow, "bis", 11, fg=MUTED).pack(side="left", padx=(px(12), px(8)))
        self._spin(qrow, self.v_th, self.v_tm)

        # ---- Darstellung
        head("Darstellung")
        toggle_row("Immer im Vordergrund", app.v_topmost, app.apply_settings)
        arow = tk.Frame(self, bg=BG)
        arow.pack(fill="x", pady=(px(8), px(2)))
        label(arow, "Deckkraft", 11).pack(side="left")
        self.alpha_lbl = label(arow, f"{int(round(app.v_alpha.get() * 100))} %", 11, fg=ACCENT)
        self.alpha_lbl.pack(side="right")
        self.v_alpha_pct = tk.IntVar(value=int(round(app.v_alpha.get() * 100)))
        self.alpha_scale = slider(self, self.v_alpha_pct, 60, 100, command=self.on_alpha, width=260)
        self.alpha_scale.pack(fill="x", pady=(px(4), 0))

        # ---- Liste
        head("Liste")
        mrow = tk.Frame(self, bg=BG)
        mrow.pack(fill="x", pady=px(3))
        label(mrow, "Max. Aufgaben im Widget", 11).pack(side="left")
        stepper(mrow, app.v_max_items, 1, 20, command=self.on_max_items).pack(side="right")

        # ---- System
        head("System")

        def auto_cmd():
            app.toggle_autostart()
            sw_auto.draw()
        sw_auto = toggle_row("Mit Windows starten", app.v_autostart, auto_cmd)

        brow = tk.Frame(self, bg=BG)
        brow.pack(fill="x", pady=(px(22), 0))
        text_button(brow, "Schließen", self.close, bg=ACCENT, bold=True, padx=20).pack(side="right")
        self.bind("<Escape>", lambda e: self.close())
        self.update_idletasks()
        sw_, sh_ = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw_ - self.winfo_reqwidth()) // 2}+{(sh_ - self.winfo_reqheight()) // 3}")
        show_themed(self, self.app.effective_theme() == "dark")

    def _spin(self, parent, vh, vm):
        stepper(parent, vh, 0, 23, wrap=True, pad=True, command=self.on_quiet).pack(side="left")
        label(parent, ":", 12).pack(side="left", padx=px(2))
        stepper(parent, vm, 0, 59, wrap=True, pad=True, command=self.on_quiet).pack(side="left")

    def on_alpha(self, pct):
        pct = int(pct)
        self.app.v_alpha.set(pct / 100)
        self.alpha_lbl.config(text=f"{pct} %")
        self.app.apply_settings()

    def on_quiet(self):
        self._commit_quiet()

    def on_max_items(self):
        self._commit_max_items()

    def _commit_quiet(self):
        try:
            frm = f"{int(self.v_fh.get()):02d}:{int(self.v_fm.get()):02d}"
            to = f"{int(self.v_th.get()):02d}:{int(self.v_tm.get()):02d}"
        except ValueError:
            return
        self.app.settings["quiet"]["from"] = frm
        self.app.settings["quiet"]["to"] = to
        save_data(self.app.data)

    def _commit_max_items(self):
        try:
            n = max(1, min(20, int(self.app.v_max_items.get())))
        except (ValueError, tk.TclError):
            return
        if n != self.app.v_max_items.get():
            self.app.v_max_items.set(n)
        self.app.settings["max_items"] = n
        self.app.render_list(force=True)
        save_data(self.app.data)

    def close(self):
        self._commit_quiet()
        self._commit_max_items()
        self.app.settings_win = None
        self.destroy()


class SetupDialog(tk.Toplevel):
    """Einrichtungs-Assistent beim ersten Start."""

    def __init__(self, app):
        super().__init__(app.root)
        self.withdraw()
        self.app = app
        self.title("Willkommen")
        self.configure(bg=BG, padx=px(24), pady=px(20))
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.attributes("-toolwindow", True)
        self.protocol("WM_DELETE_WINDOW", self.finish)

        self.v_short = tk.BooleanVar(value=True)
        self.v_auto = tk.BooleanVar(value=True)
        self.v_top = tk.BooleanVar(value=bool(app.settings.get("topmost")))
        self.v_theme = tk.StringVar(value=app.settings.get("theme", "dark"))

        label(self, "Willkommen bei TaskWidgets", 14, bold=True).pack(anchor="w")
        label(self, "Kurz einrichten – später jederzeit in den Einstellungen änderbar.",
              9, fg=MUTED).pack(anchor="w", pady=(px(2), 0))

        def row(text, var):
            r = tk.Frame(self, bg=BG)
            r.pack(fill="x", pady=px(7))
            label(r, text, 11).pack(side="left")
            toggle(r, var).pack(side="right")

        section_header(self, "Start").pack(anchor="w", pady=(px(16), px(6)))
        row("Verknüpfung auf dem Desktop erstellen", self.v_short)
        row("Mit Windows öffnen", self.v_auto)
        row("Immer im Vordergrund", self.v_top)

        section_header(self, "Design").pack(anchor="w", pady=(px(16), px(6)))
        segmented(self, self.v_theme, (("dark", "Dunkel"), ("light", "Hell"), ("auto", "Auto"))).pack(anchor="w")

        brow = tk.Frame(self, bg=BG)
        brow.pack(fill="x", pady=(px(22), 0))
        text_button(brow, "Fertig", self.finish, bg=ACCENT, bold=True, padx=22).pack(side="right")
        self.bind("<Return>", lambda e: self.finish())

        self.update_idletasks()
        sw_, sh_ = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw_ - self.winfo_reqwidth()) // 2}+{(sh_ - self.winfo_reqheight()) // 3}")
        show_themed(self, (self.v_theme.get() == "dark") or
                    (self.v_theme.get() == "auto" and not windows_wants_light()))

    def finish(self):
        app = self.app
        app.settings["setup_done"] = True
        # Vordergrund
        app.settings["topmost"] = bool(self.v_top.get())
        app.v_topmost.set(app.settings["topmost"])
        app.root.attributes("-topmost", app.settings["topmost"])
        # Autostart
        if bool(self.v_auto.get()) != autostart_enabled():
            app.v_autostart.set(bool(self.v_auto.get()))
            app.toggle_autostart()
        # Verknüpfung
        if self.v_short.get():
            app.make_desktop_shortcut(announce=False)
        # Design
        theme = self.v_theme.get()
        changed = theme != app.settings.get("theme")
        app.settings["theme"] = theme
        app.v_theme.set(theme)
        save_data(app.data)
        self.destroy()
        if changed:
            app.retheme()
