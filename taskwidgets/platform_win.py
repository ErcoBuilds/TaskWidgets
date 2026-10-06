"""Windows-spezifische Helfer: DPI, Theme der Titelleiste, abgerundete Ecken,
Pipetten-Cursor, Autostart und Desktop-Verknüpfung."""
import ctypes
import ctypes.wintypes as wintypes
import math
import os
import subprocess
import sys
import tempfile
import tkinter as tk

from taskwidgets.config import APP_NAME, STARTUP_FILE

try:
    import winreg
except ImportError:
    winreg = None


def set_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def resource(name):
    """Pfad zu einer mitgelieferten Datei (auch in der gebauten .exe)."""
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), name)


def _app_script():
    """Pfad des gestarteten Skripts (für Autostart/Verknüpfung im Quellbetrieb)."""
    return os.path.abspath(sys.argv[0])


def windows_wants_light():
    """True, wenn in Windows das helle App-Design eingestellt ist."""
    if not winreg:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return bool(val)
    except OSError:
        return False


def work_area():
    r = ctypes.wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
    return r.left, r.top, r.right, r.bottom


def round_corners(win):
    """Win11: abgerundete Ecken auch für rahmenlose Fenster."""
    try:
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        pref = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
    except Exception:
        pass


def set_titlebar_theme(win, dark):
    """Dunkle/helle native Titelleiste passend zum App-Design (Win10 2004+/Win11)."""
    try:
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(1 if dark else 0)
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        if res != 0:  # ältere Builds: Attribut 19
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))
        return res
    except Exception:
        return -1


class _ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD), ("yHotspot", wintypes.DWORD),
                ("hbmMask", wintypes.HBITMAP), ("hbmColor", wintypes.HBITMAP)]


class _BMPHDR(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


_PIPETTE_CURSOR = None


def pipette_cursor():
    """Kleiner, selbst gezeichneter Pipetten-Cursor (HCURSOR). Wird einmal erstellt."""
    global _PIPETTE_CURSOR
    if _PIPETTE_CURSOR is not None:
        return _PIPETTE_CURSOR
    try:
        N = 32

        def pseg(px_, py_, ax, ay, bx, by):
            dx, dy = bx - ax, by - ay
            L = dx * dx + dy * dy
            t = 0 if L == 0 else max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / L))
            return math.hypot(px_ - (ax + t * dx), py_ - (ay + t * dy))

        def cov(th, d):
            return max(0.0, min(1.0, th - d + 0.5))

        buf = (ctypes.c_ubyte * (N * N * 4))()
        for y in range(N):
            for x in range(N):
                cx, cy = x + 0.5, y + 0.5
                ds = pseg(cx, cy, 3.5, 28.0, 20.0, 11.0)   # Stiel (Spitze unten links -> Kolben oben rechts)
                db = math.hypot(cx - 23.0, cy - 8.0)        # Kolben oben rechts
                acc = [0.0, 0.0, 0.0, 0.0]                  # premultipliziert: R,G,B,A

                def over(col, c):
                    for k in range(3):
                        acc[k] = col[k] * c + acc[k] * (1 - c)
                    acc[3] = c + acc[3] * (1 - c)

                over((255, 255, 255), cov(2.6, ds))         # weiße Kontur Stiel
                over((43, 46, 51), cov(1.3, ds))            # dunkler Stiel
                over((255, 255, 255), cov(5.9, db))         # weißer Rand Kolben
                over((91, 155, 255), cov(4.3, db))          # blauer Kolben
                a = acc[3]
                i = (y * N + x) * 4
                if a > 0:
                    buf[i + 0] = max(0, min(255, int(round(acc[2] / a))))  # B
                    buf[i + 1] = max(0, min(255, int(round(acc[1] / a))))  # G
                    buf[i + 2] = max(0, min(255, int(round(acc[0] / a))))  # R
                    buf[i + 3] = max(0, min(255, int(round(a * 255))))     # A

        u, g = ctypes.windll.user32, ctypes.windll.gdi32
        u.GetDC.restype = wintypes.HDC
        u.GetDC.argtypes = [wintypes.HWND]
        u.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        g.CreateDIBSection.restype = wintypes.HBITMAP
        g.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
        g.CreateBitmap.restype = wintypes.HBITMAP
        g.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.UINT, ctypes.c_void_p]
        g.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        u.CreateIconIndirect.restype = wintypes.HICON
        u.CreateIconIndirect.argtypes = [ctypes.POINTER(_ICONINFO)]
        hdr = _BMPHDR(ctypes.sizeof(_BMPHDR), N, -N, 1, 32, 0, 0, 0, 0, 0, 0)
        ppv = ctypes.c_void_p()
        hdc = u.GetDC(0)
        hbmp = g.CreateDIBSection(hdc, ctypes.byref(hdr), 0, ctypes.byref(ppv), None, 0)
        u.ReleaseDC(0, hdc)
        ctypes.memmove(ppv, buf, N * N * 4)
        hmask = g.CreateBitmap(N, N, 1, 1, None)
        ii = _ICONINFO(0, 3, 28, hmask, hbmp)
        _PIPETTE_CURSOR = u.CreateIconIndirect(ctypes.byref(ii))
        g.DeleteObject(hbmp)
        g.DeleteObject(hmask)
    except Exception:
        _PIPETTE_CURSOR = None
    return _PIPETTE_CURSOR


