import customtkinter as ctk
import pyodbc
from tkinter import ttk, messagebox
import tkinter as tk
from datetime import datetime
import json
import os
import base64
import math

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Palette (Catppuccin Mocha) ─────────────────────────────────────────────
BG      = "#1e1e2e"
SIDEBAR = "#181825"
SRF0    = "#313244"
SRF1    = "#45475a"
TXT     = "#cdd6f4"
SUB     = "#a6adc8"
ACC     = "#cba6f7"
GRN     = "#a6e3a1"
RED     = "#f38ba8"
YEL     = "#f9e2af"

SYSTEM_DBS = {"master", "tempdb", "model", "msdb"}


def _apply_styles():
    s = ttk.Style()
    s.theme_use("clam")
    for name, bg, sel in [("Data", BG, SRF1), ("Nav", SIDEBAR, SRF0)]:
        s.configure(f"{name}.Treeview",
                    background=bg, foreground=TXT, rowheight=48,
                    fieldbackground=bg, borderwidth=0, font=("Segoe UI", 16))
        s.configure(f"{name}.Treeview.Heading",
                    background=SRF0, foreground=ACC,
                    relief="flat", font=("Segoe UI", 15, "bold"))
        s.map(f"{name}.Treeview", background=[("selected", sel)])
    s.configure("Nav.Treeview.Heading", background=SIDEBAR, foreground=SIDEBAR)
    for o in ("Vertical", "Horizontal"):
        s.configure(f"{o}.TScrollbar",
                    background=SRF0, troughcolor=BG,
                    arrowcolor=TXT, borderwidth=0)


