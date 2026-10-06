"""Wiederverwendbare tkinter-Bausteine im Programmdesign: Pillen-Buttons, Segment-
Umschalter, Schiebeschalter, Zahlenfelder (Stepper), Regler und kleine Helfer.

Alle Funktionen lesen die Theme-Farben über bloße Namen (BG, FG, ACCENT …). Das
config.subscribe(globals()) unten sorgt dafür, dass ein Theme-Wechsel sofort greift.
"""
import math
import tkinter as tk
import tkinter.font as tkfont

from taskwidgets import config
from taskwidgets.config import *  # noqa: F401,F403  (Theme-Namen, px, DAYS …)

config.subscribe(globals())


def _hoverable(w, bg, hover, fg=None, hover_fg=None):
    w.bind("<Enter>", lambda e: w.config(bg=hover, fg=hover_fg or fg or w.cget("fg")))
    w.bind("<Leave>", lambda e: w.config(bg=bg, fg=fg or w.cget("fg")))


def icon_button(parent, glyph, command, bg=None, fg=None, size=11):
    bg = BG if bg is None else bg
    fg = MUTED if fg is None else fg
    b = tk.Label(parent, text=glyph, font=(ICON_FONT, size), bg=bg, fg=fg,
                 padx=px(7), pady=px(5), cursor="hand2")
    _hoverable(b, bg, HOVER, fg, FG)
    b.bind("<Button-1>", lambda e: command())
    return b


def _mix(c1, c2, t):
    """Mischt zwei Hex-Farben (t=0 -> c1, t=1 -> c2)."""
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _round_rect(cv, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def text_button(parent, text, command, bg=None, fg=None, hover=None, bold=False, padx=14):
    """Abgerundeter Pillen-Button auf Canvas-Basis. Signatur bleibt kompatibel."""
    pbg = parent.cget("bg")
    fill = CARD if bg is None else bg
    fg = (FG if fill == CARD else "#101114") if fg is None else fg
    hov = _mix(fill, FG, 0.16) if fill == CARD else _mix(fill, "#ffffff", 0.16)
    f = tkfont.Font(family=FONT, size=10, weight="bold" if bold else "normal")
    w = f.measure(text) + 2 * px(padx)
    h = px(32)
    cv = tk.Canvas(parent, width=w, height=h, bg=pbg, highlightthickness=0, bd=0, cursor="hand2")
    rect = _round_rect(cv, px(1), px(1), w - px(1), h - px(1), px(9), fill=fill, outline="")
    cv.create_text(w / 2, h / 2, text=text, fill=fg, font=f)
    cv.bind("<Enter>", lambda e: cv.itemconfig(rect, fill=hov))
    cv.bind("<Leave>", lambda e: cv.itemconfig(rect, fill=fill))
    cv.bind("<Button-1>", lambda e: command())
    return cv


def segmented(parent, variable, options, command=None):
    """Moderner Segment-Umschalter (ersetzt Radiobuttons/OptionMenu)."""
    track = _mix(BG, "#000000", 0.22)
    cont = tk.Frame(parent, bg=track, padx=px(3), pady=px(3))
    segs = {}

    def refresh():
        cur = variable.get()
        for val, lab in segs.items():
            on = (val == cur)
            lab.config(bg=ACCENT if on else track, fg="#101114" if on else MUTED)

    def pick(val):
        variable.set(val)
        refresh()
        if command:
            command()

    for val, text in options:
        lab = tk.Label(cont, text=text, font=(FONT, 10), padx=px(13), pady=px(5),
                       cursor="hand2", bg=track, fg=MUTED)
        lab.bind("<Button-1>", lambda e, v=val: pick(v))
        lab.pack(side="left")
        segs[val] = lab
    refresh()
    cont.refresh = refresh
    return cont


def _circle_img(d, fill, bg, outline=None, ow=0):
    """Weicher (kantengeglätteter) Kreis als PhotoImage – runder als create_oval.

    `bg` ist die Farbe hinter dem Kreis, gegen die die Kante gemischt wird.
    """
    d = max(2, int(round(d)))
    r = d / 2.0
    inr = r - ow
    f = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(bg[i:i + 2], 16) for i in (1, 3, 5))
    o = tuple(int(outline[i:i + 2], 16) for i in (1, 3, 5)) if outline else f
    rows = []
    for y in range(d):
        row = []
        for x in range(d):
            dist = math.hypot(x + 0.5 - r, y + 0.5 - r)
            cov_out = max(0.0, min(1.0, r - dist + 0.5))      # ganze Scheibe
            cov_in = max(0.0, min(1.0, inr - dist + 0.5))     # Füllung ohne Rand
            col = []
            for k in range(3):
                v = f[k] * cov_in + o[k] * (cov_out - cov_in) + b[k] * (1 - cov_out)
                col.append(max(0, min(255, int(round(v)))))
            row.append("#%02x%02x%02x" % tuple(col))
        rows.append("{" + " ".join(row) + "}")
    img = tk.PhotoImage(width=d, height=d)
    img.put(" ".join(rows))
    return img


