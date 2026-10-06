"""Eigener Farbwähler im Programmdesign: HSV-Feld, Farbtonleiste, Hex-Eingabe, Pipette."""
import colorsys
import ctypes
import ctypes.wintypes as wintypes
import tkinter as tk

from taskwidgets import config
from taskwidgets.config import *  # noqa: F401,F403
from taskwidgets.widgets import entry_style, text_button
from taskwidgets.platform_win import pipette_cursor, show_themed

config.subscribe(globals())


class ColorPicker(tk.Toplevel):
    """Eigener Farbwähler im Programmdesign: HSV-Feld + Farbtonleiste + Hex-Eingabe."""

    def __init__(self, editor, start, on_ok):
        super().__init__(editor)
        self.withdraw()
        self.app = editor.app
        self.on_ok = on_ok
        self.start = start if (isinstance(start, str) and start.startswith("#") and len(start) == 7) else ACCENT
        self.title("Farbe wählen")
        self.configure(bg=BG, padx=px(18), pady=px(16))
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.attributes("-toolwindow", True)

        r, g, b = (int(self.start[i:i + 2], 16) / 255 for i in (1, 3, 5))
        self.h, self.s, self.v = colorsys.rgb_to_hsv(r, g, b)

        self.Z = 2
        self.SV = (px(176) // self.Z) * self.Z
        self.base = self.SV // self.Z
        self.barw = px(22)

        top = tk.Frame(self, bg=BG)
        top.pack()
        self.sv = tk.Canvas(top, width=self.SV, height=self.SV, highlightthickness=0, bd=0, cursor="crosshair")
        self.sv.pack(side="left")
        self.bar = tk.Canvas(top, width=self.barw, height=self.SV, highlightthickness=0, bd=0, cursor="hand2")
        self.bar.pack(side="left", padx=(px(12), 0))
        self.sv_item = self.sv.create_image(0, 0, anchor="nw")
        self.sv_mark = self.sv.create_oval(0, 0, 0, 0, outline="#ffffff", width=2)
        self.bar_item = self.bar.create_image(0, 0, anchor="nw")
        self.bar_mark = self.bar.create_rectangle(0, 0, 0, 0, outline="#ffffff", width=2)
        self.sv.bind("<Button-1>", self._sv_pick)
        self.sv.bind("<B1-Motion>", self._sv_pick)
        self.bar.bind("<Button-1>", self._bar_pick)
        self.bar.bind("<B1-Motion>", self._bar_pick)

        prow = tk.Frame(self, bg=BG)
        prow.pack(fill="x", pady=(px(14), 0))
        self.new_sw = tk.Label(prow, bg=self.start, width=5, height=2, highlightthickness=1,
                               highlightbackground=BORDER)
        self.new_sw.pack(side="left")
        text_button(prow, "Pipette", self._eyedrop, padx=12).pack(side="left", padx=(px(10), 0))
        self.v_hex = tk.StringVar(value=self.start.upper())
        he = tk.Entry(prow, textvariable=self.v_hex, width=9, justify="center",
                      **{**entry_style(), "font": (FONT, 12)})
        he.pack(side="right", ipady=px(3))
        he.bind("<Return>", lambda e: self._from_hex())
        he.bind("<FocusOut>", lambda e: self._from_hex())

        brow = tk.Frame(self, bg=BG)
        brow.pack(fill="x", pady=(px(14), 0))
        text_button(brow, "OK", self._ok, bg=ACCENT, bold=True, padx=20).pack(side="right")
        text_button(brow, "Abbrechen", self.destroy, padx=16).pack(side="right", padx=(0, px(6)))
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Destroy>", lambda e: (e.widget is self) and self._restore_cursor())

        self._render_bar()
        self._render_sv()
        self._update()
        self.update_idletasks()
        self.geometry(f"+{editor.winfo_rootx() + px(30)}+{editor.winfo_rooty() + px(30)}")
        show_themed(self, self.app.effective_theme() == "dark")

    @staticmethod
    def _rgb_hex(r, g, b):
        return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))

    def _hex(self):
        return self._rgb_hex(*colorsys.hsv_to_rgb(self.h, self.s, self.v))

    def _render_bar(self):
        n = self.base
        cells = []
        for y in range(n):
            r, g, b = colorsys.hsv_to_rgb(y / (n - 1), 1, 1)
            cells.append("{%s}" % self._rgb_hex(r, g, b))
        img = tk.PhotoImage(width=1, height=n)
        img.put(" ".join(cells))
        self._bar_ref = img.zoom(self.barw, self.Z)
        self.bar.itemconfig(self.bar_item, image=self._bar_ref)

    def _render_sv(self):
        n = self.base
        rows = []
        for yy in range(n):
            v = 1 - yy / (n - 1)
            row = [self._rgb_hex(*colorsys.hsv_to_rgb(self.h, xx / (n - 1), v)) for xx in range(n)]
            rows.append("{" + " ".join(row) + "}")
        img = tk.PhotoImage(width=n, height=n)
        img.put(" ".join(rows))
        self._sv_ref = img.zoom(self.Z, self.Z)
        self.sv.itemconfig(self.sv_item, image=self._sv_ref)

    def _update(self):
        col = self._hex()
        self.new_sw.config(bg=col)
        self.v_hex.set(col.upper())
        sx, sy = self.s * self.SV, (1 - self.v) * self.SV
        rad = px(6)
        self.sv.coords(self.sv_mark, sx - rad, sy - rad, sx + rad, sy + rad)
        by = self.h * self.SV
        self.bar.coords(self.bar_mark, px(1), by - px(2), self.barw - px(1), by + px(2))

    def _sv_pick(self, e):
        self.s = max(0.0, min(1.0, e.x / self.SV))
        self.v = max(0.0, min(1.0, 1 - e.y / self.SV))
        self._update()

    def _bar_pick(self, e):
        self.h = max(0.0, min(1.0, e.y / self.SV))
        self._render_sv()
        self._update()

    def _from_hex(self):
        t = self.v_hex.get().strip()
        if not t.startswith("#"):
            t = "#" + t
        if len(t) == 7:
            try:
                r, g, b = (int(t[i:i + 2], 16) / 255 for i in (1, 3, 5))
                self.h, self.s, self.v = colorsys.rgb_to_hsv(r, g, b)
                self._render_sv()
                self._update()
                return
            except ValueError:
                pass
        self._update()

    def _set_pipette_cursor(self):
        """Systemweit auf Fadenkreuz/Pipette umstellen (für den Aufnahme-Modus)."""
        self._cursor_replaced = False
        try:
            u = ctypes.windll.user32
            u.LoadCursorW.restype = wintypes.HANDLE
            u.CopyIcon.restype = wintypes.HANDLE
            u.CopyIcon.argtypes = [wintypes.HANDLE]
            u.SetSystemCursor.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            src = pipette_cursor()
            if not src:  # Fallback: Fadenkreuz
                src = u.LoadCursorW(None, ctypes.cast(ctypes.c_void_p(32515), wintypes.LPCWSTR))
            for ocr in (32512, 32513, 32649):  # OCR_NORMAL, OCR_IBEAM, OCR_HAND
                cp = u.CopyIcon(src)
                if cp:
                    u.SetSystemCursor(cp, ocr)
            self._cursor_replaced = True
        except Exception:
            pass

    def _restore_cursor(self):
        if getattr(self, "_cursor_replaced", False):
            try:
                ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)  # SPI_SETCURSORS
            except Exception:
                pass
            self._cursor_replaced = False

    def _eyedrop(self):
        """Farbe per Pipette irgendwo vom Bildschirm aufnehmen (nächster Linksklick)."""
        ctypes.windll.gdi32.GetPixel.restype = ctypes.c_uint32
        self.withdraw()
        self._set_pipette_cursor()
        self._eye_phase = "release"   # erst Loslassen des Buttons abwarten
        self.after(40, self._eye_tick)

    def _eye_finish(self):
        self._restore_cursor()
        if self.winfo_exists():
            self.deiconify()
            self.lift()
            self.focus_force()

    def _eye_tick(self):
        if not self.winfo_exists():
            self._restore_cursor()
            return
        u = ctypes.windll.user32
        down = bool(u.GetAsyncKeyState(0x01) & 0x8000)   # VK_LBUTTON
        if u.GetAsyncKeyState(0x1B) & 0x8000:            # VK_ESCAPE -> abbrechen
            self._eye_finish()
            return
        if self._eye_phase == "release":
            if not down:
                self._eye_phase = "armed"
            return self.after(20, self._eye_tick)
        if down:
            pt = wintypes.POINT()
            u.GetCursorPos(ctypes.byref(pt))
            hdc = u.GetDC(0)
            cref = ctypes.windll.gdi32.GetPixel(hdc, pt.x, pt.y)
            u.ReleaseDC(0, hdc)
            if cref != 0xFFFFFFFF:
                r, g, b = cref & 0xFF, (cref >> 8) & 0xFF, (cref >> 16) & 0xFF
                self.h, self.s, self.v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                self._render_sv()
                self._update()
            self._eye_finish()
            return
        self.after(20, self._eye_tick)

    def _ok(self):
        self.on_ok(self._hex())
        self.destroy()