# ══════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SQL Explorer")
        self.geometry("1450x860")
        self.minsize(1100, 700)
        _apply_styles()

        self.conn:   pyodbc.Connection | None = None
        self.cursor: pyodbc.Cursor     | None = None

        # Current browse context
        self._cur_db     = ""
        self._cur_schema = ""
        self._cur_table  = ""
        self._cur_cols:  list[dict] = []   # {name, type, nullable, identity}
        self._cur_pk:    list[str]  = []

        # Sort state
        self._sort_col = ""
        self._sort_dir = ""   # "" | "asc" | "desc"

        # Col-info toggle
        self._show_col_info = False

        # All loaded rows (unfiltered) for search
        self._cur_rows: list = []

        # ERD stored schema data
        self._erd_data = None

        # Connection form vars
        self.v_server       = ctk.StringVar(value="localhost")
        self.v_db           = ctk.StringVar(value="")
        self.v_auth         = ctk.StringVar(value="windows")
        self.v_user         = ctk.StringVar(value="sa")
        self.v_pass         = ctk.StringVar(value="")
        self.v_save_pass    = ctk.BooleanVar(value=False)
        self.v_auto_connect = ctk.BooleanVar(value=False)

        self._load_session()   # pre-fill fields from saved session

        self._pages: dict[str, ctk.CTkFrame] = {}
        self._nav_btns: dict[str, ctk.CTkButton] = {}

        self._build_shell()
        self._build_connection_page()
        self._build_browser_page()
        self._build_query_page()
        self._build_viz_page()
        self._show("connection")

        # Auto-connect after UI is ready
        if self.v_auto_connect.get():
            self.after(300, self._connect)

    # ── Shell ──────────────────────────────────────────────────────────────
    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sb = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=SIDEBAR)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(20, weight=1)

        ctk.CTkLabel(sb, text="SQL Explorer",
                     font=ctk.CTkFont("Segoe UI", 17, "bold"),
                     text_color=ACC).grid(row=0, column=0, padx=16, pady=(28, 6))

        self._status_lbl = ctk.CTkLabel(sb, text="⬤  Not connected",
                                         font=ctk.CTkFont("Segoe UI", 11),
                                         text_color=RED)
        self._status_lbl.grid(row=1, column=0, padx=16, pady=(0, 20))

        ctk.CTkFrame(sb, height=1, fg_color=SRF0).grid(
            row=2, column=0, sticky="ew", padx=12, pady=(0, 14))

        for i, (icon, label, key) in enumerate([
            ("⚙", "Connection",   "connection"),
            ("🗄", "Data Browser", "browser"),
            ("▶", "Query Runner", "query"),
            ("🗺", "Visualize",    "viz"),
        ]):
            b = ctk.CTkButton(
                sb, text=f"{icon}  {label}", anchor="w", height=44,
                corner_radius=8, fg_color="transparent", hover_color=SRF0,
                font=ctk.CTkFont("Segoe UI", 13),
                command=lambda k=key: self._show(k),
            )
            b.grid(row=i + 3, column=0, padx=12, pady=3, sticky="ew")
            self._nav_btns[key] = b

        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color=BG)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

    def _new_page(self, key: str) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self._content, corner_radius=0, fg_color="transparent")
        f.grid(row=0, column=0, sticky="nsew")
        f.grid_remove()
        self._pages[key] = f
        return f

    def _show(self, key: str):
        for f in self._pages.values():
            f.grid_remove()
        self._pages[key].grid()
        for k, b in self._nav_btns.items():
            b.configure(fg_color=SRF0 if k == key else "transparent")

    def _requires_conn(self) -> bool:
        if not self.conn:
            messagebox.showwarning("Not connected",
                                   "Go to ⚙ Connection and connect first.")
            return False
        return True

    # ══════════════════════════════════════════════════════════════════════
    # CONNECTION PAGE
    # ══════════════════════════════════════════════════════════════════════
    def _build_connection_page(self):
        page = self._new_page("connection")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(page, text="Database Connection",
                     font=ctk.CTkFont("Segoe UI", 26, "bold"),
                     text_color=TXT).grid(row=0, column=0, padx=40, pady=(40, 4), sticky="w")
        ctk.CTkLabel(page, text="Connect to any SQL Server instance — all databases will be discovered automatically",
                     font=ctk.CTkFont("Segoe UI", 12), text_color=SUB).grid(
            row=1, column=0, padx=40, pady=(0, 24), sticky="w")

        card = ctk.CTkFrame(page, fg_color=SIDEBAR, corner_radius=12)
        card.grid(row=2, column=0, padx=40, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        fields = [
            ("Server / Instance", self.v_server, False,
             "e.g.  localhost  ·  .\\SQLEXPRESS  ·  SERVER\\INSTANCE"),
            ("Initial Database",  self.v_db,     False,
             "optional — leave blank, all databases shown"),
            ("Username",          self.v_user,   False, "SQL Server auth only"),
            ("Password",          self.v_pass,   True,  "SQL Server auth only"),
        ]
        for i, (lbl, var, hide, hint) in enumerate(fields):
            ctk.CTkLabel(card, text=lbl, text_color=SUB,
                         font=ctk.CTkFont("Segoe UI", 12)).grid(
                row=i, column=0, padx=(24, 12), pady=10, sticky="w")
            ctk.CTkEntry(card, textvariable=var, show="●" if hide else "",
                         placeholder_text=hint, height=36).grid(
                row=i, column=1, padx=(0, 24), pady=10, sticky="ew")

        ctk.CTkLabel(card, text="Authentication", text_color=SUB,
                     font=ctk.CTkFont("Segoe UI", 12)).grid(
            row=4, column=0, padx=(24, 12), pady=10, sticky="w")
        ar = ctk.CTkFrame(card, fg_color="transparent")
        ar.grid(row=4, column=1, padx=(0, 24), pady=10, sticky="w")
        ctk.CTkRadioButton(ar, text="Windows Auth",
                           variable=self.v_auth, value="windows").pack(side="left", padx=(0, 24))
        ctk.CTkRadioButton(ar, text="SQL Server Auth",
                           variable=self.v_auth, value="sql").pack(side="left")

        # Options row
        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.grid(row=5, column=0, columnspan=2, padx=24, pady=(8, 4), sticky="w")
        ctk.CTkCheckBox(opts, text="Save password",
                        variable=self.v_save_pass).pack(side="left", padx=(0, 28))
        ctk.CTkCheckBox(opts, text="Auto-connect on startup",
                        variable=self.v_auto_connect).pack(side="left")

        ctk.CTkButton(card, text="Connect to SQL Server", height=44,
                      font=ctk.CTkFont("Segoe UI", 14, "bold"),
                      command=self._connect).grid(
            row=6, column=0, columnspan=2, padx=24, pady=(4, 24), sticky="ew")

        self._log_box = ctk.CTkTextbox(page, height=200,
                                        font=ctk.CTkFont("Courier New", 11),
                                        fg_color="#11111b", text_color=GRN)
        self._log_box.grid(row=3, column=0, padx=40, pady=(20, 40), sticky="nsew")
        self._log_box.configure(state="disabled")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"[{ts}]  {msg}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _connect(self):
        srv = self.v_server.get().strip()
        if not srv:
            messagebox.showerror("Error", "Server name is required."); return
        db = self.v_db.get().strip() or "master"
        try:
            if self.v_auth.get() == "windows":
                cs = (f"DRIVER={{SQL Server}};SERVER={srv};"
                      f"DATABASE={db};Trusted_Connection=yes")
            else:
                cs = (f"DRIVER={{SQL Server}};SERVER={srv};DATABASE={db};"
                      f"UID={self.v_user.get()};PWD={self.v_pass.get()}")
            if self.conn:
                try: self.conn.close()
                except Exception: pass
            self.conn   = pyodbc.connect(cs, timeout=8)
            self.cursor = self.conn.cursor()
            self._log(f"✓  Connected  →  {srv}  (initial DB: {db})")
            self._status_lbl.configure(text=f"⬤  {srv}", text_color=GRN)
            self._save_session()
            self._refresh_nav_tree()
            self._populate_query_db_list()
        except pyodbc.Error as exc:
            self._log(f"✗  {exc}")
            messagebox.showerror("Connection failed", str(exc))

    def _save_session(self):
        data = {
            "server":       self.v_server.get().strip(),
            "db":           self.v_db.get().strip(),
            "auth":         self.v_auth.get(),
            "user":         self.v_user.get().strip(),
            "password":     base64.b64encode(self.v_pass.get().encode()).decode()
                            if self.v_save_pass.get() else "",
            "save_pass":    self.v_save_pass.get(),
            "auto_connect": self.v_auto_connect.get(),
        }
        try:
            with open(SESSION_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_session(self):
        if not os.path.exists(SESSION_FILE):
            return
        try:
            with open(SESSION_FILE) as f:
                data = json.load(f)
            self.v_server.set(data.get("server", "localhost"))
            self.v_db.set(data.get("db", ""))
            self.v_auth.set(data.get("auth", "windows"))
            self.v_user.set(data.get("user", "sa"))
            self.v_save_pass.set(data.get("save_pass", False))
            self.v_auto_connect.set(data.get("auto_connect", False))
            if data.get("save_pass") and data.get("password"):
                self.v_pass.set(
                    base64.b64decode(data["password"].encode()).decode())
        except Exception:
            pass   # corrupt session file — silently ignore

    # ══════════════════════════════════════════════════════════════════════
    # DATA BROWSER PAGE
    # ══════════════════════════════════════════════════════════════════════
    def _build_browser_page(self):
        page = self._new_page("browser")
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(0, weight=1)

        # ── Left nav panel ─────────────────────────────────────────────────
        nav = ctk.CTkFrame(page, width=420, corner_radius=0, fg_color=SIDEBAR)
        nav.grid(row=0, column=0, sticky="nsew")
        nav.grid_propagate(False)
        nav.grid_rowconfigure(2, weight=1)
        nav.grid_columnconfigure(0, weight=1)

        nh = ctk.CTkFrame(nav, fg_color="transparent")
        nh.grid(row=0, column=0, sticky="ew", padx=10, pady=(14, 4))
        nh.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(nh, text="Databases & Tables",
                     font=ctk.CTkFont("Segoe UI", 17, "bold"),
                     text_color=ACC).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(nh, text="↻", width=30, height=28,
                      command=self._refresh_nav_tree).grid(row=0, column=1)

        self._nav_search = ctk.CTkEntry(nav, placeholder_text="🔍  filter tables…",
                                         height=44, font=ctk.CTkFont("Segoe UI", 15))
        self._nav_search.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="ew")
        self._nav_search.bind("<KeyRelease>", lambda e: self._filter_nav())

        ntf = ctk.CTkFrame(nav, fg_color=SIDEBAR, corner_radius=0)
        ntf.grid(row=2, column=0, sticky="nsew")
        ntf.grid_rowconfigure(0, weight=1)
        ntf.grid_columnconfigure(0, weight=1)

        self._nav_tree = ttk.Treeview(ntf, style="Nav.Treeview", show="tree",
                                       selectmode="browse")
        nvsb = ttk.Scrollbar(ntf, orient="vertical", command=self._nav_tree.yview)
        self._nav_tree.configure(yscrollcommand=nvsb.set)
        self._nav_tree.grid(row=0, column=0, sticky="nsew")
        nvsb.grid(row=0, column=1, sticky="ns")
        self._nav_tree.bind("<<TreeviewSelect>>", self._on_nav_select)
        self._nav_tree.bind("<<TreeviewOpen>>",   self._on_db_expand)

        # ── Right data panel ───────────────────────────────────────────────
        dp = ctk.CTkFrame(page, corner_radius=0, fg_color=BG)
        dp.grid(row=0, column=1, sticky="nsew")
        dp.grid_rowconfigure(2, weight=1)
        dp.grid_columnconfigure(0, weight=1)

        # Toolbar  (2 rows so buttons never overflow)
        tb = ctk.CTkFrame(dp, fg_color=SIDEBAR, corner_radius=0)
        tb.grid(row=0, column=0, sticky="ew")
        tb.grid_columnconfigure(1, weight=1)

        # Row 0 — table name + row count
        self._table_lbl = ctk.CTkLabel(tb, text="← Select a table",
                                        font=ctk.CTkFont("Segoe UI", 18, "bold"),
                                        text_color=ACC)
        self._table_lbl.grid(row=0, column=0, padx=16, pady=(12, 2), sticky="w")

        self._row_lbl = ctk.CTkLabel(tb, text="", text_color=SUB,
                                      font=ctk.CTkFont("Segoe UI", 15))
        self._row_lbl.grid(row=0, column=1, padx=8, pady=(12, 2), sticky="w")

        # Row 1 — limit selector + action buttons
        btns = ctk.CTkFrame(tb, fg_color="transparent")
        btns.grid(row=1, column=0, columnspan=3, padx=12, pady=(2, 10), sticky="w")

        ctk.CTkLabel(btns, text="Limit:", text_color=SUB).pack(side="left", padx=(0, 4))
        self._limit_var = ctk.StringVar(value="500")
        ctk.CTkComboBox(btns, variable=self._limit_var,
                         values=["100", "500", "1000", "5000", "ALL"],
                         width=90, height=34).pack(side="left", padx=(0, 16))

        for txt, color, cmd in [
            ("↻  Refresh", None,      self._refresh_table),
            ("➕  Insert",  None,      self._show_insert_modal),
            ("✏  Edit",    None,      self._show_edit_modal),
            ("🗑  Delete",  "#e06c75", self._confirm_delete),
        ]:
            kw = {"fg_color": color, "hover_color": "#be5046"} if color else {}
            ctk.CTkButton(btns, text=txt, height=34, width=110, **kw,
                          command=cmd).pack(side="left", padx=3)

        # Separator + info toggle button
        ctk.CTkFrame(btns, width=1, height=30, fg_color=SRF0).pack(
            side="left", padx=10)
        self._info_btn = ctk.CTkButton(
            btns, text="ℹ  Column Info", height=34, width=130,
            fg_color=SRF0, hover_color=SRF1,
            command=self._toggle_col_info)
        self._info_btn.pack(side="left", padx=3)

        # ── Search bar (row=1) ─────────────────────────────────────────────
        sf = ctk.CTkFrame(dp, fg_color=SIDEBAR, corner_radius=0)
        sf.grid(row=1, column=0, sticky="ew")
        sf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(sf, text="🔍  Search rows:", text_color=SUB,
                     font=ctk.CTkFont("Segoe UI", 13)).grid(
            row=0, column=0, padx=(14, 6), pady=8)
        self._search_var = ctk.StringVar()
        ctk.CTkEntry(sf, textvariable=self._search_var,
                     placeholder_text="Type to filter all columns…",
                     height=34, font=ctk.CTkFont("Segoe UI", 13)).grid(
            row=0, column=1, padx=(0, 6), pady=8, sticky="ew")
        ctk.CTkButton(sf, text="✕ Clear", width=80, height=34, fg_color=SRF0,
                      command=lambda: self._search_var.set("")).grid(
            row=0, column=2, padx=(0, 12), pady=8)
        self._search_var.trace_add("write", lambda *_: self._search_table())

        # ── Data treeview (row=2) ──────────────────────────────────────────
        self._dtf = ctk.CTkFrame(dp, fg_color=BG, corner_radius=0)
        self._dtf.grid(row=2, column=0, sticky="nsew")
        self._dtf.grid_rowconfigure(0, weight=1)
        self._dtf.grid_columnconfigure(0, weight=1)

        self._data_tree = ttk.Treeview(self._dtf, style="Data.Treeview",
                                        show="headings", selectmode="extended")
        dv = ttk.Scrollbar(self._dtf, orient="vertical",   command=self._data_tree.yview)
        dh = ttk.Scrollbar(self._dtf, orient="horizontal", command=self._data_tree.xview)
        self._data_tree.configure(yscrollcommand=dv.set, xscrollcommand=dh.set)
        self._data_tree.grid(row=0, column=0, sticky="nsew")
        dv.grid(row=0, column=1, sticky="ns")
        dh.grid(row=1, column=0, sticky="ew")

        # ── Column info panel (row=2, hidden by default) ───────────────────
        self._cif = ctk.CTkFrame(dp, fg_color=BG, corner_radius=0)
        self._cif.grid(row=2, column=0, sticky="nsew")
        self._cif.grid_rowconfigure(0, weight=1)
        self._cif.grid_columnconfigure(0, weight=1)
        self._cif.grid_remove()   # hidden until toggled

        _ci_cols = ["Column", "Type", "Nullable", "Primary Key", "Identity"]
        self._ci_tree = ttk.Treeview(self._cif, style="Data.Treeview",
                                      columns=_ci_cols, show="headings",
                                      selectmode="none")
        for c, w in zip(_ci_cols, [220, 130, 110, 120, 110]):
            self._ci_tree.heading(c, text=c)
            self._ci_tree.column(c, width=w, minwidth=80, stretch=True)
        ci_vsb = ttk.Scrollbar(self._cif, orient="vertical",
                                command=self._ci_tree.yview)
        self._ci_tree.configure(yscrollcommand=ci_vsb.set)
        self._ci_tree.grid(row=0, column=0, sticky="nsew")
        ci_vsb.grid(row=0, column=1, sticky="ns")

    # ── DB / catalog helpers ───────────────────────────────────────────────
    def _get_databases(self) -> list[str]:
        self.cursor.execute(
            "SELECT name FROM sys.databases "
            "WHERE HAS_DBACCESS(name) = 1 ORDER BY name"
        )
        return [r[0] for r in self.cursor.fetchall()]

    def _get_tables(self, db: str) -> list[tuple[str, str]]:
        self.cursor.execute(
            f"SELECT TABLE_SCHEMA, TABLE_NAME "
            f"FROM [{db}].INFORMATION_SCHEMA.TABLES "
            f"WHERE TABLE_TYPE = 'BASE TABLE' "
            f"ORDER BY TABLE_SCHEMA, TABLE_NAME"
        )
        return [(r[0], r[1]) for r in self.cursor.fetchall()]

    def _get_columns(self, db: str, schema: str, table: str) -> list[dict]:
        self.cursor.execute(
            f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, "
            f"COLUMNPROPERTY(OBJECT_ID('[{db}].[{schema}].[{table}]'), "
            f"COLUMN_NAME, 'IsIdentity') "
            f"FROM [{db}].INFORMATION_SCHEMA.COLUMNS "
            f"WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? "
            f"ORDER BY ORDINAL_POSITION",
            schema, table,
        )
        return [
            {
                "name":     r[0],
                "type":     r[1],
                "nullable": r[2] == "YES",
                "identity": bool(r[3]),
            }
            for r in self.cursor.fetchall()
        ]

    def _get_pk(self, db: str, schema: str, table: str) -> list[str]:
        self.cursor.execute(
            f"SELECT kcu.COLUMN_NAME "
            f"FROM [{db}].INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
            f"JOIN [{db}].INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
            f"  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
            f" AND tc.TABLE_SCHEMA    = kcu.TABLE_SCHEMA "
            f" AND tc.TABLE_NAME      = kcu.TABLE_NAME "
            f"WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' "
            f"  AND tc.TABLE_SCHEMA = ? AND tc.TABLE_NAME = ? "
            f"ORDER BY kcu.ORDINAL_POSITION",
            schema, table,
        )
        return [r[0] for r in self.cursor.fetchall()]

    # ── Nav tree ───────────────────────────────────────────────────────────
    def _refresh_nav_tree(self):
        if not self._requires_conn(): return
        self._nav_search.delete(0, "end")
        self._rebuild_nav(term="")

    def _rebuild_nav(self, term: str):
        self._nav_tree.delete(*self._nav_tree.get_children())
        if not self.conn: return
        try:
            dbs = self._get_databases()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        for db in dbs:
            icon = "🔒" if db.lower() in SYSTEM_DBS else "🗄"
            if not term:
                # Lazy-load: just show the db node with a dummy child
                iid = self._nav_tree.insert(
                    "", "end", iid=f"db::{db}",
                    text=f"  {icon}  {db}", open=False, tags=("db",))
                self._nav_tree.insert(iid, "end", text="  …", tags=("dummy",))
            else:
                # Eager-load for filtering
                try:
                    tables = self._get_tables(db)
                except Exception:
                    tables = []
                matches = [
                    (s, t) for s, t in tables
                    if term in f"{s}.{t}".lower() or term in db.lower()
                ]
                if not matches:
                    continue
                iid = self._nav_tree.insert(
                    "", "end", iid=f"db::{db}",
                    text=f"  {icon}  {db}", open=True, tags=("db",))
                for schema, tbl in matches:
                    self._nav_tree.insert(
                        iid, "end",
                        iid=f"tbl::{db}::{schema}::{tbl}",
                        text=f"   📋  {schema}.{tbl}",
                        tags=("table",))

    def _filter_nav(self):
        term = self._nav_search.get().strip().lower()
        self._rebuild_nav(term=term)

    def _on_db_expand(self, _event):
        sel = self._nav_tree.focus()
        if not sel.startswith("db::"):
            return
        children = self._nav_tree.get_children(sel)
        # Only expand-load if children are still the dummy placeholder
        if not (len(children) == 1 and
                "dummy" in self._nav_tree.item(children[0], "tags")):
            return
        self._nav_tree.delete(children[0])
        db = sel[4:]
        try:
            tables = self._get_tables(db)
            for schema, tbl in tables:
                self._nav_tree.insert(
                    sel, "end",
                    iid=f"tbl::{db}::{schema}::{tbl}",
                    text=f"   📋  {schema}.{tbl}",
                    tags=("table",))
            if not tables:
                self._nav_tree.insert(sel, "end",
                                      text="   (no tables)", tags=("empty",))
        except Exception as e:
            self._nav_tree.insert(sel, "end",
                                  text=f"   ⚠  {e}", tags=("error",))

    def _on_nav_select(self, _event):
        sel = self._nav_tree.focus()
        if not sel.startswith("tbl::"):
            return
        _, db, schema, table = sel.split("::", 3)
        self._cur_db     = db
        self._cur_schema = schema
        self._cur_table  = table
        self._load_table()

    # ── Table data ─────────────────────────────────────────────────────────
    def _load_table(self):
        if not self._cur_table: return
        db, schema, table = self._cur_db, self._cur_schema, self._cur_table
        try:
            self._cur_cols = self._get_columns(db, schema, table)
            self._cur_pk   = self._get_pk(db, schema, table)
            cols = [c["name"] for c in self._cur_cols]

            limit = self._limit_var.get()
            top   = f"TOP {limit} " if limit != "ALL" else ""
            self.cursor.execute(
                f"SELECT {top}* FROM [{db}].[{schema}].[{table}]")
            rows = self.cursor.fetchall()

            # Reset sort state on fresh load
            self._sort_col = ""
            self._sort_dir = ""

            self._data_tree["columns"] = cols
            for col in cols:
                self._data_tree.heading(col, text=col,
                                        command=lambda c=col: self._sort_col_click(c))
                self._data_tree.column(col, width=200, minwidth=100, stretch=True)
            self._cur_rows = [
                [v if v is not None else "NULL" for v in row]
                for row in rows
            ]
            self._search_var.set("")   # clear search on new table load
            self._data_tree.delete(*self._data_tree.get_children())
            for row_vals in self._cur_rows:
                self._data_tree.insert("", "end", values=row_vals)

            self._table_lbl.configure(text=f"{db}  ›  {schema}.{table}")
            suffix = f"  (limit {limit})" if limit != "ALL" and len(rows) >= int(limit) else ""
            self._row_lbl.configure(
                text=f"{len(rows)} row{'s' if len(rows) != 1 else ''}{suffix}")
        except Exception as e:
            messagebox.showerror("Error loading table", str(e))

    def _refresh_table(self):
        self._load_table()

    def _search_table(self):
        term = self._search_var.get().lower()
        self._data_tree.delete(*self._data_tree.get_children())
        for row_vals in self._cur_rows:
            if not term or any(term in str(v).lower() for v in row_vals):
                self._data_tree.insert("", "end", values=row_vals)
        # Restore sort indicators on headings
        arrow = " ▲" if self._sort_dir == "asc" else (" ▼" if self._sort_dir == "desc" else "")
        for col in [c["name"] for c in self._cur_cols]:
            label = col + (arrow if col == self._sort_col else "")
            self._data_tree.heading(col, text=label,
                                    command=lambda c=col: self._sort_col_click(c))

    # ── Column header sort ─────────────────────────────────────────────────
    def _sort_col_click(self, col: str):
        if self._sort_col != col:
            self._sort_col = col
            self._sort_dir = "asc"
        else:
            self._sort_dir = "desc" if self._sort_dir == "asc" else "asc"
        self._apply_sort()

    def _apply_sort(self):
        col_names = [c["name"] for c in self._cur_cols]
        if self._sort_col not in col_names:
            return
        idx     = col_names.index(self._sort_col)
        reverse = self._sort_dir == "desc"

        # Collect all rows with their iids
        items = [(self._data_tree.item(iid, "values"), iid)
                 for iid in self._data_tree.get_children()]

        def key(item):
            val = item[0][idx]
            if val == "NULL":
                return (1, "")        # NULLs always last
            try:
                return (0, float(val))
            except (ValueError, TypeError):
                return (0, str(val).lower())

        items.sort(key=key, reverse=reverse)
        for i, (_, iid) in enumerate(items):
            self._data_tree.move(iid, "", i)

        # Update headings — show ▲/▼ on sorted column, plain text on others
        arrow = " ▲" if self._sort_dir == "asc" else " ▼"
        for col in col_names:
            label = col + (arrow if col == self._sort_col else "")
            self._data_tree.heading(col, text=label,
                                    command=lambda c=col: self._sort_col_click(c))

    # ── Column info toggle ─────────────────────────────────────────────────
    def _toggle_col_info(self):
        self._show_col_info = not self._show_col_info
        if self._show_col_info:
            self._dtf.grid_remove()
            self._populate_col_info()
            self._cif.grid()
            self._info_btn.configure(text="📊  Show Data")
        else:
            self._cif.grid_remove()
            self._dtf.grid()
            self._info_btn.configure(text="ℹ  Column Info")

    def _populate_col_info(self):
        self._ci_tree.delete(*self._ci_tree.get_children())
        for col in self._cur_cols:
            self._ci_tree.insert("", "end", values=(
                col["name"],
                col["type"],
                "✓  NULL ok"  if col["nullable"] else "✗  NOT NULL",
                "🔑  Yes"     if col["name"] in self._cur_pk else "—",
                "⚡  Yes"     if col["identity"] else "—",
            ))

    # ── INSERT modal ───────────────────────────────────────────────────────
    def _show_insert_modal(self):
        if not self._requires_conn(): return
        if not self._cur_table:
            messagebox.showwarning("No table", "Select a table from the left panel first.")
            return

        m = ctk.CTkToplevel(self)
        m.title(f"Insert  →  {self._cur_schema}.{self._cur_table}")
        m.geometry("540x580")
        m.resizable(True, True)
        m.grab_set()
        m.lift()

        ctk.CTkLabel(m, text=f"Insert row  →  {self._cur_schema}.{self._cur_table}",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=ACC).pack(padx=20, pady=(18, 10), anchor="w")

        sf = ctk.CTkScrollableFrame(m, fg_color="transparent")
        sf.pack(fill="both", expand=True, padx=16, pady=0)
        sf.grid_columnconfigure(1, weight=1)

        entries: dict[str, ctk.CTkEntry] = {}
        for i, col in enumerate(self._cur_cols):
            tag = "identity" if col["identity"] else ("nullable" if col["nullable"] else "required")
            hint = "auto (identity)" if col["identity"] else \
                   ("NULL" if col["nullable"] else "required")
            lbl_txt = (f"{col['name']}  "
                       f"({col['type']} · {'NULL ok' if col['nullable'] else 'NOT NULL'}"
                       f"{' · identity' if col['identity'] else ''})")
            ctk.CTkLabel(sf, text=lbl_txt, text_color=SUB,
                         font=ctk.CTkFont("Segoe UI", 11)).grid(
                row=i, column=0, padx=(0, 10), pady=5, sticky="w")
            e = ctk.CTkEntry(sf, placeholder_text=hint)
            e.grid(row=i, column=1, pady=5, sticky="ew")
            if col["identity"]:
                e.configure(state="disabled")
            entries[col["name"]] = e

        def do_insert():
            insertable = [c for c in self._cur_cols if not c["identity"]]
            col_names  = [c["name"] for c in insertable]
            vals = []
            for c in insertable:
                raw = entries[c["name"]].get().strip()
                vals.append(None if raw == "" else raw)
            ph  = ", ".join("?" * len(col_names))
            sql = (f"INSERT INTO [{self._cur_db}].[{self._cur_schema}].[{self._cur_table}] "
                   f"({', '.join(f'[{n}]' for n in col_names)}) VALUES ({ph})")
            try:
                self.cursor.execute(sql, vals)
                self.conn.commit()
                m.destroy()
                self._load_table()
                messagebox.showinfo("Inserted", "Row inserted successfully.")
            except Exception as e:
                messagebox.showerror("Insert error", str(e))

        br = ctk.CTkFrame(m, fg_color="transparent")
        br.pack(fill="x", padx=16, pady=14)
        ctk.CTkButton(br, text="Cancel", fg_color=SRF0,
                      command=m.destroy).pack(side="left", padx=(0, 8))
        ctk.CTkButton(br, text="Insert Row", command=do_insert).pack(side="left")

    # ── EDIT modal ─────────────────────────────────────────────────────────
    def _show_edit_modal(self):
        if not self._requires_conn(): return
        if not self._cur_table:
            messagebox.showwarning("No table", "Select a table first."); return
        sel = self._data_tree.selection()
        if not sel:
            messagebox.showwarning("No row selected",
                                   "Click on a row in the table to edit it."); return
        if not self._cur_pk:
            messagebox.showwarning("No primary key",
                                   "This table has no primary key.\n"
                                   "Use the Query Runner to update rows manually."); return

        col_names = [c["name"] for c in self._cur_cols]
        row_dict  = dict(zip(col_names, self._data_tree.item(sel[0], "values")))

        m = ctk.CTkToplevel(self)
        m.title(f"Edit  →  {self._cur_schema}.{self._cur_table}")
        m.geometry("540x600")
        m.resizable(True, True)
        m.grab_set()
        m.lift()

        ctk.CTkLabel(m, text=f"Edit row  →  {self._cur_schema}.{self._cur_table}",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=ACC).pack(padx=20, pady=(18, 10), anchor="w")

        sf = ctk.CTkScrollableFrame(m, fg_color="transparent")
        sf.pack(fill="both", expand=True, padx=16, pady=0)
        sf.grid_columnconfigure(1, weight=1)

        entries: dict[str, ctk.CTkEntry] = {}
        for i, col in enumerate(self._cur_cols):
            is_pk = col["name"] in self._cur_pk
            lbl_txt = (f"{col['name']}  ({col['type']})"
                       + ("  🔑 PK — locked" if is_pk else ""))
            ctk.CTkLabel(sf, text=lbl_txt,
                         text_color=ACC if is_pk else SUB,
                         font=ctk.CTkFont("Segoe UI", 11)).grid(
                row=i, column=0, padx=(0, 10), pady=5, sticky="w")
            e = ctk.CTkEntry(sf)
            current = row_dict.get(col["name"], "")
            if current != "NULL":
                e.insert(0, str(current))
            if is_pk or col["identity"]:
                e.configure(state="disabled")
            e.grid(row=i, column=1, pady=5, sticky="ew")
            entries[col["name"]] = e

        def do_update():
            sets, set_params = [], []
            for col in self._cur_cols:
                if col["name"] in self._cur_pk or col["identity"]:
                    continue
                raw = entries[col["name"]].get().strip()
                sets.append(f"[{col['name']}] = ?")
                set_params.append(None if raw in ("NULL", "") and col["nullable"] else raw)
            if not sets:
                messagebox.showwarning("Nothing to update", "No editable fields."); return
            where  = " AND ".join(f"[{pk}] = ?" for pk in self._cur_pk)
            pk_vals = [
                None if row_dict[pk] == "NULL" else row_dict[pk]
                for pk in self._cur_pk
            ]
            sql = (f"UPDATE [{self._cur_db}].[{self._cur_schema}].[{self._cur_table}] "
                   f"SET {', '.join(sets)} WHERE {where}")
            try:
                self.cursor.execute(sql, set_params + pk_vals)
                self.conn.commit()
                m.destroy()
                self._load_table()
                messagebox.showinfo("Updated", "Row updated successfully.")
            except Exception as e:
                messagebox.showerror("Update error", str(e))

        br = ctk.CTkFrame(m, fg_color="transparent")
        br.pack(fill="x", padx=16, pady=14)
        ctk.CTkButton(br, text="Cancel", fg_color=SRF0,
                      command=m.destroy).pack(side="left", padx=(0, 8))
        ctk.CTkButton(br, text="Save Changes", command=do_update).pack(side="left")

    # ── DELETE ─────────────────────────────────────────────────────────────
    def _confirm_delete(self):
        if not self._requires_conn(): return
        if not self._cur_table:
            messagebox.showwarning("No table", "Select a table first."); return
        sels = self._data_tree.selection()
        if not sels:
            messagebox.showwarning("No selection",
                                   "Select one or more rows to delete."); return
        if not self._cur_pk:
            messagebox.showwarning("No primary key",
                                   "This table has no primary key.\n"
                                   "Use the Query Runner to delete rows manually."); return
        if not messagebox.askyesno(
                "Confirm delete",
                f"Delete {len(sels)} row(s) from "
                f"{self._cur_schema}.{self._cur_table}?\n\nThis cannot be undone."):
            return

        col_names    = [c["name"] for c in self._cur_cols]
        where        = " AND ".join(f"[{pk}] = ?" for pk in self._cur_pk)
        sql          = (f"DELETE FROM [{self._cur_db}].[{self._cur_schema}]"
                        f".[{self._cur_table}] WHERE {where}")
        try:
            for iid in sels:
                row_dict = dict(zip(col_names,
                                    self._data_tree.item(iid, "values")))
                pk_vals  = [
                    None if row_dict[pk] == "NULL" else row_dict[pk]
                    for pk in self._cur_pk
                ]
                self.cursor.execute(sql, pk_vals)
            self.conn.commit()
            self._load_table()
            messagebox.showinfo("Deleted", f"{len(sels)} row(s) deleted.")
        except Exception as e:
            messagebox.showerror("Delete error", str(e))

    # ══════════════════════════════════════════════════════════════════════
    # QUERY RUNNER PAGE
    # ══════════════════════════════════════════════════════════════════════
    def _build_query_page(self):
        page = self._new_page("query")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        # Header
        hdr = ctk.CTkFrame(page, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="▶  Query Runner",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     text_color=TXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr,
                     text="Write any SQL — SELECT, INSERT, UPDATE, DELETE — press F5 or Run",
                     text_color=SUB, font=ctk.CTkFont("Segoe UI", 11)).grid(
            row=1, column=0, sticky="w")

        # DB selector
        db_row = ctk.CTkFrame(hdr, fg_color="transparent")
        db_row.grid(row=0, column=1, rowspan=2, sticky="e")
        ctk.CTkLabel(db_row, text="USE database:", text_color=SUB).pack(side="left", padx=(0, 6))
        self._qdb_var   = ctk.StringVar()
        self._qdb_combo = ctk.CTkComboBox(db_row, variable=self._qdb_var, values=[],
                                           width=200, command=self._on_qdb_change)
        self._qdb_combo.pack(side="left")

        # Editor frame
        ef = ctk.CTkFrame(page, fg_color=SIDEBAR, corner_radius=10)
        ef.grid(row=1, column=0, padx=24, pady=(0, 8), sticky="ew")
        ef.grid_columnconfigure(0, weight=1)

        self._sql_editor = ctk.CTkTextbox(
            ef, height=150,
            font=ctk.CTkFont("Courier New", 12),
            fg_color="#11111b", text_color="#cdd6f4",
            border_width=0)
        self._sql_editor.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        self._sql_editor.insert("0.0", "SELECT TOP 100 * FROM ")

        bb = ctk.CTkFrame(ef, fg_color="transparent")
        bb.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkButton(bb, text="▶  Run  (F5)", height=34, width=130,
                      command=self._run_query).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bb, text="Clear", height=34, width=80,
                      fg_color=SRF0, command=self._clear_query).pack(side="left", padx=(0, 12))
        self._q_status = ctk.CTkLabel(bb, text="",
                                       font=ctk.CTkFont("Segoe UI", 11),
                                       text_color=GRN)
        self._q_status.pack(side="left")

        self.bind("<F5>", lambda _e: self._run_query())

        # Results grid
        rf = ctk.CTkFrame(page, fg_color=BG, corner_radius=0)
        rf.grid(row=2, column=0, padx=24, pady=(0, 24), sticky="nsew")
        rf.grid_rowconfigure(0, weight=1)
        rf.grid_columnconfigure(0, weight=1)

        self._q_tree = ttk.Treeview(rf, style="Data.Treeview", show="headings")
        qv = ttk.Scrollbar(rf, orient="vertical",   command=self._q_tree.yview)
        qh = ttk.Scrollbar(rf, orient="horizontal", command=self._q_tree.xview)
        self._q_tree.configure(yscrollcommand=qv.set, xscrollcommand=qh.set)
        self._q_tree.grid(row=0, column=0, sticky="nsew")
        qv.grid(row=0, column=1, sticky="ns")
        qh.grid(row=1, column=0, sticky="ew")

    def _populate_query_db_list(self):
        try:
            dbs = self._get_databases()
            self._qdb_combo.configure(values=dbs)
            self._viz_db_combo.configure(values=dbs)
            if dbs:
                self._qdb_var.set(dbs[0])
                self._on_qdb_change(dbs[0])
                self._viz_db_var.set(dbs[0])
        except Exception:
            pass

    def _on_qdb_change(self, value: str):
        if self.conn and value:
            try:
                self.cursor.execute(f"USE [{value}]")
            except Exception:
                pass

    def _run_query(self):
        if not self._requires_conn(): return
        sql = self._sql_editor.get("0.0", "end").strip()
        if not sql: return
        try:
            self.cursor.execute(sql)
            if self.cursor.description:
                cols = [d[0] for d in self.cursor.description]
                rows = self.cursor.fetchall()
                self._q_tree["columns"] = cols
                for col in cols:
                    self._q_tree.heading(col, text=col)
                    self._q_tree.column(col, width=200, minwidth=100, stretch=True)
                self._q_tree.delete(*self._q_tree.get_children())
                for row in rows:
                    self._q_tree.insert(
                        "", "end",
                        values=[v if v is not None else "NULL" for v in row])
                self._q_status.configure(
                    text=f"✓  {len(rows)} row{'s' if len(rows) != 1 else ''} returned",
                    text_color=GRN)
            else:
                self.conn.commit()
                self._q_status.configure(
                    text=f"✓  Done  ({self.cursor.rowcount} row(s) affected)",
                    text_color=GRN)
        except Exception as e:
            self._q_status.configure(text="✗  Error — see dialog", text_color=RED)
            messagebox.showerror("Query error", str(e))

    def _clear_query(self):
        self._sql_editor.delete("0.0", "end")
        self._q_status.configure(text="")
        self._q_tree.delete(*self._q_tree.get_children())

    # ══════════════════════════════════════════════════════════════════════
    # VISUALIZE PAGE  — interactive ERD canvas
    # ══════════════════════════════════════════════════════════════════════
    def _build_viz_page(self):
        page = self._new_page("viz")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        # ── Top controls bar ───────────────────────────────────────────────
        ctrl = ctk.CTkFrame(page, fg_color=SIDEBAR, corner_radius=0)
        ctrl.grid(row=0, column=0, sticky="ew")
        ctrl.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(ctrl, text="🗺  Data Model  /  ERD",
                     font=ctk.CTkFont("Segoe UI", 17, "bold"),
                     text_color=ACC).grid(row=0, column=0, padx=16, pady=12, sticky="w")

        ctk.CTkLabel(ctrl, text="Database:", text_color=SUB).grid(
            row=0, column=1, padx=(20, 6), pady=12)
        self._viz_db_var   = ctk.StringVar()
        self._viz_db_combo = ctk.CTkComboBox(ctrl, variable=self._viz_db_var,
                                              values=[], width=220)
        self._viz_db_combo.grid(row=0, column=2, padx=(0, 10), pady=12, sticky="w")

        ctk.CTkButton(ctrl, text="▶  Generate", height=36, width=120,
                      command=self._gen_erd).grid(row=0, column=3, padx=4, pady=12)

        # Zoom buttons
        for txt, delta, col in [("＋ Zoom In", 1.25, 4), ("－ Zoom Out", 0.8, 5)]:
            ctk.CTkButton(ctrl, text=txt, height=36, width=110, fg_color=SRF0,
                          command=lambda d=delta: self._erd_zoom_btn(d)).grid(
                row=0, column=col, padx=4, pady=12)
        ctk.CTkButton(ctrl, text="↺  Reset", height=36, width=90, fg_color=SRF0,
                      command=self._erd_reset).grid(row=0, column=6, padx=(4, 16), pady=12)

        # Legend
        leg = ctk.CTkLabel(ctrl,
                           text="  🔑 PK   ⚡ Identity   ──▶ Foreign Key     "
                                "Drag to pan  ·  Scroll to zoom",
                           text_color=SUB, font=ctk.CTkFont("Segoe UI", 11))
        leg.grid(row=1, column=0, columnspan=7, padx=16, pady=(0, 8), sticky="w")

        # ── Canvas area ────────────────────────────────────────────────────
        canvas_bg = "#11111b"
        cf = tk.Frame(page, bg=canvas_bg)
        cf.grid(row=1, column=0, sticky="nsew")
        cf.grid_rowconfigure(0, weight=1)
        cf.grid_columnconfigure(0, weight=1)

        self._erd_canvas = tk.Canvas(cf, bg=canvas_bg,
                                      highlightthickness=0, cursor="fleur")
        vscroll = ttk.Scrollbar(cf, orient="vertical",
                                 command=self._erd_canvas.yview)
        hscroll = ttk.Scrollbar(cf, orient="horizontal",
                                 command=self._erd_canvas.xview)
        self._erd_canvas.configure(yscrollcommand=vscroll.set,
                                    xscrollcommand=hscroll.set)
        self._erd_canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")

        # Placeholder text
        self._erd_canvas.create_text(
            400, 200, text="Select a database and click ▶ Generate",
            fill=SRF0, font=("Segoe UI", 18), tags="placeholder")

        # Interaction bindings
        self._erd_canvas.bind("<ButtonPress-1>",   self._erd_pan_start)
        self._erd_canvas.bind("<B1-Motion>",        self._erd_pan_move)
        self._erd_canvas.bind("<MouseWheel>",       self._erd_zoom_wheel)
        self._erd_canvas.bind("<Button-4>",         self._erd_zoom_wheel)
        self._erd_canvas.bind("<Button-5>",         self._erd_zoom_wheel)

    # ── ERD schema queries ─────────────────────────────────────────────────
    def _gen_erd(self):
        if not self._requires_conn(): return
        db = self._viz_db_var.get().strip()
        if not db:
            messagebox.showwarning("No database", "Select a database first."); return

        self._erd_canvas.delete("all")
        self._erd_canvas.create_text(
            400, 200, text="Loading schema…", fill=SUB,
            font=("Segoe UI", 16), tags="loading")
        self.update_idletasks()

        try:
            # Tables + columns
            self.cursor.execute(
                f"SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, "
                f"COLUMNPROPERTY(OBJECT_ID('[{db}].['+TABLE_SCHEMA+'].['+TABLE_NAME+']'),"
                f"COLUMN_NAME,'IsIdentity') "
                f"FROM [{db}].INFORMATION_SCHEMA.COLUMNS "
                f"ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION"
            )
            tables_cols: dict[tuple, list] = {}
            for schema, tbl, col, dtype, nullable, identity in self.cursor.fetchall():
                key = (schema, tbl)
                tables_cols.setdefault(key, []).append({
                    "name": col, "type": dtype,
                    "nullable": nullable == "YES", "identity": bool(identity)
                })

            # PKs
            self.cursor.execute(
                f"SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME "
                f"FROM [{db}].INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
                f"JOIN [{db}].INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
                f"  ON tc.CONSTRAINT_NAME=kcu.CONSTRAINT_NAME "
                f" AND tc.TABLE_SCHEMA=kcu.TABLE_SCHEMA "
                f" AND tc.TABLE_NAME=kcu.TABLE_NAME "
                f"WHERE tc.CONSTRAINT_TYPE='PRIMARY KEY'"
            )
            pks: dict[tuple, set] = {}
            for schema, tbl, col in self.cursor.fetchall():
                pks.setdefault((schema, tbl), set()).add(col)

            # FKs
            self.cursor.execute(
                f"SELECT "
                f"  fk_tc.TABLE_SCHEMA, fk_tc.TABLE_NAME, fk_kcu.COLUMN_NAME, "
                f"  pk_tc.TABLE_SCHEMA, pk_tc.TABLE_NAME, pk_kcu.COLUMN_NAME "
                f"FROM [{db}].INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc "
                f"JOIN [{db}].INFORMATION_SCHEMA.TABLE_CONSTRAINTS fk_tc "
                f"  ON rc.CONSTRAINT_NAME=fk_tc.CONSTRAINT_NAME "
                f"JOIN [{db}].INFORMATION_SCHEMA.TABLE_CONSTRAINTS pk_tc "
                f"  ON rc.UNIQUE_CONSTRAINT_NAME=pk_tc.CONSTRAINT_NAME "
                f"JOIN [{db}].INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk_kcu "
                f"  ON rc.CONSTRAINT_NAME=fk_kcu.CONSTRAINT_NAME "
                f"JOIN [{db}].INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk_kcu "
                f"  ON rc.UNIQUE_CONSTRAINT_NAME=pk_kcu.CONSTRAINT_NAME "
                f"ORDER BY fk_tc.TABLE_NAME"
            )
            fks = self.cursor.fetchall()

            self._erd_data = (tables_cols, pks, fks)
            self._draw_erd()

        except Exception as e:
            self._erd_canvas.delete("all")
            self._erd_canvas.create_text(
                400, 200, text=f"Error: {e}", fill=RED,
                font=("Segoe UI", 13))

    # ── ERD drawing ────────────────────────────────────────────────────────
    def _draw_erd(self):
        if not self._erd_data:
            return
        tables_cols, pks, fks = self._erd_data
        canvas = self._erd_canvas
        canvas.delete("all")

        BOX_W    = 270
        HDR_H    = 42
        COL_H    = 26
        PAD_X    = 100
        PAD_Y    = 70

        sorted_keys = sorted(tables_cols.keys())
        n           = len(sorted_keys)
        if n == 0:
            canvas.create_text(400, 200, text="No tables found.",
                               fill=SUB, font=("Segoe UI", 14))
            return

        n_cols = min(4, max(1, math.ceil(math.sqrt(n))))

        # Compute heights
        heights = {k: HDR_H + len(cols) * COL_H + 10
                   for k, cols in tables_cols.items()}

        # Compute row max heights for proper vertical spacing
        row_max_h: dict[int, int] = {}
        for i, k in enumerate(sorted_keys):
            ri = i // n_cols
            row_max_h[ri] = max(row_max_h.get(ri, 0), heights[k])

        # Row y offsets
        row_y: dict[int, int] = {}
        y_cur = 50
        for ri in sorted(row_max_h):
            row_y[ri] = y_cur
            y_cur += row_max_h[ri] + PAD_Y

        # Table positions
        positions: dict[tuple, tuple] = {}
        for i, k in enumerate(sorted_keys):
            ri, ci = divmod(i, n_cols)
            x = 50 + ci * (BOX_W + PAD_X)
            y = row_y[ri]
            positions[k] = (x, y, BOX_W, heights[k])

        # ── Draw FK lines first (behind boxes) ─────────────────────────────
        for fk_schema, fk_tbl, fk_col, pk_schema, pk_tbl, pk_col in fks:
            from_key = (fk_schema, fk_tbl)
            to_key   = (pk_schema, pk_tbl)
            if from_key not in positions or to_key not in positions:
                continue
            fx, fy, fw, fh = positions[from_key]
            tx, ty, tw, th = positions[to_key]

            # Find column Y for the FK column
            fk_col_idx = next((i for i, c in enumerate(tables_cols[from_key])
                               if c["name"] == fk_col), 0)
            pk_col_idx = next((i for i, c in enumerate(tables_cols[to_key])
                               if c["name"] == pk_col), 0)
            fy_conn = fy + HDR_H + fk_col_idx * COL_H + COL_H // 2
            ty_conn = ty + HDR_H + pk_col_idx * COL_H + COL_H // 2

            # Choose edges based on horizontal position
            if fx + fw / 2 <= tx + tw / 2:
                p1 = (fx + fw, fy_conn)
                p2 = (tx,      ty_conn)
            else:
                p1 = (fx,      fy_conn)
                p2 = (tx + tw, ty_conn)

            # Bezier control points
            dx = abs(p2[0] - p1[0]) * 0.5
            canvas.create_line(
                p1[0], p1[1],
                p1[0] + (dx if p1[0] < p2[0] else -dx), p1[1],
                p2[0] - (dx if p1[0] < p2[0] else -dx), p2[1],
                p2[0], p2[1],
                smooth=True, fill="#89b4fa", width=2,
                arrow=tk.LAST, arrowshape=(12, 14, 5), tags="fk")

        # ── Draw table boxes ───────────────────────────────────────────────
        for k in sorted_keys:
            x, y, w, h = positions[k]
            schema, tbl = k
            cols  = tables_cols[k]
            pk_set = pks.get(k, set())

            # Outer border
            canvas.create_rectangle(x - 2, y - 2, x + w + 2, y + h + 2,
                                    fill="#45475a", outline="", tags="tbl")
            # Header
            canvas.create_rectangle(x, y, x + w, y + HDR_H,
                                    fill="#313244", outline="", tags="tbl")
            canvas.create_text(x + w / 2, y + HDR_H / 2,
                               text=f"{schema}.{tbl}",
                               fill=ACC, font=("Segoe UI", 12, "bold"),
                               width=w - 16, tags="tbl")

            # Column rows
            for ci, col in enumerate(cols):
                cy   = y + HDR_H + ci * COL_H
                bg   = "#1e1e2e" if ci % 2 == 0 else "#181825"
                canvas.create_rectangle(x, cy, x + w, cy + COL_H,
                                        fill=bg, outline="", tags="tbl")

                # Icon prefix
                if col["name"] in pk_set:
                    prefix = "🔑 "
                    color  = YEL
                elif col["identity"]:
                    prefix = "⚡ "
                    color  = "#89dceb"
                else:
                    prefix = "   "
                    color  = TXT

                label = f"{prefix}{col['name']}  ({col['type']})"
                canvas.create_text(x + 10, cy + COL_H / 2,
                                   text=label, fill=color,
                                   font=("Segoe UI", 10), anchor="w",
                                   width=w - 14, tags="tbl")

            # Bottom border line
            canvas.create_line(x, y + h, x + w, y + h,
                               fill="#45475a", width=1, tags="tbl")

        # Update scroll region
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=(
                bbox[0] - 40, bbox[1] - 40,
                bbox[2] + 40, bbox[3] + 40))

    # ── ERD interactions ───────────────────────────────────────────────────
    def _erd_pan_start(self, event):
        self._erd_canvas.scan_mark(event.x, event.y)

    def _erd_pan_move(self, event):
        self._erd_canvas.scan_dragto(event.x, event.y, gain=1)

    def _erd_zoom_wheel(self, event):
        if event.num == 4 or event.delta > 0:
            factor = 1.1
        else:
            factor = 0.9
        cx = self._erd_canvas.canvasx(event.x)
        cy = self._erd_canvas.canvasy(event.y)
        self._erd_canvas.scale("all", cx, cy, factor, factor)
        bbox = self._erd_canvas.bbox("all")
        if bbox:
            self._erd_canvas.configure(scrollregion=(
                bbox[0] - 40, bbox[1] - 40,
                bbox[2] + 40, bbox[3] + 40))

    def _erd_zoom_btn(self, factor: float):
        w = self._erd_canvas.winfo_width()
        h = self._erd_canvas.winfo_height()
        cx = self._erd_canvas.canvasx(w / 2)
        cy = self._erd_canvas.canvasy(h / 2)
        self._erd_canvas.scale("all", cx, cy, factor, factor)
        bbox = self._erd_canvas.bbox("all")
        if bbox:
            self._erd_canvas.configure(scrollregion=(
                bbox[0] - 40, bbox[1] - 40,
                bbox[2] + 40, bbox[3] + 40))

    def _erd_reset(self):
        self._draw_erd()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()
