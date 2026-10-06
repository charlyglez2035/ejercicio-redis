import json
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import END, BooleanVar, Canvas, StringVar, Text, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    # Las URL de los servicios viven en el .env raiz de library/.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
SECRET_KEY_PATTERN = re.compile(r"(authorization|cookie|password|token|secret|api[-_]?key|credential)", re.I)

# (clave, etiqueta, variable de entorno, URL por defecto)
SERVICES = (
    ("login", "Login", "LOGIN_SERVICE_URL", "http://127.0.0.1:5000"),
    ("users", "Users", "USERS_SERVICE_URL", "http://127.0.0.1:5002"),
    ("books", "Books", "BOOKS_SERVICE_URL", "http://127.0.0.1:5001"),
    ("authors", "Authors", "AUTHORS_SERVICE_URL", "http://127.0.0.1:5003"),
    ("pedidos", "Pedidos", "PEDIDOS_SERVICE_URL", "http://127.0.0.1:5004"),
    ("pagos", "Pagos", "PAGOS_SERVICE_URL", "http://127.0.0.1:5005"),
)
try:
    TIMEOUT_SECONDS = float(os.getenv("SERVICE_TIMEOUT_SECONDS", "10"))
except ValueError:
    TIMEOUT_SECONDS = 10.0

STATUS_MESSAGES = {
    400: "Solicitud invalida: revisa los datos del formulario.",
    401: "No autenticado: falta el JWT o es invalido, expiro o fue revocado.",
    403: "Acceso denegado: tu rol no tiene permisos para esta operacion.",
    404: "No encontrado: el recurso solicitado no existe.",
    409: "Conflicto: la operacion choca con el estado actual de los datos.",
    500: "Error interno del microservicio. Intentalo mas tarde.",
    502: "El microservicio no respondio correctamente.",
    503: "Servicio no disponible temporalmente (base de datos o Redis).",
}
LIGHT_COLORS = {"off": "#9aa5b1", "red": "#c0392b", "amber": "#e0a100", "green": "#1e8449"}