def _round_rect_img(w, h, r, fill, bg):
    """Weiche (kantengeglättete) abgerundete Fläche als PhotoImage."""
    w, h = max(2, int(round(w))), max(2, int(round(h)))
    r = min(r, w / 2.0, h / 2.0)
    cx, cy = w / 2.0, h / 2.0
    hx, hy = w / 2.0 - r, h / 2.0 - r
    f = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(bg[i:i + 2], 16) for i in (1, 3, 5))
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            qx = abs(x + 0.5 - cx) - hx
            qy = abs(y + 0.5 - cy) - hy
            sd = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r
            cov = max(0.0, min(1.0, 0.5 - sd))
            row.append("#%02x%02x%02x" % tuple(
                max(0, min(255, int(round(f[k] * cov + b[k] * (1 - cov))))) for k in range(3)))
        rows.append("{" + " ".join(row) + "}")
    img = tk.PhotoImage(width=w, height=h)
    img.put(" ".join(rows))
    return img


def toggle(parent, variable, command=None):
    """Schiebeschalter (ersetzt Checkbuttons)."""
    pbg = parent.cget("bg")
    w, h = px(42), px(24)
    cv = tk.Canvas(parent, width=w, height=h, bg=pbg, highlightthickness=0, bd=0, cursor="hand2")
    kd = h - px(6)
    cv._imgs = {}
    track = cv.create_image(0, 0, anchor="nw")
    knob = cv.create_image(px(3), px(3), anchor="nw")

    def _img(on):
        if on not in cv._imgs:
            cv._imgs[on] = (_round_rect_img(w, h, h / 2, ACCENT if on else BORDER, pbg),
                            _circle_img(kd, "#ffffff", ACCENT if on else BORDER))
        return cv._imgs[on]

    def draw():
        on = bool(variable.get())
        timg, kimg = _img(on)
        cv.itemconfig(track, image=timg)
        cv.itemconfig(knob, image=kimg)
        x = (w - px(3) - kd) if on else px(3)
        cv.coords(knob, x, px(3))

    def flip(_e=None):
        variable.set(not variable.get())
        draw()
        if command:
            command()

    cv.bind("<Button-1>", flip)
    cv.draw = draw
    draw()
    return cv


def section_header(parent, text, glyph=None):
    """Kleine Abschnitts-Überschrift mit optionalem Icon."""
    f = tk.Frame(parent, bg=parent.cget("bg"))
    if glyph:
        tk.Label(f, text=glyph, font=(ICON_FONT, 10), fg=ACCENT, bg=f.cget("bg")).pack(side="left", padx=(0, px(6)))
    tk.Label(f, text=text.upper(), font=(FONT, 8, "bold"), fg=MUTED, bg=f.cget("bg")).pack(side="left")
    return f


def label(parent, text="", size=10, fg=None, bg=None, bold=False, **kw):
    return tk.Label(parent, text=text, font=(FONT, size, "bold" if bold else "normal"),
                    fg=FG if fg is None else fg, bg=BG if bg is None else bg, **kw)


def entry_style():
    return dict(bg=CARD, fg=FG, insertbackground=FG, relief="flat", font=(FONT, 11),
                disabledbackground=CARD, disabledforeground=MUTED, readonlybackground=CARD,
                highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)


def _spin_style():
    return dict(bg=CARD, fg=FG, insertbackground=FG, relief="flat", buttonbackground=CARD,
                highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)


