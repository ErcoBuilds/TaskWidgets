"""Symbol im Infobereich der Taskleiste (Tray) samt eigener Nachrichtenschleife,
die nötigen Win32-Strukturen/-Bindungen und die Einzelinstanz-Prüfung."""
import ctypes
import ctypes.wintypes as wintypes
import os
import sys
import threading

from taskwidgets.config import APP_NAME
from taskwidgets.platform_win import resource

WM_APP_TRAY = 0x8001  # Mausereignisse am Tray-Symbol
WM_APP_TIP = 0x8002   # Tooltip aktualisieren
WM_APP_SHOW = 0x8003  # zweiter Programmstart -> Widget zeigen
TRAY_CLASS = "TaskWidgetsTrayWnd"
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256), ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wintypes.HICON)]


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32")
for _fn, _args, _res in (
    (user32.DefWindowProcW, [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], LRESULT),
    (user32.CreateWindowExW, [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                              ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                              wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID], wintypes.HWND),
    (user32.RegisterClassW, [ctypes.POINTER(WNDCLASSW)], wintypes.ATOM),
    (user32.LoadImageW, [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                         wintypes.UINT], wintypes.HANDLE),
    (user32.LoadIconW, [wintypes.HINSTANCE, wintypes.LPVOID], wintypes.HICON),
    (user32.PostMessageW, [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
    (user32.FindWindowW, [wintypes.LPCWSTR, wintypes.LPCWSTR], wintypes.HWND),
    (user32.MessageBoxW, [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT], ctypes.c_int),
    (user32.CreatePopupMenu, [], wintypes.HMENU),
    (user32.AppendMenuW, [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR], wintypes.BOOL),
    (user32.SetMenuDefaultItem, [wintypes.HMENU, wintypes.UINT, wintypes.UINT], wintypes.BOOL),
    (user32.TrackPopupMenu, [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                             wintypes.HWND, wintypes.LPVOID], ctypes.c_int),
    (user32.DestroyMenu, [wintypes.HMENU], wintypes.BOOL),
    (user32.GetCursorPos, [ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
    (user32.SetForegroundWindow, [wintypes.HWND], wintypes.BOOL),
    (user32.GetMessageW, [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT],
     wintypes.BOOL),
    (user32.TranslateMessage, [ctypes.POINTER(wintypes.MSG)], wintypes.BOOL),
    (user32.DispatchMessageW, [ctypes.POINTER(wintypes.MSG)], LRESULT),
    (user32.DestroyWindow, [wintypes.HWND], wintypes.BOOL),
    (user32.PostQuitMessage, [ctypes.c_int], None),
    (user32.RegisterWindowMessageW, [wintypes.LPCWSTR], wintypes.UINT),
    (user32.GetSystemMetrics, [ctypes.c_int], ctypes.c_int),
    (shell32.Shell_NotifyIconW, [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)], wintypes.BOOL),
    (kernel32.GetModuleHandleW, [wintypes.LPCWSTR], wintypes.HMODULE),
    (kernel32.CreateMutexW, [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
):
    _fn.argtypes, _fn.restype = _args, _res


def single_instance():
    """Läuft das Programm schon, wird dort das Widget eingeblendet und hier beendet."""
    handle = kernel32.CreateMutexW(None, False, "Local\\TaskWidgetsMutex")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        hwnd = user32.FindWindowW(TRAY_CLASS, None)
        if hwnd:
            user32.PostMessageW(hwnd, WM_APP_SHOW, 0, 0)
        else:
            user32.MessageBoxW(None, "TaskWidgets läuft bereits.", APP_NAME, 0x40)
        sys.exit(0)
    return handle


class Tray(threading.Thread):
    """Symbol im Infobereich. Läuft in eigenem Thread mit eigener Nachrichtenschleife und
    meldet Klicks über eine Queue an den tkinter-Thread."""

    MENU_IDS = {1: "toggle", 2: "new", 3: "list", 4: "history", 5: "autostart", 9: "quit"}

    def __init__(self, events, state):
        super().__init__(daemon=True)
        self.events = events
        self.state = state
        self.hwnd = None
        self.hicon = None
        self.tip = APP_NAME

    def run(self):
        hinst = kernel32.GetModuleHandleW(None)
        self._proc = WNDPROC(self.wndproc)  # Referenz halten, sonst räumt der GC sie weg
        wc = WNDCLASSW(lpfnWndProc=self._proc, hInstance=hinst, lpszClassName=TRAY_CLASS)
        user32.RegisterClassW(ctypes.byref(wc))
        self.taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")
        self.hwnd = user32.CreateWindowExW(0, TRAY_CLASS, APP_NAME, 0, 0, 0, 0, 0, None, None, hinst, None)
        size = user32.GetSystemMetrics(49)  # SM_CXSMICON
        if os.path.exists(resource("icon.ico")):
            self.hicon = user32.LoadImageW(None, resource("icon.ico"), 1, size, size, 0x10)
        if not self.hicon:
            self.hicon = user32.LoadIconW(None, ctypes.c_void_p(32512))  # IDI_APPLICATION
        self.notify(0)  # NIM_ADD
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def notify(self, action):
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd, nid.uID = self.hwnd, 1
        nid.uFlags = 0x1 | 0x2 | 0x4  # NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_APP_TRAY
        nid.hIcon = self.hicon
        nid.szTip = self.tip[:127]
        shell32.Shell_NotifyIconW(action, ctypes.byref(nid))

    def wndproc(self, hwnd, msg, wp, lp):
        if msg == WM_APP_TRAY:
            if lp == 0x0202:  # WM_LBUTTONUP
                self.events.put("toggle")
            elif lp == 0x0205:  # WM_RBUTTONUP
                self.show_menu()
            return 0
        if msg == WM_APP_TIP:
            self.notify(1)  # NIM_MODIFY
            return 0
        if msg == WM_APP_SHOW:
            self.events.put("show")
            return 0
        if msg == getattr(self, "taskbar_created", None):  # Explorer wurde neu gestartet
            self.notify(0)
            return 0
        if msg == 0x0010:  # WM_CLOSE
            user32.DestroyWindow(hwnd)
            return 0
        if msg == 0x0002:  # WM_DESTROY
            self.notify(2)  # NIM_DELETE
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def show_menu(self):
        state = self.state()
        hmenu = user32.CreatePopupMenu()
        user32.AppendMenuW(hmenu, 0, 1, "Widget ausblenden" if state["visible"] else "Widget anzeigen")
        user32.AppendMenuW(hmenu, 0, 2, "Neue Aufgabe")
        user32.AppendMenuW(hmenu, 0, 3, "Alle Aufgaben")
        user32.AppendMenuW(hmenu, 0, 4, "Verlauf")
        user32.AppendMenuW(hmenu, 0x800, 0, None)  # Trennlinie
        user32.AppendMenuW(hmenu, 0x8 if state["autostart"] else 0, 5, "Mit Windows starten")
        user32.AppendMenuW(hmenu, 0x800, 0, None)
        user32.AppendMenuW(hmenu, 0, 9, "Beenden")
        user32.SetMenuDefaultItem(hmenu, 1, False)
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenu(hmenu, 0x100 | 0x80 | 0x2, pt.x, pt.y, 0, self.hwnd, None)
        user32.PostMessageW(self.hwnd, 0, 0, 0)
        user32.DestroyMenu(hmenu)
        if cmd in self.MENU_IDS:
            self.events.put(self.MENU_IDS[cmd])

    def set_tip(self, text):
        if text != self.tip:
            self.tip = text
            if self.hwnd:
                user32.PostMessageW(self.hwnd, WM_APP_TIP, 0, 0)

    def stop(self):
        if self.hwnd:
            user32.PostMessageW(self.hwnd, 0x0010, 0, 0)
            self.join(timeout=1)