def sanitize(value, key=""):
    if SECRET_KEY_PATTERN.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {name: sanitize(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return JWT_PATTERN.sub("[REDACTED]", value)
    return value


def sanitize_url(value):
    try:
        parts = urllib.parse.urlsplit(value)
        host = parts.hostname or ""
        if parts.port:
            host += f":{parts.port}"
        if parts.username or parts.password:
            host = f"[REDACTED]@{host}"
        query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        query = [
            (key, "[REDACTED]" if SECRET_KEY_PATTERN.search(key) else item)
            for key, item in query
        ]
        return urllib.parse.urlunsplit((parts.scheme, host, parts.path,
                                        urllib.parse.urlencode(query), parts.fragment))
    except (TypeError, ValueError):
        return JWT_PATTERN.sub("[REDACTED]", value)


def display(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


class LibraryClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Library | Cliente de microservicios")
        self.root.geometry("1220x860")
        self.token = None
        self.refresh_token = None
        self.expires_at = None
        self.user = None
        self.token_lock = threading.Lock()
        self.results = queue.Queue()
        self.urls = {key: StringVar(value=os.getenv(env, default)) for key, _label, env, default in SERVICES}
        self.identity = StringVar()
        self.password = StringVar()
        self.without_token = BooleanVar(value=False)
        self.show_all_actions = BooleanVar(value=False)
        self.session_text = StringVar(value="Sin sesion")
        self.access_widgets = []
        self.health_lights = {}
        self._build()
        self._apply_role()
        self.root.after(100, self._poll_results)

    # ==================== INTERFAZ ====================

    def _build(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=3)
        self.root.rowconfigure(2, weight=1)

        header = ttk.Frame(self.root)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        header.columnconfigure(1, weight=1)
        self.session_light = Canvas(header, width=22, height=22, highlightthickness=0)
        self.session_dot = self.session_light.create_oval(3, 3, 19, 19, fill=LIGHT_COLORS["red"], outline="")
        self.session_light.grid(row=0, column=0, padx=(0, 6))
        ttk.Label(header, textvariable=self.session_text, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(header, text="Omitir JWT (prueba 401)", variable=self.without_token).grid(row=0, column=2, padx=8)
        ttk.Checkbutton(header, text="Habilitar todas las acciones (prueba 403)", variable=self.show_all_actions,
                        command=self._apply_role).grid(row=0, column=3, padx=8)

        self.tabs = ttk.Notebook(self.root)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self._build_login_tab()
        self._build_users_tab()
        self._build_books_tab()
        self._build_authors_tab()
        self._build_pedidos_tab()
        self._build_pagos_tab()

        log_frame = ttk.LabelFrame(self.root, text="Peticiones sanitizadas")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = Text(log_frame, height=10, wrap="none", state="disabled", font=("Consolas", 9))
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)
        actions = ttk.Frame(log_frame)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        ttk.Button(actions, text="Copiar", command=self._copy_log).pack(side="left", padx=4)
        ttk.Button(actions, text="Exportar", command=self._export_log).pack(side="left", padx=4)
        ttk.Button(actions, text="Limpiar", command=self._clear_log).pack(side="left", padx=4)

    def _build_login_tab(self):
        frame = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(frame, text="Login")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        urls = ttk.LabelFrame(frame, text="Servicios (semaforos de disponibilidad)")
        urls.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        urls.columnconfigure(2, weight=1)
        urls.columnconfigure(5, weight=1)
        for index, (key, label, _env, _default) in enumerate(SERVICES):
            row, column = divmod(index, 2)
            light = Canvas(urls, width=18, height=18, highlightthickness=0)
            dot = light.create_oval(2, 2, 16, 16, fill=LIGHT_COLORS["off"], outline="")
            light.grid(row=row, column=column * 3, padx=(8, 2), pady=4)
            self.health_lights[key] = (light, dot)
            ttk.Label(urls, text=label, width=8).grid(row=row, column=column * 3 + 1, sticky="w")
            ttk.Entry(urls, textvariable=self.urls[key]).grid(row=row, column=column * 3 + 2, sticky="ew", padx=(0, 12))
        ttk.Button(urls, text="Comprobar servicios", command=self._check_health).grid(
            row=3, column=0, columnspan=6, sticky="w", padx=8, pady=6)

        auth = ttk.LabelFrame(frame, text="Autenticacion")
        auth.grid(row=1, column=0, sticky="ew", pady=6)
        auth.columnconfigure(1, weight=1)
        auth.columnconfigure(3, weight=1)
        ttk.Label(auth, text="Usuario o correo").grid(row=0, column=0, padx=8, pady=8)
        ttk.Entry(auth, textvariable=self.identity).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Label(auth, text="Contrasena").grid(row=0, column=2, padx=8)
        password_entry = ttk.Entry(auth, textvariable=self.password, show="*")
        password_entry.grid(row=0, column=3, sticky="ew", padx=8)
        password_entry.bind("<Return>", lambda _event: self._login())
        buttons = ttk.Frame(auth)
        buttons.grid(row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 8))
        ttk.Button(buttons, text="Registro", command=self._registration_dialog).pack(side="left", padx=4)
        ttk.Button(buttons, text="Login", command=self._login).pack(side="left", padx=4)
        for label, command in (("Sesion", self._session), ("Renovar token", self._refresh),
                               ("Logout", self._logout)):
            button = ttk.Button(buttons, text=label, command=command)
            button.pack(side="left", padx=4)
            self._register(button, "auth")

        self.login_detail = self._detail_text(frame)
        self.login_detail.grid(row=2, column=0, sticky="nsew")

    def _detail_text(self, parent):
        return Text(parent, height=8, wrap="none", state="disabled", font=("Consolas", 9))

    def _resource_tab(self, spec):
        """Pestaña CRUD generica: formulario, acciones, tabla y detalle JSON."""
        frame = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(frame, text=spec["title"])
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        tab = {"spec": spec, "vars": {}, "rows": {}}

        form = ttk.LabelFrame(frame, text="Formulario")
        form.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
        for row, (key, label, kind, *_flags) in enumerate(spec["fields"]):
            var = StringVar()
            tab["vars"][key] = var
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=3)
            if kind == "password":
                widget = ttk.Entry(form, textvariable=var, show="*", width=32)
            elif kind == "bool":
                widget = ttk.Combobox(form, textvariable=var, values=("", "true", "false"), state="readonly", width=30)
            elif kind.startswith("choice:"):
                widget = ttk.Combobox(form, textvariable=var, values=("",) + tuple(kind[7:].split("|")),
                                      state="readonly", width=30)
            else:
                widget = ttk.Entry(form, textvariable=var, width=32)
            widget.grid(row=row, column=1, sticky="ew", padx=6, pady=3)

        buttons = ttk.Frame(form)
        buttons.grid(row=len(spec["fields"]), column=0, columnspan=2, sticky="ew", pady=6)
        for index, (label, command, access) in enumerate(spec["actions"](tab)):
            button = ttk.Button(buttons, text=label, command=command)
            button.grid(row=index // 3, column=index % 3, sticky="ew", padx=2, pady=2)
            self._register(button, access)
        ttk.Button(buttons, text="Limpiar formulario",
                   command=lambda: [var.set("") for var in tab["vars"].values()]).grid(
            row=99, column=0, columnspan=3, sticky="ew", padx=2, pady=(6, 2))
        if spec.get("extra"):
            spec["extra"](tab, form, len(spec["fields"]) + 1)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=2)
        columns = [column[0] for column in spec["columns"]]
        tree = ttk.Treeview(right, columns=columns, show="headings", selectmode="browse", height=10)
        for key, heading, width in spec["columns"]:
            tree.heading(key, text=heading)
            tree.column(key, width=width, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(right, orient="vertical", command=tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.bind("<<TreeviewSelect>>", lambda _event: self._row_selected(tab))
        detail = self._detail_text(right)
        detail.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(6, 0))
        tab.update(tree=tree, detail=detail)
        return tab

    def _crud_actions(self, tab, read="public", list_access=None, create="admin", update="admin",
                      delete="admin", create_keys=None, update_keys=None, patch_keys=None):
        return [
            ("Listar", lambda: self._list(tab, list_access or read), list_access or read),
            ("Consultar", lambda: self._get(tab, read), read),
            ("Crear", lambda: self._write(tab, "POST", create_keys), create),
            ("Reemplazar (PUT)", lambda: self._write(tab, "PUT", update_keys), update),
            ("Actualizar (PATCH)", lambda: self._write(tab, "PATCH", patch_keys or update_keys), update),
            ("Eliminar", lambda: self._write(tab, "DELETE"), delete),
        ]

    def _build_users_tab(self):
        self._resource_tab({
            "title": "Users", "service": "users", "path": "/users", "id": "id",
            "fields": (
                ("id", "ID", "int", "path"),
                ("username", "Usuario", "text"),
                ("email", "Correo", "text"),
                ("full_name", "Nombre completo", "text"),
                ("password", "Contrasena (nueva)", "password"),
                ("role_id", "Rol", "choice:customer|admin"),
                ("email_verified", "Correo verificado", "bool"),
            ),
            "columns": (("id", "ID", 50), ("username", "Usuario", 120), ("email", "Correo", 200),
                        ("full_name", "Nombre", 180), ("role_id", "Rol", 80),
                        ("email_verified", "Verificado", 80)),
            "actions": lambda tab: self._crud_actions(tab, read="auth", list_access="admin", update="auth") + [
                ("Roles", lambda: self._show(tab, "GET", "/roles", auth=False), "public"),
            ],
        })

    def _build_books_tab(self):
        self._resource_tab({
            "title": "Books", "service": "books", "path": "/api/books", "id": "isbn",
            "fields": (
                ("isbn", "ISBN", "text"),
                ("title", "Titulo", "text"),
                ("publication_year", "Anio", "int"),
                ("price", "Precio", "decimal"),
                ("stock", "Stock", "int"),
                ("format_id", "Formato (ID)", "int"),
                ("category_id", "Categoria (ID)", "int"),
                ("authors", "Autores (separados por coma)", "list"),
            ),
            "columns": (("isbn", "ISBN", 130), ("title", "Titulo", 260), ("authors", "Autores", 200),
                        ("price", "Precio", 70), ("stock", "Stock", 60), ("category", "Categoria", 120)),
            "actions": lambda tab: self._crud_actions(tab),
        })

    def _build_authors_tab(self):
        relation = {"isbn": StringVar(), "order": StringVar()}

        def extra(tab, form, row):
            box = ttk.LabelFrame(form, text="Relacion autor - libro")
            box.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=6)
            ttk.Label(box, text="ISBN").grid(row=0, column=0, sticky="w", padx=4)
            ttk.Entry(box, textvariable=relation["isbn"], width=20).grid(row=0, column=1, padx=4, pady=2)
            ttk.Label(box, text="Orden").grid(row=1, column=0, sticky="w", padx=4)
            ttk.Entry(box, textvariable=relation["order"], width=20).grid(row=1, column=1, padx=4, pady=2)
            for index, (label, command, access) in enumerate((
                ("Ver libros", lambda: self._show(tab, "GET", self._item_path(tab, "/books"), auth=False), "public"),
                ("Relacionar", lambda: self._link_book(tab, relation), "admin"),
                ("Quitar", lambda: self._unlink_book(tab, relation), "admin"),
            )):
                button = ttk.Button(box, text=label, command=command)
                button.grid(row=2, column=index, padx=2, pady=4)
                self._register(button, access)

        self._resource_tab({
            "title": "Authors", "service": "authors", "path": "/authors", "id": "author_id",
            "fields": (
                ("author_id", "ID", "int", "path"),
                ("name", "Nombre", "text"),
                ("books", "Libros (ISBN separados por coma)", "list"),
            ),
            "columns": (("author_id", "ID", 60), ("name", "Nombre", 280), ("book_count", "Libros", 70)),
            "actions": lambda tab: self._crud_actions(tab),
            "extra": extra,
        })

    def _build_pedidos_tab(self):
        line = {"isbn": StringVar(), "quantity": StringVar()}

        def extra(tab, form, row):
            box = ttk.LabelFrame(form, text="Lineas y stock")
            box.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=6)
            ttk.Label(box, text="ISBN").grid(row=0, column=0, sticky="w", padx=4)
            ttk.Entry(box, textvariable=line["isbn"], width=20).grid(row=0, column=1, columnspan=2, padx=4, pady=2)
            ttk.Label(box, text="Cantidad / stock").grid(row=1, column=0, sticky="w", padx=4)
            ttk.Entry(box, textvariable=line["quantity"], width=20).grid(row=1, column=1, columnspan=2, padx=4, pady=2)
            for index, (label, command, access) in enumerate((
                ("Agregar linea", lambda: self._line_request(tab, line, "POST"), "auth"),
                ("Actualizar linea", lambda: self._line_request(tab, line, "PATCH"), "auth"),
                ("Quitar linea", lambda: self._line_request(tab, line, "DELETE"), "auth"),
                ("Ver stock", lambda: self._show_stock(tab, line), "public"),
                ("Ajustar stock", lambda: self._adjust_stock(tab, line), "admin"),
                ("Estados", lambda: self._show(tab, "GET", "/pedidos/estados", auth=False), "public"),
            )):
                button = ttk.Button(box, text=label, command=command)
                button.grid(row=2 + index // 3, column=index % 3, sticky="ew", padx=2, pady=2)
                self._register(button, access)

        self._resource_tab({
            "title": "Pedidos", "service": "pedidos", "path": "/pedidos", "id": "order_id",
            "list_params": {"status": "status"},
            "fields": (
                ("order_id", "ID pedido", "int", "path"),
                ("user_id", "Cliente (ID, solo admin)", "int"),
                ("status", "Estado (filtro / cambio)", "choice:pending|paid|shipped|delivered|cancelled"),
                ("lines", "Lineas isbn:cant, isbn:cant", "lines"),
            ),
            "columns": (("order_id", "ID", 60), ("username", "Cliente", 120), ("status", "Estado", 90),
                        ("total", "Total", 80), ("created_at", "Creado", 220)),
            "actions": lambda tab: [
                ("Listar", lambda: self._list(tab, "auth"), "auth"),
                ("Consultar", lambda: self._get(tab, "auth"), "auth"),
                ("Crear", lambda: self._write(tab, "POST", ("user_id", "lines")), "auth"),
                ("Reemplazar lineas", lambda: self._write(tab, "PUT", ("lines",)), "auth"),
                ("Cambiar estado", lambda: self._write(tab, "PATCH", ("status",)), "auth"),
                ("Cancelar", lambda: self._cancel_order(tab), "auth"),
                ("Eliminar", lambda: self._write(tab, "DELETE"), "admin"),
            ],
            "extra": extra,
        })

    def _build_pagos_tab(self):
        self._resource_tab({
            "title": "Pagos", "service": "pagos", "path": "/pagos", "id": "payment_id",
            "list_params": {"order_id": "order_id"},
            "fields": (
                ("payment_id", "ID pago", "int", "path"),
                ("order_id", "Pedido (ID)", "int"),
                ("amount", "Monto", "decimal"),
                ("method", "Metodo", "choice:card|cash|transfer"),
                ("reference", "Referencia", "text"),
                ("status", "Estado", "choice:pending|approved|rejected|refunded"),
            ),
            "columns": (("payment_id", "ID", 60), ("order_id", "Pedido", 70), ("amount", "Monto", 80),
                        ("method", "Metodo", 80), ("status", "Estado", 90), ("order_status", "Estado pedido", 110)),
            "actions": lambda tab: [
                ("Listar", lambda: self._list(tab, "auth"), "auth"),
                ("Consultar", lambda: self._get(tab, "auth"), "auth"),
                ("Registrar", lambda: self._write(tab, "POST", ("order_id", "amount", "method", "reference", "status")), "auth"),
                ("Reemplazar (PUT)", lambda: self._write(tab, "PUT", ("amount", "method", "reference", "status")), "admin"),
                ("Actualizar estado", lambda: self._write(tab, "PATCH", ("status",)), "admin"),
                ("Eliminar", lambda: self._write(tab, "DELETE"), "admin"),
                ("Metodos y estados", lambda: self._show(tab, "GET", "/pagos/estados", auth=False), "public"),
            ],
        })

    # ==================== ROLES Y SESION ====================

    def _register(self, widget, access):
        self.access_widgets.append((widget, access))

    def _role(self):
        return (self.user or {}).get("role_id")

    def _apply_role(self):
        """Solo mejora la UX; el backend vuelve a comprobar JWT y rol en cada peticion."""
        logged = self.token is not None
        for widget, access in self.access_widgets:
            enabled = (
                access == "public"
                or self.show_all_actions.get()
                or (logged and (access == "auth" or self._role() == "admin"))
            )
            widget.state(["!disabled"] if enabled else ["disabled"])
        if not logged:
            self.session_text.set("Sin sesion")
            color = "red"
        else:
            expires = datetime.fromtimestamp(self.expires_at).strftime("%H:%M:%S") if self.expires_at else "?"
            user = self.user or {}
            self.session_text.set(
                f"Sesion: {user.get('username', '?')} (user_id {user.get('id', '?')}, rol {self._role()}) "
                f"- JWT en memoria, expira {expires}"
            )
            color = "green" if self._role() == "admin" else "amber"
        self.session_light.itemconfigure(self.session_dot, fill=LIGHT_COLORS[color])

    def _store_tokens(self, data):
        with self.token_lock:
            self.token = data["access_token"]
            self.refresh_token = data.get("refresh_token") or self.refresh_token
            self.expires_at = time.time() + int(data.get("expires_in") or 0)
        user = dict(data.get("user") or self.user or {})
        user["id"] = data.get("user_id", user.get("id"))
        user["role_id"] = data.get("role_id") or user.get("role_id") or user.get("role")
        self.user = user

    def _clear_session(self, message=None):
        with self.token_lock:
            self.token = None
            self.refresh_token = None
            self.expires_at = None
        self.user = None
        self._apply_role()
        if message:
            messagebox.showwarning("Sesion", message)

    def _login(self):
        if not self.identity.get().strip() or not self.password.get():
            messagebox.showinfo("Login", "Captura usuario/correo y contrasena.")
            return
        payload = {"identity": self.identity.get().strip(), "password": self.password.get()}
        self.password.set("")
        self.api("login", "POST", "/login", payload, auth=False, on_success=self._on_login)

    def _on_login(self, data):
        if not isinstance(data, dict) or not data.get("access_token"):
            messagebox.showerror("Login", "El servicio no devolvio un JWT.")
            return
        self._store_tokens(data)
        self._apply_role()
        self._set_text(self.login_detail, {"message": data.get("message"), "user": data.get("user"),
                                           "expires_in": data.get("expires_in")})
        messagebox.showinfo("Login", "Sesion iniciada.")

    def _session(self):
        self.api("login", "GET", "/session", on_success=lambda data: self._set_text(self.login_detail, data))

    def _refresh(self):
        if not self.refresh_token:
            messagebox.showinfo("Sesion", "No hay refresh token en memoria; inicia sesion.")
            return
        def done(data):
            self._store_tokens(data)
            self._apply_role()
            self._set_text(self.login_detail, {"message": data.get("message"), "expires_in": data.get("expires_in")})
        self.api("login", "POST", "/refresh", {"refresh_token": self.refresh_token}, auth=False, on_success=done)

    def _logout(self):
        self.api("login", "POST", "/logout", on_success=lambda _data: self._clear_session("Sesion cerrada."))

    def _registration_dialog(self):
        dialog = Toplevel(self.root)
        dialog.title("Registro de usuario")
        fields = ("username", "email", "nombre", "apellido_paterno", "apellido_materno", "password")
        inputs = {}
        for row, name in enumerate(fields):
            ttk.Label(dialog, text=name.replace("_", " ")).grid(row=row, column=0, padx=8, pady=5, sticky="w")
            entry = ttk.Entry(dialog, show="*" if name == "password" else "", width=34)
            entry.grid(row=row, column=1, padx=8, pady=5, sticky="ew")
            inputs[name] = entry

        def register():
            values = {name: field.get() for name, field in inputs.items()}
            self.api("login", "POST", "/register", values, auth=False,
                     on_success=lambda data: messagebox.showinfo("Registro", data.get("message", "Usuario registrado.")))
            dialog.destroy()

        ttk.Button(dialog, text="Registrar", command=register).grid(row=len(fields), column=1, padx=8, pady=10, sticky="e")
        dialog.columnconfigure(1, weight=1)

    def _check_health(self):
        for key, _label, _env, _default in SERVICES:
            light, dot = self.health_lights[key]
            light.itemconfigure(dot, fill=LIGHT_COLORS["off"])

            def complete(status, data, _error, light=light, dot=dot):
                if status == 200 and isinstance(data, dict) and data.get("status") in (None, "ok"):
                    color = "green"
                elif status is not None:
                    color = "amber"
                else:
                    color = "red"
                light.itemconfigure(dot, fill=LIGHT_COLORS[color])

            self.api(key, "GET", "/health", auth=False, on_complete=complete)

    # ==================== OPERACIONES CRUD ====================

    def _field_specs(self, tab):
        return {field[0]: field for field in tab["spec"]["fields"]}

    def _item_path(self, tab, suffix=""):
        spec = tab["spec"]
        identifier = tab["vars"][spec["id"]].get().strip()
        if not identifier:
            return None
        return f"{spec['path']}/{urllib.parse.quote(identifier, safe='')}{suffix}"

    def _payload(self, tab, keys=None):
        """Convierte el formulario en JSON; los campos vacios no se envian."""
        payload = {}
        specs = self._field_specs(tab)
        for key in keys or specs:
            _key, label, kind, *flags = specs[key]
            raw = tab["vars"][key].get().strip()
            if "path" in flags or raw == "":
                continue
            try:
                if kind == "int":
                    payload[key] = int(raw)
                elif kind == "decimal":
                    payload[key] = float(raw)
                elif kind == "bool":
                    payload[key] = raw == "true"
                elif kind == "list":
                    payload[key] = [item.strip() for item in raw.split(",") if item.strip()]
                elif kind == "lines":
                    payload[key] = []
                    for item in filter(str.strip, raw.split(",")):
                        isbn, _sep, quantity = item.strip().rpartition(":")
                        if not isbn.strip():
                            raise ValueError()
                        payload[key].append({"isbn": isbn.strip(), "quantity": int(quantity)})
                else:
                    payload[key] = raw
            except ValueError:
                raise ValueError(f"El campo '{label}' tiene un valor invalido.") from None
        return payload

    def _list(self, tab, access):
        spec = tab["spec"]
        params = {
            param: tab["vars"][field].get().strip()
            for param, field in spec.get("list_params", {}).items()
            if tab["vars"][field].get().strip()
        }
        self.api(spec["service"], "GET", spec["path"], params=params, auth=access != "public",
                 on_success=lambda data: self._fill_tree(tab, data))

    def _get(self, tab, access):
        path = self._item_path(tab)
        if path is None:
            messagebox.showinfo("Dato requerido", "Captura el identificador o selecciona un registro.")
            return

        def done(data):
            self._fill_form(tab, data)
            self._set_text(tab["detail"], data)

        self.api(tab["spec"]["service"], "GET", path, auth=access != "public", on_success=done)

    def _write(self, tab, method, keys=None):
        spec = tab["spec"]
        if method == "POST":
            path = spec["path"]
        else:
            path = self._item_path(tab)
            if path is None:
                messagebox.showinfo("Dato requerido", "Captura el identificador o selecciona un registro.")
                return
        payload = None
        if method != "DELETE":
            try:
                payload = self._payload(tab, keys)
            except ValueError as error:
                messagebox.showerror("Formulario", str(error))
                return
            if not payload:
                messagebox.showinfo("Formulario", "No hay datos para enviar.")
                return
        elif not messagebox.askyesno("Confirmar", "Eliminar el registro seleccionado?"):
            return
        self._send_write(tab, method, path, payload)

    def _send_write(self, tab, method, path, payload=None):
        def done(data):
            if "password" in tab["vars"]:
                tab["vars"]["password"].set("")
            self._set_text(tab["detail"], data)
            message = data.get("message") if isinstance(data, dict) else None
            messagebox.showinfo(tab["spec"]["title"], message or "Operacion completada.")

        self.api(tab["spec"]["service"], method, path, payload, on_success=done)

    def _show(self, tab, method, path, auth=True):
        if path is None:
            messagebox.showinfo("Dato requerido", "Captura el identificador o selecciona un registro.")
            return
        self.api(tab["spec"]["service"], method, path, auth=auth,
                 on_success=lambda data: self._set_text(tab["detail"], data))

    def _link_book(self, tab, relation):
        path = self._item_path(tab, "/books")
        isbn = relation["isbn"].get().strip()
        if path is None or not isbn:
            messagebox.showinfo("Dato requerido", "Captura el ID del autor y el ISBN.")
            return
        payload = {"isbn": isbn}
        order = relation["order"].get().strip()
        if order:
            if not order.isdigit():
                messagebox.showerror("Formulario", "El orden debe ser un entero positivo.")
                return
            payload["author_order"] = int(order)
        self._send_write(tab, "POST", path, payload)

    def _unlink_book(self, tab, relation):
        isbn = relation["isbn"].get().strip()
        path = self._item_path(tab, "/books/" + urllib.parse.quote(isbn, safe="")) if isbn else None
        if path is None:
            messagebox.showinfo("Dato requerido", "Captura el ID del autor y el ISBN.")
            return
        self._send_write(tab, "DELETE", path)

    def _line_request(self, tab, line, method):
        isbn = line["isbn"].get().strip()
        quantity = line["quantity"].get().strip()
        suffix = "/lineas" if method == "POST" else "/lineas/" + urllib.parse.quote(isbn, safe="")
        path = self._item_path(tab, suffix)
        if path is None or not isbn or (method != "DELETE" and not quantity.isdigit()):
            messagebox.showinfo("Dato requerido", "Captura ID de pedido, ISBN y una cantidad entera.")
            return
        payload = None
        if method == "POST":
            payload = {"isbn": isbn, "quantity": int(quantity)}
        elif method == "PATCH":
            payload = {"quantity": int(quantity)}
        self._send_write(tab, method, path, payload)

    def _show_stock(self, tab, line):
        isbn = line["isbn"].get().strip()
        path = "/stock/" + urllib.parse.quote(isbn, safe="") if isbn else "/stock"
        self._show(tab, "GET", path, auth=False)

    def _adjust_stock(self, tab, line):
        isbn = line["isbn"].get().strip()
        stock = line["quantity"].get().strip()
        if not isbn or not stock.isdigit():
            messagebox.showinfo("Dato requerido", "Captura el ISBN y el nuevo stock (entero >= 0).")
            return
        self._send_write(tab, "PATCH", "/stock/" + urllib.parse.quote(isbn, safe=""), {"stock": int(stock)})

    def _cancel_order(self, tab):
        path = self._item_path(tab)
        if path is None:
            messagebox.showinfo("Dato requerido", "Captura el ID del pedido.")
            return
        if messagebox.askyesno("Confirmar", "Cancelar el pedido? El stock se devolvera."):
            self._send_write(tab, "PATCH", path, {"status": "cancelled"})

    # ==================== TABLAS Y DETALLE ====================

    def _fill_tree(self, tab, data):
        tree = tab["tree"]
        tree.delete(*tree.get_children())
        tab["rows"] = {}
        rows = data if isinstance(data, list) else []
        columns = [column[0] for column in tab["spec"]["columns"]]
        for index, row in enumerate(rows):
            iid = str(index)
            tab["rows"][iid] = row
            tree.insert("", END, iid=iid, values=[display(row.get(key)) for key in columns])
        self._set_text(tab["detail"], {"registros": len(rows)})

    def _row_selected(self, tab):
        selection = tab["tree"].selection()
        if selection:
            self._fill_form(tab, tab["rows"].get(selection[0], {}))

    def _fill_form(self, tab, data):
        if not isinstance(data, dict):
            return
        for key, _label, kind, *_flags in tab["spec"]["fields"]:
            if kind == "password" or key not in data:
                continue
            value = data[key]
            if kind == "list" and isinstance(value, list):
                value = ", ".join(item.get("isbn", "") if isinstance(item, dict) else str(item) for item in value)
            elif kind == "lines" and isinstance(value, list):
                value = ", ".join(f"{item['isbn']}:{item['quantity']}" for item in value)
            tab["vars"][key].set(display(value))

    def _set_text(self, widget, data):
        widget.configure(state="normal")
        widget.delete("1.0", END)
        widget.insert(END, json.dumps(sanitize(data), ensure_ascii=False, indent=2, default=str))
        widget.configure(state="disabled")

    # ==================== HTTP ====================

    def api(self, service, method, path, payload=None, params=None, auth=True,
            on_success=None, on_complete=None):
        """Peticion asincrona; centraliza JWT, renovacion, errores y log sanitizado."""
        query = dict(params or {})
        query["format"] = "json"
        url = self.urls[service].get().strip().rstrip("/") + path + "?" + urllib.parse.urlencode(query)
        refresh_url = self.urls["login"].get().strip().rstrip("/") + "/refresh?format=json"
        omitted = auth and self.without_token.get()
        use_auth = auth and not omitted
        if use_auth and not self.token:
            messagebox.showinfo("Sesion", "Inicia sesion para realizar esta operacion.")
            return

        def worker():
            status, data, error, record = self._send(service, method, url, payload, use_auth)
            self.results.put(("log", record))
            if status == 401 and use_auth and self._try_refresh(refresh_url):
                status, data, error, record = self._send(service, method, url, payload, use_auth)
                self.results.put(("log", record))
            self.results.put(("result", {
                "service": service, "status": status, "data": data, "error": error,
                "on_success": on_success, "on_complete": on_complete, "used_auth": use_auth,
            }))

        threading.Thread(target=worker, daemon=True).start()

    def _send(self, service, method, url, payload, use_auth):
        request_id = str(uuid.uuid4())
        headers = {"Accept": "application/json", "X-Request-ID": request_id}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        with self.token_lock:
            token = self.token
        if use_auth and token:
            headers["Authorization"] = "Bearer " + token
        started = time.monotonic()
        status = None
        error = None
        cache = None
        raw = ""
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                status = response.status
                cache = response.headers.get("X-Cache")
                raw = response.read(1_000_000).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as response:
            status = response.code
            cache = response.headers.get("X-Cache")
            raw = response.read(1_000_000).decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exception:
            reason = getattr(exception, "reason", exception)
            error = "timeout" if isinstance(reason, TimeoutError) or "timed out" in str(reason) else "unavailable"
        try:
            response_data = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            response_data = {"error": "Respuesta no valida del servicio."}
        record = {
            "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
            "request_id": request_id,
            "servicio": service,
            "metodo": method,
            "url": sanitize_url(url),
            "headers": sanitize(headers),
            "payload": sanitize(payload),
            "estado_http": status,
            "x_cache": cache,
            "duracion_ms": round((time.monotonic() - started) * 1000, 2),
            "respuesta": sanitize(response_data),
            "error": error,
        }
        return status, response_data, error, record

    def _try_refresh(self, refresh_url):
        """Ante un 401 intenta una sola renovacion con el refresh token en memoria."""
        with self.token_lock:
            refresh_token = self.refresh_token
        if not refresh_token:
            return False
        status, data, _error, record = self._send("login", "POST", refresh_url,
                                                  {"refresh_token": refresh_token}, False)
        self.results.put(("log", record))
        if status == 200 and isinstance(data, dict) and data.get("access_token"):
            self.results.put(("tokens", data))
            with self.token_lock:
                self.token = data["access_token"]
                self.refresh_token = data.get("refresh_token")
            return True
        return False

    def _poll_results(self):
        while True:
            try:
                kind, item = self.results.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._append_log(item)
            elif kind == "tokens":
                self._store_tokens(item)
                self._apply_role()
            else:
                self._handle_result(item)
        self.root.after(100, self._poll_results)

    def _handle_result(self, result):
        status, data, error = result["status"], result["data"], result["error"]
        if result["on_complete"]:
            result["on_complete"](status, data, error)
            return
        service = result["service"]
        if error:
            if error == "timeout":
                messagebox.showerror("Tiempo agotado", f"El microservicio {service} no respondio a tiempo.")
            else:
                messagebox.showerror("Servicio no disponible",
                                     f"No se pudo conectar con el microservicio {service}. Revisa que este iniciado.")
            return
        if status is not None and 200 <= status < 300:
            if result["on_success"]:
                result["on_success"](data)
            return
        server_message = ""
        if isinstance(data, dict):
            server_message = str(data.get("error") or data.get("message") or "")[:300]
        friendly = STATUS_MESSAGES.get(status, f"El servicio respondio con estado {status}.")
        if status == 401 and result["used_auth"]:
            self._clear_session()
            friendly = "Tu sesion expiro o el JWT fue revocado. Inicia sesion de nuevo."
        elif status == 401 and service == "login":
            friendly = "Credenciales o refresh token invalidos."
        detail = f"\n\nDetalle: {server_message}" if server_message else ""
        messagebox.showerror(f"{service} - HTTP {status}", friendly + detail)

    # ==================== LOG ====================

    def _append_log(self, record):
        self.log.configure(state="normal")
        self.log.insert(END, json.dumps(record, ensure_ascii=False, indent=2) + "\n\n")
        lines = int(self.log.index("end-1c").split(".")[0])
        if lines > 4000:
            self.log.delete("1.0", f"{lines - 4000}.0")
        self.log.see(END)
        self.log.configure(state="disabled")

    def _copy_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log.get("1.0", END))

    def _export_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=(("Text", "*.txt"),))
        if path:
            with open(path, "w", encoding="utf-8") as output:
                output.write(self.log.get("1.0", END))

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", END)
        self.log.configure(state="disabled")


if __name__ == "__main__":
    root = Tk()
    LibraryClient(root)
    root.mainloop()