def stepper(parent, var, lo, hi, wrap=False, width=2, command=None, pad=False):
    """Ein kompaktes Zahlenfeld mit ▴/▾-Spalte rechts – eine Umrandung statt drei.

    Links eine echte tk.Entry (Tippen + var-Bindung bleiben), rechts im selben
    abgerundeten CARD-Feld eine schlanke Chevron-Spalte: obere Hälfte +1, untere
    Hälfte −1. Mausrad über dem Feld schrittet ebenfalls.
    """
    bg = parent.cget("bg")
    cont = tk.Frame(parent, bg=bg)

    def fmt(n):
        return f"{n:02d}" if pad else str(n)

    def cur():
        try:
            return int(var.get())
        except (ValueError, tk.TclError):
            return lo

    def step(d):
        n = cur() + d
        if n > hi:
            n = lo if wrap else hi
        if n < lo:
            n = hi if wrap else lo
        var.set(fmt(n))
        if command:
            command()

    # --- Maße (DPI-abhängig über px); width = Zeichen -> Pixel ---
    ef = tkfont.Font(family=FONT, size=11)
    text_w = ef.measure("0" * max(width, 1)) + px(10)   # Zahlenbereich
    gutter = px(16)                                      # Chevron-Spalte
    h = px(26)
    w = text_w + gutter

    cv = tk.Canvas(cont, width=w, height=h, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
    cv.pack()
    rect = _round_rect(cv, px(1), px(1), w - px(1), h - px(1), px(7), fill=CARD, outline=BORDER)
    div_x = text_w
    cv.create_line(div_x, px(6), div_x, h - px(6), fill=_mix(BORDER, CARD, 0.45))

    # Echtes Entry eingebettet – Tippen & var-Bindung bleiben erhalten.
    e = tk.Entry(cv, textvariable=var, width=width, justify="center", **entry_style())
    e.config(highlightthickness=0, bd=0)
    cv.create_window(div_x / 2, h / 2, window=e, width=text_w - px(4), height=h - px(8))

    # Chevrons: ▴/▾ in Segoe UI rendern verlässlich in beiden Themes.
    chev_x = text_w + gutter / 2
    up = cv.create_text(chev_x, h * 0.30, text="▴", fill=MUTED, font=(FONT, 9, "bold"))
    dn = cv.create_text(chev_x, h * 0.70, text="▾", fill=MUTED, font=(FONT, 9, "bold"))

    def _paint(active=None):
        cv.itemconfig(up, fill=FG if active == "up" else MUTED)
        cv.itemconfig(dn, fill=FG if active == "dn" else MUTED)

    def _half(ev):
        return "up" if ev.y < h / 2 else "dn"

    def _on_motion(ev):
        _paint(_half(ev) if ev.x >= div_x else None)

    def _on_click(ev):
        if ev.x >= div_x:
            step(1 if _half(ev) == "up" else -1)

    def _on_wheel(ev):
        step(1 if ev.delta > 0 else -1)

    cv.bind("<Motion>", _on_motion)
    cv.bind("<Leave>", lambda _e: _paint(None))
    cv.bind("<Button-1>", _on_click)
    cv.bind("<MouseWheel>", _on_wheel)
    e.bind("<MouseWheel>", _on_wheel)

    def _clamp(_ev=None):
        var.set(fmt(max(lo, min(hi, cur()))))
        cv.itemconfig(rect, outline=BORDER)
        if command:
            command()

    e.bind("<FocusIn>", lambda _e: cv.itemconfig(rect, outline=ACCENT))
    e.bind("<FocusOut>", _clamp)

    cont.step = step    # programmatischer Zugriff (Tests/Tastatur)
    cont.var = var
    return cont


def day_pills(parent, variables, command=None):
    """Mehrfachauswahl der Wochentage als Pillenreihe (im Segment-Look)."""
    track = _mix(BG, "#000000", 0.22)
    cont = tk.Frame(parent, bg=track, padx=px(3), pady=px(3))
    cells = []

    def refresh():
        for v, lab in cells:
            on = bool(v.get())
            lab.config(bg=ACCENT if on else track, fg="#101114" if on else MUTED)

    def flip(v):
        v.set(0 if v.get() else 1)
        refresh()
        if command:
            command()

    for v, name in zip(variables, DAYS):
        lab = tk.Label(cont, text=name, font=(FONT, 10), width=3, padx=px(6), pady=px(5),
                       cursor="hand2", bg=track, fg=MUTED)
        lab.bind("<Button-1>", lambda e, vv=v: flip(vv))
        lab.pack(side="left")
        cells.append((v, lab))
    refresh()
    cont.refresh = refresh
    return cont


def slider(parent, var, lo, hi, command=None, width=260):
    """Konturierter Canvas-Schieberegler mit ACCENT-Füllung und weißem Knopf.

    `var` wird als Prozentwert (int lo..hi) gelesen/gesetzt; `command(pct)` läuft live.
    """
    bg = parent.cget("bg")
    w, h = px(width), px(22)
    cv = tk.Canvas(parent, width=w, height=h, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
    kd = px(16)
    x0, x1 = kd / 2, w - kd / 2
    ty0, ty1 = h / 2 - px(3), h / 2 + px(3)
    track = _round_rect(cv, x0, ty0, x1, ty1, px(3), fill=CARD, outline=BORDER)
    fill = _round_rect(cv, x0, ty0, x0 + px(1), ty1, px(3), fill=ACCENT, outline="")
    cv._knob_img = _circle_img(kd, "#ffffff", bg, outline=BORDER, ow=max(1, px(1)))
    knob = cv.create_image(0, 0, anchor="nw", image=cv._knob_img)

    def pct():
        try:
            return int(round(float(var.get())))
        except (ValueError, tk.TclError):
            return lo

    def draw(p):
        p = max(lo, min(hi, p))
        frac = (p - lo) / (hi - lo) if hi > lo else 0
        cx = x0 + frac * (x1 - x0)
        cv.coords(knob, cx - kd / 2, h / 2 - kd / 2)
        cv.coords(fill, x0, ty0, max(x0 + px(1), cx), ty1)

    def set_from_x(px_x):
        frac = (px_x - x0) / (x1 - x0) if x1 > x0 else 0
        p = int(round(lo + max(0, min(1, frac)) * (hi - lo)))
        if p != pct():
            var.set(p)
            if command:
                command(p)
        draw(p)

    cv.bind("<Button-1>", lambda e: set_from_x(e.x))
    cv.bind("<B1-Motion>", lambda e: set_from_x(e.x))
    cv.draw = lambda: draw(pct())
    draw(pct())
    return cv
