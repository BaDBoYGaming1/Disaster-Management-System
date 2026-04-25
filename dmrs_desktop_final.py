"""
Disaster Management Relief System — Desktop Application
Built with Python tkinter (zero external dependencies)
C backend loaded via ctypes
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import ctypes, json, os, sys, threading, webbrowser
from pathlib import Path

# ─── Load C Engine ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
if sys.platform == "win32":
    LIB_NAME = "libdisaster.so"
else:
    LIB_NAME = "libdisaster.dll"

LIB_PATH = BASE_DIR / LIB_NAME

try:
    lib = ctypes.CDLL(str(LIB_PATH))
except OSError:
    tk.Tk().withdraw()
    messagebox.showerror("Missing Library",
        f"Could not load {LIB_NAME}\n\n"
        "Please compile the C backend first:\n\n"
        "  Windows:  gcc -shared -fPIC -o libdisaster.dll disaster_engine.c -lm\n"
        "  Linux/Mac: cd backend && make")
    sys.exit(1)

lib.engine_login.restype           = ctypes.c_int
lib.engine_register.restype        = ctypes.c_int
lib.engine_add_disaster.restype    = ctypes.c_int
lib.engine_remove_disaster.restype = ctypes.c_int
lib.engine_add_resource.restype    = ctypes.c_int
lib.engine_remove_resource.restype = ctypes.c_int
lib.engine_assign_resource.restype = ctypes.c_int
lib.engine_init()

BUF = 65536

def cbuf():
    return ctypes.create_string_buffer(BUF)

def c_get_disasters():
    b = cbuf(); lib.engine_get_disasters(b, BUF); return json.loads(b.value.decode())

def c_get_resources():
    b = cbuf(); lib.engine_get_resources(b, BUF); return json.loads(b.value.decode())

def c_get_stats():
    b = cbuf(); lib.engine_stats(b, BUF); return json.loads(b.value.decode())

def c_nearest(lat, lon):
    b = cbuf()
    lib.engine_nearest_disaster(ctypes.c_double(lat), ctypes.c_double(lon), b, BUF)
    return json.loads(b.value.decode())

def c_user_info(uid):
    b = cbuf(); lib.engine_user_info(ctypes.c_int(uid), b, BUF); return json.loads(b.value.decode())

def c_route(src_idx, dst_idx):
    """Call engine_route(src, dst, buf, size) → parsed JSON with waypoints."""
    b = cbuf()
    lib.engine_route(ctypes.c_int(src_idx), ctypes.c_int(dst_idx), b, ctypes.c_int(BUF))
    return json.loads(b.value.decode())

# ─── Graph Algorithm Engine (pure Python, operates on city node list) ────────
import math as _math

# Canonical city list
CITY_NODES = [
    ("Mumbai",      19.0760, 72.8777),
    ("Chennai",     13.0827, 80.2707),
    ("Kolkata",     22.5726, 88.3639),
    ("Hyderabad",   17.3850, 78.4867),
    ("Delhi",       28.6139, 77.2090),
    ("Kochi",        9.9312, 76.2673),
    ("Bhubaneswar", 20.2961, 85.8189),
    ("Dehradun",    30.3165, 78.0322),
]

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = _math.radians(lat2 - lat1)
    dlon = _math.radians(lon2 - lon1)
    a = (_math.sin(dlat/2)**2 +
         _math.cos(_math.radians(lat1)) * _math.cos(_math.radians(lat2)) *
         _math.sin(dlon/2)**2)
    return R * 2 * _math.atan2(_math.sqrt(a), _math.sqrt(1-a))

def _build_adjacency():
    """Full adjacency list: every city connected to every other (complete graph)."""
    n = len(CITY_NODES)
    adj = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(n):
            if i != j:
                d = _haversine(CITY_NODES[i][1], CITY_NODES[i][2],
                               CITY_NODES[j][1], CITY_NODES[j][2])
                adj[i].append((j, d))
    return adj

CITY_ADJ = _build_adjacency()

# ─── Colour Palette ───────────────────────────────────────────────────────────
BG       = "#0a0e17"
SURFACE  = "#111827"
SURFACE2 = "#162032"
BORDER   = "#1e2d45"
ACCENT   = "#e63946"
ACCENT2  = "#f4a261"
ACCENT3  = "#4cc9f0"
SUCCESS  = "#22c55e"
WARNING  = "#eab308"
TEXT     = "#e2e8f0"
MUTED    = "#64748b"

SEV_COLORS = ["", ACCENT3, SUCCESS, WARNING, ACCENT2, ACCENT]
TYPE_ICONS = {
    "flood": "🌊", "cyclone": "🌀", "earthquake": "🌍",
    "landslide": "⛰", "fire": "🔥", "heatwave": "☀️", "other": "⚠️"
}
RES_ICONS = {
    "rescue_team": "🚁", "medical": "💊", "food": "🍱",
    "shelter": "⛺", "equipment": "🔧", "water": "💧"
}

# ─── Shared session state ─────────────────────────────────────────────────────
session = {"user_id": None, "username": None, "role": None}


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DMRS — Secure Access")
        self.geometry("480x560")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.eval('tk::PlaceWindow . center')
        self._build()

    def _build(self):
        # ── Header ──
        hdr = tk.Frame(self, bg=ACCENT, height=4)
        hdr.pack(fill="x")

        logo_frame = tk.Frame(self, bg=BG, pady=30)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="🚨 DMRS", font=("Courier", 28, "bold"),
                 bg=BG, fg=ACCENT).pack()
        tk.Label(logo_frame, text="DISASTER MANAGEMENT RELIEF SYSTEM",
                 font=("Courier", 9), bg=BG, fg=MUTED).pack()

        # ── Card ──
        card = tk.Frame(self, bg=SURFACE, padx=40, pady=30,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=30, pady=(0, 30))

        tk.Label(card, text="SECURE ACCESS", font=("Courier", 16, "bold"),
                 bg=SURFACE, fg=TEXT).pack(anchor="w")
        tk.Label(card, text="// AUTHORIZED PERSONNEL ONLY",
                 font=("Courier", 9), bg=SURFACE, fg=MUTED).pack(anchor="w", pady=(0, 20))

        # Flash label
        self.flash_var = tk.StringVar()
        self.flash_lbl = tk.Label(card, textvariable=self.flash_var,
                                  font=("Courier", 10), bg=SURFACE, fg=ACCENT,
                                  wraplength=360, justify="left")
        self.flash_lbl.pack(fill="x", pady=(0, 10))

        # Username
        tk.Label(card, text="USERNAME", font=("Courier", 9),
                 bg=SURFACE, fg=MUTED).pack(anchor="w")
        self.username_var = tk.StringVar()
        uentry = tk.Entry(card, textvariable=self.username_var,
                          font=("Courier", 13), bg=BG, fg=TEXT,
                          insertbackground=TEXT, relief="flat",
                          highlightbackground=BORDER, highlightthickness=1)
        uentry.pack(fill="x", ipady=8, pady=(2, 14))
        uentry.focus()

        # Password
        tk.Label(card, text="PASSWORD", font=("Courier", 9),
                 bg=SURFACE, fg=MUTED).pack(anchor="w")
        self.password_var = tk.StringVar()
        pentry = tk.Entry(card, textvariable=self.password_var, show="●",
                          font=("Courier", 13), bg=BG, fg=TEXT,
                          insertbackground=TEXT, relief="flat",
                          highlightbackground=BORDER, highlightthickness=1)
        pentry.pack(fill="x", ipady=8, pady=(2, 20))
        pentry.bind("<Return>", lambda e: self._login())

        # Login button
        btn = tk.Button(card, text="ACCESS SYSTEM",
                        font=("Courier", 12, "bold"), bg=ACCENT, fg="white",
                        activebackground="#c1121f", activeforeground="white",
                        relief="flat", cursor="hand2", command=self._login)
        btn.pack(fill="x", ipady=10)

        # Register link
        reg_frame = tk.Frame(card, bg=SURFACE)
        reg_frame.pack(pady=(16, 0))
        tk.Label(reg_frame, text="New responder? ", font=("Courier", 10),
                 bg=SURFACE, fg=MUTED).pack(side="left")
        reg_link = tk.Label(reg_frame, text="Register here",
                            font=("Courier", 10, "underline"),
                            bg=SURFACE, fg=ACCENT2, cursor="hand2")
        reg_link.pack(side="left")
        reg_link.bind("<Button-1>", lambda e: self._open_register())

        tk.Label(card, text="Demo: admin / admin123",
                 font=("Courier", 9), bg=SURFACE, fg=MUTED).pack(pady=(10, 0))

        # Status bar
        status = tk.Frame(self, bg=SURFACE, height=28)
        status.pack(fill="x", side="bottom")
        tk.Label(status, text="● SYSTEM ONLINE", font=("Courier", 9),
                 bg=SURFACE, fg=SUCCESS).pack(side="left", padx=12, pady=4)

    def _login(self):
        u = self.username_var.get().strip()
        p = self.password_var.get().strip()
        if not u or not p:
            self.flash_var.set("⚠ Please enter username and password")
            return
        uid = lib.engine_login(u.encode(), p.encode())
        if uid > 0:
            info = c_user_info(uid)
            session["user_id"]  = uid
            session["username"] = info.get("username", u)
            session["role"]     = info.get("role", "viewer")
            self.destroy()
            DashboardWindow().mainloop()
        else:
            self.flash_var.set("⚠ Invalid credentials. Try: admin / admin123")

    def _open_register(self):
        RegisterWindow(self)


# ══════════════════════════════════════════════════════════════════════════════
#  REGISTER WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class RegisterWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("DMRS — Register")
        self.geometry("420x500")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self._build()

    def _build(self):
        tk.Frame(self, bg=ACCENT2, height=4).pack(fill="x")

        hdr = tk.Frame(self, bg=BG, pady=20)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🚁 JOIN THE NETWORK",
                 font=("Courier", 18, "bold"), bg=BG, fg=ACCENT2).pack()
        tk.Label(hdr, text="RESPONDER REGISTRATION",
                 font=("Courier", 9), bg=BG, fg=MUTED).pack()

        card = tk.Frame(self, bg=SURFACE, padx=30, pady=24,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        self.flash_var = tk.StringVar()
        tk.Label(card, textvariable=self.flash_var, font=("Courier", 10),
                 bg=SURFACE, fg=ACCENT, wraplength=320).pack(fill="x", pady=(0, 8))

        fields = [("USERNAME", False), ("EMAIL", False), ("PASSWORD", True)]
        self.vars = {}
        for lbl, secret in fields:
            tk.Label(card, text=lbl, font=("Courier", 9),
                     bg=SURFACE, fg=MUTED).pack(anchor="w")
            v = tk.StringVar(); self.vars[lbl] = v
            e = tk.Entry(card, textvariable=v,
                         show="●" if secret else "",
                         font=("Courier", 12), bg=BG, fg=TEXT,
                         insertbackground=TEXT, relief="flat",
                         highlightbackground=BORDER, highlightthickness=1)
            e.pack(fill="x", ipady=7, pady=(2, 12))

        tk.Label(card, text="ROLE", font=("Courier", 9),
                 bg=SURFACE, fg=MUTED).pack(anchor="w")
        self.role_var = tk.StringVar(value="viewer")
        role_combo = ttk.Combobox(card, textvariable=self.role_var,
                                  values=["viewer", "responder"],
                                  font=("Courier", 12), state="readonly")
        role_combo.pack(fill="x", ipady=5, pady=(2, 16))

        tk.Button(card, text="CREATE ACCOUNT",
                  font=("Courier", 12, "bold"), bg=ACCENT2, fg=BG,
                  activebackground="#d4894f", relief="flat",
                  cursor="hand2", command=self._register).pack(fill="x", ipady=9)

    def _register(self):
        u = self.vars["USERNAME"].get().strip()
        e = self.vars["EMAIL"].get().strip()
        p = self.vars["PASSWORD"].get().strip()
        r = self.role_var.get()
        if not all([u, e, p]):
            self.flash_var.set("⚠ All fields are required")
            return
        uid = lib.engine_register(u.encode(), p.encode(), r.encode(), e.encode())
        if uid == -2:
            self.flash_var.set("⚠ Username already taken")
        elif uid > 0:
            messagebox.showinfo("Success", "Account created! Please log in.")
            self.destroy()
        else:
            self.flash_var.set("⚠ Registration failed")


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class DashboardWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"DMRS — Command Dashboard [{session['username'].upper()}]")
        self.geometry("1280x780")
        self.minsize(1100, 680)
        self.configure(bg=BG)
        self.eval('tk::PlaceWindow . center')
        # ── Algorithm visualisation state ──
        self._algo_running   = False
        self._algo_after_ids = []
        self._dijkstra_path  = []
        self._algo_state     = {}          # current overlay state dict
        self.after_ids       = []
        self._build()
        self._refresh_all()
        self._auto_refresh()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        self._build_navbar()
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True)
        self._build_left(main)
        self._build_center(main)
        self._build_right(main)
        self._build_statusbar()

    def _build_navbar(self):
        nav = tk.Frame(self, bg=SURFACE, height=52,
                       highlightbackground=BORDER, highlightthickness=1)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        tk.Label(nav, text="🚨 DMRS", font=("Courier", 16, "bold"),
                 bg=SURFACE, fg=ACCENT).pack(side="left", padx=(16, 4), pady=14)
        tk.Label(nav, text="COMMAND CENTER", font=("Courier", 8),
                 bg=SURFACE, fg=MUTED).pack(side="left", pady=14)

        # Right side
        role_colors = {"admin": ACCENT, "responder": ACCENT2, "viewer": ACCENT3}
        role_color = role_colors.get(session["role"], MUTED)
        tk.Label(nav, text=f"[{session['role'].upper()}]",
                 font=("Courier", 10, "bold"), bg=SURFACE,
                 fg=role_color).pack(side="right", padx=8)
        tk.Label(nav, text=f"OPS: {session['username'].upper()}",
                 font=("Courier", 10), bg=SURFACE, fg=MUTED).pack(side="right", padx=4)

        tk.Button(nav, text="⏻ LOGOUT", font=("Courier", 10),
                  bg=SURFACE, fg=MUTED, activebackground=SURFACE,
                  activeforeground=ACCENT, relief="flat", cursor="hand2",
                  command=self._logout).pack(side="right", padx=8)
        tk.Button(nav, text="↻ REFRESH", font=("Courier", 10),
                  bg=SURFACE, fg=MUTED, activebackground=SURFACE,
                  activeforeground=ACCENT3, relief="flat", cursor="hand2",
                  command=self._refresh_all).pack(side="right", padx=4)

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=SURFACE, width=340,
                        highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # Tab bar
        tab_bar = tk.Frame(left, bg=SURFACE)
        tab_bar.pack(fill="x")
        self.active_tab = tk.StringVar(value="disasters")
        self.tab_btns = {}
        for key, label in [("disasters", "🔴 DISASTERS"), ("resources", "📦 RESOURCES")]:
            btn = tk.Button(tab_bar, text=label, font=("Courier", 10, "bold"),
                            bg=SURFACE, fg=MUTED, relief="flat", cursor="hand2",
                            command=lambda k=key: self._switch_tab(k))
            btn.pack(side="left", fill="x", expand=True, ipady=10)
            self.tab_btns[key] = btn

        tk.Frame(left, bg=BORDER, height=2).pack(fill="x")

        # Panels
        self.disaster_panel = tk.Frame(left, bg=SURFACE)
        self.resource_panel = tk.Frame(left, bg=SURFACE)
        self._build_disaster_panel(self.disaster_panel)
        self._build_resource_panel(self.resource_panel)
        self._switch_tab("disasters")

    def _build_disaster_panel(self, parent):
        # Add form (admin/responder only)
        if session["role"] in ("admin", "responder"):
            form = tk.LabelFrame(parent, text=" + ADD DISASTER ",
                                 font=("Courier", 9), bg=SURFACE, fg=ACCENT2,
                                 highlightbackground=BORDER, highlightthickness=1,
                                 padx=10, pady=8)
            form.pack(fill="x", padx=8, pady=8)

            self.d_vars = {
                "name": tk.StringVar(), "type": tk.StringVar(value="flood"),
                "lat":  tk.StringVar(), "lon":  tk.StringVar(),
                "sev":  tk.StringVar(value="5")
            }
            self._field(form, "e.g. Mumbai Coastal Flood", self.d_vars["name"])
            combo_row = tk.Frame(form, bg=SURFACE)
            combo_row.pack(fill="x", pady=2)
            ttk.Combobox(combo_row, textvariable=self.d_vars["type"],
                         values=list(TYPE_ICONS.keys()),
                         font=("Courier", 10), width=12,
                         state="readonly").pack(side="left", padx=(0, 4))
            ttk.Combobox(combo_row, textvariable=self.d_vars["sev"],
                         values=["5","4","3","2","1"],
                         font=("Courier", 10), width=5,
                         state="readonly").pack(side="left")
            tk.Label(combo_row, text="(sev)", font=("Courier", 8),
                     bg=SURFACE, fg=MUTED).pack(side="left", padx=3)

            ll = tk.Frame(form, bg=SURFACE)
            ll.pack(fill="x", pady=2)
            self._ph_entry(ll, "e.g. 19.0760", self.d_vars["lat"],  width=12, side="left", padx=(0,4))
            self._ph_entry(ll, "e.g. 72.8777", self.d_vars["lon"],  width=12, side="left", padx=(0,4))

            tk.Button(form, text="⚡ DEPLOY ALERT",
                      font=("Courier", 10, "bold"), bg=ACCENT, fg="white",
                      activebackground="#c1121f", relief="flat", cursor="hand2",
                      command=self._add_disaster).pack(fill="x", ipady=7, pady=(4, 0))

        # List
        tk.Label(parent, text="▸ ACTIVE INCIDENTS",
                 font=("Courier", 9), bg=SURFACE, fg=MUTED).pack(anchor="w", padx=10, pady=(6, 2))

        container = tk.Frame(parent, bg=SURFACE)
        container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        scrollbar = tk.Scrollbar(container, bg=SURFACE, troughcolor=BG)
        scrollbar.pack(side="right", fill="y")

        self.disaster_canvas = tk.Canvas(container, bg=SURFACE,
                                         highlightthickness=0,
                                         yscrollcommand=scrollbar.set)
        self.disaster_canvas.pack(fill="both", expand=True)
        scrollbar.config(command=self.disaster_canvas.yview)

        self.disaster_list_frame = tk.Frame(self.disaster_canvas, bg=SURFACE)
        self.disaster_canvas.create_window((0, 0), window=self.disaster_list_frame,
                                            anchor="nw", tags="frame")
        self.disaster_list_frame.bind("<Configure>", lambda e: self.disaster_canvas.configure(
            scrollregion=self.disaster_canvas.bbox("all")))
        self.disaster_canvas.bind("<Configure>", lambda e: self.disaster_canvas.itemconfig(
            "frame", width=e.width))

    def _build_resource_panel(self, parent):
        if session["role"] in ("admin", "responder"):
            form = tk.LabelFrame(parent, text=" + ADD RESOURCE ",
                                 font=("Courier", 9), bg=SURFACE, fg=ACCENT2,
                                 highlightbackground=BORDER, highlightthickness=1,
                                 padx=10, pady=8)
            form.pack(fill="x", padx=8, pady=8)

            self.r_vars = {
                "name": tk.StringVar(), "type": tk.StringVar(value="rescue_team"),
                "lat":  tk.StringVar(), "lon":  tk.StringVar(),
                "qty":  tk.StringVar(), "unit": tk.StringVar()
            }
            self._field(form, "e.g. NDRF Team Alpha", self.r_vars["name"])
            ttk.Combobox(form, textvariable=self.r_vars["type"],
                         values=list(RES_ICONS.keys()),
                         font=("Courier", 10), state="readonly").pack(fill="x", pady=2)

            ll = tk.Frame(form, bg=SURFACE)
            ll.pack(fill="x", pady=2)
            self._ph_entry(ll, "e.g. 19.0760", self.r_vars["lat"], width=12, side="left", padx=(0,4))
            self._ph_entry(ll, "e.g. 72.8777", self.r_vars["lon"], width=12, side="left", padx=(0,4))

            qq = tk.Frame(form, bg=SURFACE)
            qq.pack(fill="x", pady=2)
            self._ph_entry(qq, "Qty e.g. 50",       self.r_vars["qty"],  width=9,  side="left", padx=(0,4))
            self._ph_entry(qq, "Unit e.g. personnel",self.r_vars["unit"], width=14, side="left", padx=(0,0))

            tk.Button(form, text="📦 ADD RESOURCE",
                      font=("Courier",10,"bold"), bg=ACCENT2, fg=BG,
                      activebackground="#d4894f", relief="flat", cursor="hand2",
                      command=self._add_resource).pack(fill="x", ipady=7, pady=(4,0))

        tk.Label(parent, text="▸ RESOURCE INVENTORY",
                 font=("Courier",9), bg=SURFACE, fg=MUTED).pack(anchor="w", padx=10, pady=(6,2))

        container = tk.Frame(parent, bg=SURFACE)
        container.pack(fill="both", expand=True, padx=8, pady=(0,8))

        sb = tk.Scrollbar(container, bg=SURFACE, troughcolor=BG)
        sb.pack(side="right", fill="y")
        self.resource_canvas = tk.Canvas(container, bg=SURFACE,
                                          highlightthickness=0,
                                          yscrollcommand=sb.set)
        self.resource_canvas.pack(fill="both", expand=True)
        sb.config(command=self.resource_canvas.yview)

        self.resource_list_frame = tk.Frame(self.resource_canvas, bg=SURFACE)
        self.resource_canvas.create_window((0,0), window=self.resource_list_frame,
                                            anchor="nw", tags="rframe")
        self.resource_list_frame.bind("<Configure>", lambda e: self.resource_canvas.configure(
            scrollregion=self.resource_canvas.bbox("all")))
        self.resource_canvas.bind("<Configure>", lambda e: self.resource_canvas.itemconfig(
            "rframe", width=e.width))

    def _build_center(self, parent):
        center = tk.Frame(parent, bg=BG)
        center.pack(side="left", fill="both", expand=True)

        # ── Row 1 toolbar: location / map ─────────────────────────────────────
        toolbar = tk.Frame(center, bg=SURFACE, height=44,
                           highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="LIVE OPERATIONS MAP",
                 font=("Courier",9), bg=SURFACE, fg=MUTED).pack(side="left", padx=12, pady=12)

        tk.Button(toolbar, text="📍 MY LOCATION",
                  font=("Courier",10,"bold"), bg=ACCENT, fg="white",
                  activebackground="#c1121f", relief="flat", cursor="hand2",
                  command=self._locate_me).pack(side="left", padx=8, ipady=4)

        self.loc_label = tk.Label(toolbar, text="Click to use real-time location",
                                  font=("Courier",9), bg=SURFACE, fg=MUTED)
        self.loc_label.pack(side="left")

        tk.Button(toolbar, text="🗺 OPEN MAP IN BROWSER",
                  font=("Courier",10), bg=SURFACE2, fg=ACCENT3,
                  activebackground=BORDER, relief="flat", cursor="hand2",
                  command=self._open_full_map).pack(side="right", padx=8, ipady=4)

        # ── Row 2 toolbar: algorithm buttons ──────────────────────────────────
        algo_bar = tk.Frame(center, bg="#0d1520", height=40,
                            highlightbackground=BORDER, highlightthickness=1)
        algo_bar.pack(fill="x")
        algo_bar.pack_propagate(False)

        tk.Label(algo_bar, text="ALGORITHMS:",
                 font=("Courier",8), bg="#0d1520", fg=MUTED).pack(side="left", padx=10, pady=10)

        tk.Button(algo_bar, text="⚡ SHORTEST PATH",
                  font=("Courier",9,"bold"), bg="#1a3a5c", fg=ACCENT3,
                  activebackground="#234d7a", relief="flat", cursor="hand2",
                  command=self._run_dijkstra).pack(side="left", padx=3, ipady=5, ipadx=6)

        tk.Button(algo_bar, text="✖ CLEAR",
                  font=("Courier",9), bg="#1a1a1a", fg=MUTED,
                  activebackground=BORDER, relief="flat", cursor="hand2",
                  command=self._clear_algo).pack(side="left", padx=3, ipady=5, ipadx=4)

        # Algo status label
        self.algo_status = tk.Label(algo_bar, text="",
                                     font=("Courier",8), bg="#0d1520", fg=ACCENT2)
        self.algo_status.pack(side="right", padx=12)

        # ── Map canvas ────────────────────────────────────────────────────────
        self.map_canvas = tk.Canvas(center, bg="#0d1b2a", highlightthickness=0)
        self.map_canvas.pack(fill="both", expand=True)
        self.map_canvas.bind("<Configure>", self._redraw_map)

        # Map data
        self.user_pos      = None
        self.map_disasters = []
        self.map_resources = []
        # Overlay layers (drawn on top of base map, preserved across redraws)
        self._overlay_items = []   # canvas item ids for algorithm overlays

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=SURFACE, width=220,
                         highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="▸ LIVE STATS",
                 font=("Courier",9), bg=SURFACE, fg=MUTED).pack(anchor="w", padx=10, pady=(10,4))

        # Stat cards
        self.stat_vars = {
            "active":    tk.StringVar(value="—"),
            "resolved":  tk.StringVar(value="—"),
            "resources": tk.StringVar(value="—"),
            "deployed":  tk.StringVar(value="—"),
        }
        stat_defs = [
            ("ACTIVE DISASTERS", "active",    ACCENT),
            ("RESOLVED",         "resolved",  SUCCESS),
            ("TOTAL RESOURCES",  "resources", ACCENT3),
            ("DEPLOYED",         "deployed",  ACCENT2),
        ]
        for lbl, key, color in stat_defs:
            card = tk.Frame(right, bg=SURFACE2,
                            highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", padx=8, pady=4)
            tk.Label(card, textvariable=self.stat_vars[key],
                     font=("Courier",32,"bold"), bg=SURFACE2,
                     fg=color).pack(pady=(8,2))
            tk.Label(card, text=lbl, font=("Courier",8),
                     bg=SURFACE2, fg=MUTED).pack(pady=(0,8))

        # Nearest disaster box
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=8, pady=8)
        tk.Label(right, text="▸ NEAREST DISASTER",
                 font=("Courier",9), bg=SURFACE, fg=MUTED).pack(anchor="w", padx=10, pady=(0,4))

        self.nearest_frame = tk.Frame(right, bg=SURFACE2,
                                       highlightbackground=ACCENT,
                                       highlightthickness=1)
        self.nearest_frame.pack(fill="x", padx=8)

        self.n_dist  = tk.StringVar(value="—")
        self.n_name  = tk.StringVar(value="Enable location")
        self.n_gmaps = tk.StringVar(value="")
        self.n_osm   = tk.StringVar(value="")

        tk.Label(self.nearest_frame, textvariable=self.n_dist,
                 font=("Courier",28,"bold"), bg=SURFACE2, fg=ACCENT2).pack(pady=(10,0))
        tk.Label(self.nearest_frame, text="KM AWAY",
                 font=("Courier",8), bg=SURFACE2, fg=MUTED).pack()
        tk.Label(self.nearest_frame, textvariable=self.n_name,
                 font=("Courier",10,"bold"), bg=SURFACE2, fg=TEXT,
                 wraplength=190).pack(pady=(4,8))

        tk.Button(self.nearest_frame, text="🗺 GOOGLE MAPS",
                  font=("Courier",9,"bold"), bg=ACCENT, fg="white",
                  activebackground="#c1121f", relief="flat", cursor="hand2",
                  command=lambda: webbrowser.open(self.n_gmaps.get()) if self.n_gmaps.get() else None
                  ).pack(fill="x", padx=8, ipady=5)
        tk.Button(self.nearest_frame, text="🌍 OPENSTREETMAP",
                  font=("Courier",9), bg=SURFACE2, fg=ACCENT3,
                  activebackground=BORDER, relief="flat", cursor="hand2",
                  command=lambda: webbrowser.open(self.n_osm.get()) if self.n_osm.get() else None
                  ).pack(fill="x", padx=8, ipady=5, pady=(4,8))

        # Legend
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=8, pady=8)
        tk.Label(right, text="▸ SEVERITY LEGEND",
                 font=("Courier",9), bg=SURFACE, fg=MUTED).pack(anchor="w", padx=10, pady=(0,4))
        for sev, color, label in [
            (5, ACCENT,  "CRITICAL"), (4, ACCENT2, "HIGH"),
            (3, WARNING, "MEDIUM"),   (2, SUCCESS, "LOW"), (1, ACCENT3, "MONITOR")
        ]:
            row = tk.Frame(right, bg=SURFACE)
            row.pack(fill="x", padx=10, pady=1)
            tk.Canvas(row, width=12, height=12, bg=SURFACE,
                      highlightthickness=0).pack(side="left")
            c = tk.Canvas(row, width=12, height=12, bg=color,
                          highlightthickness=0)
            c.pack(side="left")
            tk.Label(row, text=f" {sev} — {label}",
                     font=("Courier",9), bg=SURFACE, fg=MUTED).pack(side="left")

        # ── Algorithm legend ──────────────────────────────────────────────────
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=8, pady=8)
        tk.Label(right, text="▸ ALGORITHM LEGEND",
                 font=("Courier",9), bg=SURFACE, fg=MUTED).pack(anchor="w", padx=10, pady=(0,4))

        algo_legend = [
            ("#00d4ff", "━━", "Dijkstra Path"),
            ("#ffffff", "●",  "City Node"),
            ("#e63946", "●",  "Start Node"),
        ]
        for color, sym, lbl in algo_legend:
            row = tk.Frame(right, bg=SURFACE)
            row.pack(fill="x", padx=10, pady=1)
            tk.Label(row, text=sym, font=("Courier",10,"bold"),
                     bg=SURFACE, fg=color, width=3).pack(side="left")
            tk.Label(row, text=lbl, font=("Courier",8),
                     bg=SURFACE, fg=MUTED).pack(side="left")

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=ACCENT, height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.ticker_text = ("⚠ DISASTER MANAGEMENT RELIEF SYSTEM ACTIVE  |  "
                            "🚨 EMERGENCY HOTLINE: 1078 (NDMA)  |  "
                            "📡 REAL-TIME TRACKING ENABLED  |  "
                            "🆘 FOLLOW OFFICIAL CHANNELS FOR UPDATES  |  "
                            "⚠ ALL ACTIVE INCIDENTS MONITORED  |  ")
        self.ticker_label = tk.Label(bar, text=self.ticker_text * 3,
                                     font=("Courier", 9), bg=ACCENT, fg="white")
        self.ticker_label.pack(side="left", pady=4)
        self._animate_ticker(0)

    # ── Canvas Map ────────────────────────────────────────────────────────────
    def _lat_lon_to_xy(self, lat, lon, w, h):
        """Simple equirectangular projection bounded to India region."""
        min_lat, max_lat = 6.0,  38.0
        min_lon, max_lon = 68.0, 98.0
        pad = 30
        x = pad + (lon - min_lon) / (max_lon - min_lon) * (w - 2*pad)
        y = pad + (max_lat - lat) / (max_lat - min_lat) * (h - 2*pad)
        return x, y

    def _city_xy(self, idx, w, h):
        _, lat, lon = CITY_NODES[idx]
        return self._lat_lon_to_xy(lat, lon, w, h)

    def _redraw_map(self, event=None):
        c = self.map_canvas
        c.delete("all")
        w = c.winfo_width() or 800
        h = c.winfo_height() or 500

        # ── Grid ──
        for i in range(0, w, 40):
            c.create_line(i, 0, i, h, fill="#0f1e30", width=1)
        for j in range(0, h, 40):
            c.create_line(0, j, w, j, fill="#0f1e30", width=1)

        # ── Title ──
        c.create_text(w//2, 18, text="▸ INDIA DISASTER MAP — REAL-TIME",
                      font=("Courier", 10), fill=MUTED)

        # ── Graph edges (faint, always drawn) ──────────────────────────────
        n = len(CITY_NODES)
        for i in range(n):
            x1, y1 = self._city_xy(i, w, h)
            for j, _ in CITY_ADJ[i]:
                if j > i:   # draw each edge once
                    x2, y2 = self._city_xy(j, w, h)
                    c.create_line(x1, y1, x2, y2,
                                  fill="#162032", width=1, dash=(2, 6))

        # ── Resource markers ──
        for r in self.map_resources:
            if r.get("status") != "available":
                continue
            x, y = self._lat_lon_to_xy(r["lat"], r["lon"], w, h)
            emoji = RES_ICONS.get(r["type"], "📦")
            c.create_oval(x-8, y-8, x+8, y+8,
                          fill=SURFACE2, outline=SUCCESS, width=2)
            c.create_text(x, y, text=emoji, font=("TkDefaultFont", 9))

        # ── Disaster markers ──
        for d in self.map_disasters:
            if d.get("status") != "active":
                continue
            x, y = self._lat_lon_to_xy(d["lat"], d["lon"], w, h)
            color = SEV_COLORS[d.get("severity", 3)]
            emoji = TYPE_ICONS.get(d["type"], "⚠️")
            r = 14 + d.get("severity", 1) * 2
            c.create_oval(x-r, y-r, x+r, y+r, fill="", outline=color, width=2)
            c.create_oval(x-10, y-10, x+10, y+10,
                          fill=color, outline="white", width=1)
            c.create_text(x, y, text=emoji, font=("TkDefaultFont", 10))
            c.create_text(x, y+18, text=d["name"][:18],
                          font=("Courier", 7), fill=TEXT)

        # ── City nodes (always on top of graph edges) ──────────────────────
        for idx, (name, lat, lon) in enumerate(CITY_NODES):
            x, y = self._lat_lon_to_xy(lat, lon, w, h)
            c.create_oval(x-4, y-4, x+4, y+4,
                          fill="#334155", outline="#94a3b8", width=1,
                          tags=f"city_{idx}")
            c.create_text(x+7, y-7, text=name, font=("Courier", 7),
                          fill="#64748b", anchor="w", tags=f"citylbl_{idx}")

        # ── User location ──
        if self.user_pos:
            lat, lon = self.user_pos
            ux, uy = self._lat_lon_to_xy(lat, lon, w, h)
            c.create_oval(ux-10, uy-10, ux+10, uy+10,
                          fill=ACCENT3, outline="white", width=2)
            c.create_text(ux, uy, text="👤", font=("TkDefaultFont", 9))
            c.create_text(ux, uy+18, text="YOU",
                          font=("Courier", 7, "bold"), fill=ACCENT3)
            if hasattr(self, "_nearest_lat"):
                nx, ny = self._lat_lon_to_xy(
                    self._nearest_lat, self._nearest_lon, w, h)
                c.create_line(ux, uy, nx, ny,
                              fill=ACCENT, width=2, dash=(8, 4))

        # ── Redraw algorithm overlays preserved from animation ──────────────
        self._redraw_algo_overlay(w, h)

    # ── Algorithm Overlay State ───────────────────────────────────────────────
    def _redraw_algo_overlay(self, w, h):
        """Called at end of every _redraw_map to repaint current algo state."""
        c = self.map_canvas
        state = getattr(self, "_algo_state", {})
        algo  = state.get("algo")

        if algo == "dijkstra":
            self._paint_dijkstra_overlay(c, w, h, state)

    def _paint_dijkstra_overlay(self, c, w, h, state):
        user_pos = state.get("user_pos")
        lines = state.get("lines", [])
        nearest_name = state.get("nearest_name", "")
        nearest_distance = state.get("nearest_distance", 0)

        if not user_pos or not lines:
            return

        ux, uy = self._lat_lon_to_xy(user_pos[0], user_pos[1], w, h)

        for line in lines:
            rx, ry = self._lat_lon_to_xy(line["lat"], line["lon"], w, h)
            if line.get("is_nearest"):
                c.create_line(ux, uy, rx, ry, fill=SUCCESS, width=4)
                c.create_oval(rx-10, ry-10, rx+10, ry+10, fill=SUCCESS, outline="white", width=2)
            else:
                c.create_line(ux, uy, rx, ry, fill=ACCENT, width=2, dash=(4, 4))
                c.create_oval(rx-8, ry-8, rx+8, ry+8, fill=ACCENT, outline="white", width=1)

        # Info badge
        c.create_rectangle(w//2-220, 36, w//2+220, 62,
                           fill="#001a2c", outline=SUCCESS, width=2)
        c.create_text(w//2, 49,
                      text=f"Nearest resource name is {nearest_name} and distance is {nearest_distance:.1f} km",
                      font=("Courier",10,"bold"), fill=SUCCESS)

    # ── Algorithm Runners ─────────────────────────────────────────────────────
    def _cancel_animations(self):
        for aid in self._algo_after_ids:
            try: self.after_cancel(aid)
            except Exception: pass
        for aid in self.after_ids:
            try: self.after_cancel(aid)
            except Exception: pass
        self.after_ids.clear()
        self._algo_after_ids.clear()
        self._algo_running = False

    def _clear_algo(self):
        self._cancel_animations()
        self._algo_state = {}
        self.algo_status.config(text="")
        self._redraw_map()
        self.after_ids.clear()  # extra safety

    # ── DIJKSTRA ──────────────────────────────────────────────────────────────
    def _run_dijkstra(self):
        if self._algo_running: return
        self._cancel_animations()

        if not self.user_pos:
            self.algo_status.config(text="⚠ Set your location first", fg=ACCENT)
            return

        user_lat, user_lon = self.user_pos
        resources = [r for r in self.map_resources if r.get("status") == "available"]

        if not resources:
            self.algo_status.config(text="⚠ No available resources", fg=ACCENT)
            return

        lines = []
        nearest = None
        min_dist = float("inf")

        for r in resources:
            d = _haversine(user_lat, user_lon, r["lat"], r["lon"])
            lines.append({
                "lat": r["lat"], "lon": r["lon"],
                "name": r["name"],
                "distance": d,
                "is_nearest": False
            })
            if d < min_dist:
                min_dist = d
                nearest = r

        for line in lines:
            if line["name"] == nearest["name"] and abs(line["distance"] - min_dist) < 0.0001:
                line["is_nearest"] = True

        self._algo_state = {
            "algo": "dijkstra",
            "user_pos": self.user_pos,
            "lines": lines,
            "nearest_name": nearest["name"],
            "nearest_distance": min_dist,
        }

        self._algo_running = True
        self.algo_status.config(
            text=f"⚡ Nearest: {nearest['name']} ({min_dist:.1f} km)",
            fg=SUCCESS
        )
        self._redraw_map()
        self._algo_running = False

    # ── Data Refresh ──────────────────────────────────────────────────────────
    def _refresh_all(self):
        # Stats
        stats = c_get_stats()
        self.stat_vars["active"].set(str(stats.get("active_disasters", "—")))
        self.stat_vars["resolved"].set(str(stats.get("resolved_disasters", "—")))
        self.stat_vars["resources"].set(str(stats.get("total_resources", "—")))
        self.stat_vars["deployed"].set(str(stats.get("deployed_resources", "—")))

        # Disasters
        disasters = c_get_disasters()
        self.map_disasters = disasters
        self._render_disaster_list(disasters)

        # Resources
        resources = c_get_resources()
        self.map_resources = resources
        self._render_resource_list(resources)

        self._redraw_map()

    def _render_disaster_list(self, data):
        for w in self.disaster_list_frame.winfo_children():
            w.destroy()

        active = [d for d in data if d.get("status") == "active"]
        if not active:
            tk.Label(self.disaster_list_frame, text="✓ NO ACTIVE INCIDENTS",
                     font=("Courier",11), bg=SURFACE, fg=SUCCESS).pack(pady=20)
            return

        for d in active:
            self._disaster_card(self.disaster_list_frame, d)

    def _disaster_card(self, parent, d):
        color = SEV_COLORS[d.get("severity", 1)]
        emoji = TYPE_ICONS.get(d["type"], "⚠️")

        card = tk.Frame(parent, bg=SURFACE2,
                        highlightbackground=color, highlightthickness=2)
        card.pack(fill="x", pady=4, padx=4)

        # Header row
        hrow = tk.Frame(card, bg=SURFACE2)
        hrow.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(hrow, text=f"{emoji} {d['name'][:20]}",
                 font=("Courier",11,"bold"), bg=SURFACE2, fg=TEXT).pack(side="left")
        tk.Label(hrow, text=d["type"].upper(),
                 font=("Courier",8), bg=color, fg=BG, padx=4).pack(side="right")

        # Severity bar
        sev = d.get("severity", 1)
        bar_row = tk.Frame(card, bg=SURFACE2)
        bar_row.pack(fill="x", padx=8, pady=2)
        tk.Label(bar_row, text=f"SEV: {'█'*sev}{'░'*(5-sev)}",
                 font=("Courier",9), bg=SURFACE2, fg=color).pack(side="left")

        # Coords
        tk.Label(card, text=f"📍 {d['lat']:.4f}, {d['lon']:.4f}",
                 font=("Courier",8), bg=SURFACE2, fg=MUTED).pack(anchor="w", padx=8)

        # Action buttons
        btn_row = tk.Frame(card, bg=SURFACE2)
        btn_row.pack(fill="x", padx=8, pady=6)

        tk.Button(btn_row, text="🗺 MAPS",
                  font=("Courier",9), bg=SURFACE, fg=ACCENT3,
                  activebackground=BORDER, relief="flat", cursor="hand2",
                  command=lambda lat=d['lat'], lon=d['lon']: webbrowser.open(
                      f"https://www.google.com/maps?q={lat},{lon}"
                  )).pack(side="left", padx=(0,4), ipady=3, ipadx=4)

        if session["role"] == "admin":
            tk.Button(btn_row, text="✖ RESOLVE",
                      font=("Courier",9), bg=ACCENT, fg="white",
                      activebackground="#c1121f", relief="flat", cursor="hand2",
                      command=lambda did=d['id']: self._resolve_disaster(did)
                      ).pack(side="right", ipady=3, ipadx=4)

    def _render_resource_list(self, data):
        for w in self.resource_list_frame.winfo_children():
            w.destroy()

        if not data:
            tk.Label(self.resource_list_frame, text="No resources",
                     font=("Courier",11), bg=SURFACE, fg=MUTED).pack(pady=20)
            return

        for r in data:
            self._resource_card(self.resource_list_frame, r)

    def _resource_card(self, parent, r):
        status_color = {
            "available": SUCCESS, "deployed": WARNING, "exhausted": MUTED
        }.get(r.get("status",""), MUTED)
        emoji = RES_ICONS.get(r["type"], "📦")

        card = tk.Frame(parent, bg=SURFACE2,
                        highlightbackground=status_color, highlightthickness=2)
        card.pack(fill="x", pady=4, padx=4)

        hrow = tk.Frame(card, bg=SURFACE2)
        hrow.pack(fill="x", padx=8, pady=(8,2))
        tk.Label(hrow, text=f"{emoji} {r['name'][:20]}",
                 font=("Courier",11,"bold"), bg=SURFACE2, fg=TEXT).pack(side="left")
        tk.Label(hrow, text=r["status"].upper(),
                 font=("Courier",8), bg=status_color, fg=BG, padx=4).pack(side="right")

        tk.Label(card, text=f"QTY: {r['quantity']} {r['unit']} | {r['type']}",
                 font=("Courier",9), bg=SURFACE2, fg=MUTED).pack(anchor="w", padx=8)
        tk.Label(card, text=f"📍 {r['lat']:.4f}, {r['lon']:.4f}",
                 font=("Courier",8), bg=SURFACE2, fg=MUTED).pack(anchor="w", padx=8, pady=(0,4))

        btn_row = tk.Frame(card, bg=SURFACE2)
        btn_row.pack(fill="x", padx=8, pady=(0,6))

        if session["role"] == "admin":
            tk.Button(btn_row, text="✖ REMOVE",
                      font=("Courier",9), bg=ACCENT, fg="white",
                      activebackground="#c1121f", relief="flat", cursor="hand2",
                      command=lambda rid=r['id']: self._remove_resource(rid)
                      ).pack(side="right", ipady=3, ipadx=4)

    # ── Actions ───────────────────────────────────────────────────────────────
    def _add_disaster(self):
        # Strip values that still hold placeholder text
        PLACEHOLDERS = {"e.g. 19.0760", "e.g. 72.8777",
                        "e.g. Mumbai Coastal Flood"}
        for key in ("name","lat","lon"):
            if self.d_vars[key].get() in PLACEHOLDERS:
                self.d_vars[key].set("")
        try:
            name = self.d_vars["name"].get().strip()
            dtype = self.d_vars["type"].get()
            lat  = float(self.d_vars["lat"].get())
            lon  = float(self.d_vars["lon"].get())
            sev  = int(self.d_vars["sev"].get())
        except (ValueError, TypeError):
            messagebox.showerror("Input Error",
                "Please fill in all fields.\n\n"
                "Name: e.g. Mumbai Coastal Flood\n"
                "Latitude: e.g. 19.0760\n"
                "Longitude: e.g. 72.8777")
            return
        if not name:
            messagebox.showerror("Input Error", "Disaster name is required")
            return
        nid = lib.engine_add_disaster(
            name.encode(), dtype.encode(),
            ctypes.c_double(lat), ctypes.c_double(lon),
            ctypes.c_int(sev)
        )
        if nid > 0:
            for v in self.d_vars.values(): v.set("")
            self.d_vars["type"].set("flood")
            self.d_vars["sev"].set("5")
            self._refresh_all()
        else:
            messagebox.showerror("Error", "Failed to add disaster")

    def _add_resource(self):
        PLACEHOLDERS = {"e.g. 19.0760", "e.g. 72.8777",
                        "e.g. NDRF Team Alpha",
                        "Qty e.g. 50", "Unit e.g. personnel"}
        for key in ("name","lat","lon","qty","unit"):
            if self.r_vars[key].get() in PLACEHOLDERS:
                self.r_vars[key].set("")
        try:
            name = self.r_vars["name"].get().strip()
            rtype = self.r_vars["type"].get()
            lat  = float(self.r_vars["lat"].get())
            lon  = float(self.r_vars["lon"].get())
            qty  = int(self.r_vars["qty"].get())
            unit = self.r_vars["unit"].get().strip()
        except (ValueError, TypeError):
            messagebox.showerror("Input Error",
                "Please fill in all fields.\n\n"
                "Name: e.g. NDRF Team Alpha\n"
                "Latitude: e.g. 19.0760\n"
                "Longitude: e.g. 72.8777\n"
                "Quantity: e.g. 50\n"
                "Unit: e.g. personnel")
            return
        nid = lib.engine_add_resource(
            name.encode(), rtype.encode(),
            ctypes.c_double(lat), ctypes.c_double(lon),
            ctypes.c_int(qty), unit.encode()
        )
        if nid > 0:
            for v in self.r_vars.values(): v.set("")
            self.r_vars["type"].set("rescue_team")
            self._refresh_all()
        else:
            messagebox.showerror("Error", "Failed to add resource")

    def _resolve_disaster(self, did):
        if messagebox.askyesno("Confirm", "Mark this disaster as resolved?"):
            lib.engine_remove_disaster(ctypes.c_int(did))
            self._refresh_all()

    def _remove_resource(self, rid):
        if messagebox.askyesno("Confirm", "Remove this resource?"):
            lib.engine_remove_resource(ctypes.c_int(rid))
            self._refresh_all()

    def _locate_me(self):
        """Open a dialog to enter manual lat/lon (geolocation not available in desktop)."""
        dlg = tk.Toplevel(self)
        dlg.title("Enter Your Location")
        dlg.geometry("360x240")
        dlg.configure(bg=BG)
        dlg.grab_set()

        tk.Label(dlg, text="📍 ENTER YOUR COORDINATES",
                 font=("Courier",12,"bold"), bg=BG, fg=ACCENT2).pack(pady=16)
        tk.Label(dlg, text="(Find your coordinates on Google Maps\nor maps.google.com → right-click → coordinates)",
                 font=("Courier",9), bg=BG, fg=MUTED, justify="center").pack()

        tk.Frame(dlg, bg=BORDER, height=1).pack(fill="x", padx=20, pady=10)

        lat_var = tk.StringVar(value="28.6139")
        lon_var = tk.StringVar(value="77.2090")

        for lbl, var in [("LATITUDE", lat_var), ("LONGITUDE", lon_var)]:
            row = tk.Frame(dlg, bg=BG)
            row.pack(fill="x", padx=24, pady=4)
            tk.Label(row, text=lbl, font=("Courier",9), bg=BG,
                     fg=MUTED, width=12, anchor="w").pack(side="left")
            tk.Entry(row, textvariable=var, font=("Courier",12), bg=SURFACE,
                     fg=TEXT, insertbackground=TEXT, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1,
                     width=16).pack(side="left", ipady=5)

        def do_locate():
            try:
                lat = float(lat_var.get())
                lon = float(lon_var.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid coordinates")
                return
            self.user_pos = (lat, lon)
            self.loc_label.config(
                text=f"📍 {lat:.4f}, {lon:.4f}", fg=ACCENT3)
            data = c_nearest(lat, lon)
            if data.get("found"):
                self.n_dist.set(f"{data['distance_km']:.1f}")
                self.n_name.set(
                    f"{TYPE_ICONS.get(data['type'],'⚠️')} {data['name']}\nSeverity {data['severity']}")
                self.n_gmaps.set(data.get("maps_url", ""))
                self.n_osm.set(data.get("osm_url", ""))
                self._nearest_lat = data["lat"]
                self._nearest_lon = data["lon"]
            self._redraw_map()
            dlg.destroy()

        tk.Button(dlg, text="LOCATE & FIND NEAREST DISASTER",
                  font=("Courier",10,"bold"), bg=ACCENT, fg="white",
                  activebackground="#c1121f", relief="flat", cursor="hand2",
                  command=do_locate).pack(fill="x", padx=24, ipady=8, pady=12)

    def _open_full_map(self):
        """Opens an OpenStreetMap page showing India's disaster region."""
        webbrowser.open("https://www.openstreetmap.org/#map=5/20.5/79.0")

    def _switch_tab(self, tab):
        self.active_tab.set(tab)
        self.disaster_panel.pack_forget()
        self.resource_panel.pack_forget()
        if tab == "disasters":
            self.disaster_panel.pack(fill="both", expand=True)
        else:
            self.resource_panel.pack(fill="both", expand=True)
        for key, btn in self.tab_btns.items():
            btn.config(fg=TEXT if key == tab else MUTED,
                       bg=SURFACE2 if key == tab else SURFACE)

    def _animate_ticker(self, offset):
        try:
            self.ticker_label.place(x=-offset)
        except Exception:
            pass
        w = self.winfo_width() or 1280
        next_offset = (offset + 1) % (w + len(self.ticker_text) * 7)
        aid = self.after(30, self._animate_ticker, next_offset)
        self.after_ids.append(aid)

    def _auto_refresh(self):
        self._refresh_all()
        aid = self.after(30000, self._auto_refresh)  # every 30s
        self.after_ids.append(aid)

    def _field(self, parent, placeholder, var):
        """Entry with grey placeholder text that clears on focus."""
        e = tk.Entry(parent, font=("Courier", 10),
                     bg=BG, fg=MUTED, insertbackground=TEXT, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1)
        e.insert(0, placeholder)
        e.pack(fill="x", ipady=5, pady=2)

        def on_focus_in(event, _e=e, _ph=placeholder, _v=var):
            if _e.get() == _ph:
                _e.delete(0, "end")
                _e.config(fg=TEXT)
                _v.set("")

        def on_focus_out(event, _e=e, _ph=placeholder, _v=var):
            if _e.get().strip() == "":
                _e.delete(0, "end")
                _e.insert(0, _ph)
                _e.config(fg=MUTED)
                _v.set("")
            else:
                _v.set(_e.get())

        def on_key(event, _e=e, _v=var):
            if _e.cget("fg") == TEXT:
                _v.set(_e.get())

        e.bind("<FocusIn>",   on_focus_in)
        e.bind("<FocusOut>",  on_focus_out)
        e.bind("<KeyRelease>", on_key)
        return e

    def _ph_entry(self, parent, placeholder, var, width=12, side="left", padx=(0,4)):
        """Compact inline placeholder entry for lat/lon/qty/unit rows."""
        e = tk.Entry(parent, font=("Courier", 10), width=width,
                     bg=BG, fg=MUTED, insertbackground=TEXT, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1)
        e.insert(0, placeholder)
        e.pack(side=side, padx=padx, ipady=4)

        def on_focus_in(event, _e=e, _ph=placeholder, _v=var):
            if _e.get() == _ph:
                _e.delete(0, "end")
                _e.config(fg=TEXT)
                _v.set("")

        def on_focus_out(event, _e=e, _ph=placeholder, _v=var):
            if _e.get().strip() == "":
                _e.delete(0, "end")
                _e.insert(0, _ph)
                _e.config(fg=MUTED)
                _v.set("")
            else:
                _v.set(_e.get())

        def on_key(event, _e=e, _v=var):
            if _e.cget("fg") == TEXT:
                _v.set(_e.get())

        e.bind("<FocusIn>",   on_focus_in)
        e.bind("<FocusOut>",  on_focus_out)
        e.bind("<KeyRelease>", on_key)
        return e

    def destroy(self):
        self._cancel_animations()
        session.clear()
        super().destroy()

    def _logout(self):
        self.destroy()
        LoginWindow().mainloop()


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    LoginWindow().mainloop()