def show_themed(win, dark):
    """Fenster (zuvor mit withdraw() versteckt) erst nach Titelleisten-Theme/Ecken anzeigen,
    damit die native Titelleiste vom ersten sichtbaren Frame an das richtige Design hat."""
    win.update_idletasks()
    round_corners(win)
    set_titlebar_theme(win, dark)
    # Unsichtbar (alpha 0) einblenden, komplett zeichnen lassen (update erzwingt das
    # Neuzeichnen der Entry-Felder), dann sichtbar machen – kein weißes Aufblitzen.
    try:
        win.attributes("-alpha", 0.0)
        win.deiconify()
        win.update()
        win.attributes("-alpha", 1.0)
    except tk.TclError:
        win.deiconify()


def autostart_enabled():
    return os.path.exists(STARTUP_FILE)


def set_autostart(on):
    if on:
        if getattr(sys, "frozen", False):  # als .exe gebaut
            cmd = f'""{sys.executable}""'
        else:
            pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pyw):
                pyw = sys.executable
            cmd = f'""{pyw}"" ""{_app_script()}""'
        with open(STARTUP_FILE, "w", encoding="utf-8") as f:
            f.write(f'CreateObject("WScript.Shell").Run "{cmd}", 0, False\n')
    elif os.path.exists(STARTUP_FILE):
        os.remove(STARTUP_FILE)


def create_desktop_shortcut():
    """Legt eine Verknüpfung „TaskWidgets" auf dem Desktop an (auch bei OneDrive-Desktop)."""
    if getattr(sys, "frozen", False):  # als .exe gebaut
        target, script = sys.executable, ""
    else:
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        target = pyw if os.path.exists(pyw) else sys.executable
        script = _app_script()
    icon = resource("icon.ico")
    workdir = os.path.dirname(target)
    args_line = f's.Arguments = Chr(34) & "{script}" & Chr(34)' if script else 's.Arguments = ""'
    vbs = ("\r\n".join([
        'Set w = CreateObject("WScript.Shell")',
        'Set s = w.CreateShortcut(w.SpecialFolders("Desktop") & "\\TaskWidgets.lnk")',
        f's.TargetPath = "{target}"',
        args_line,
        f's.IconLocation = "{icon}"',
        f's.WorkingDirectory = "{workdir}"',
        's.Description = "TaskWidgets"',
        's.Save',
    ]) + "\r\n")
    path = os.path.join(tempfile.gettempdir(), "tw_make_lnk.vbs")
    with open(path, "w", encoding="mbcs") as f:
        f.write(vbs)
    try:
        subprocess.run(["wscript.exe", path], creationflags=0x08000000, timeout=15)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
