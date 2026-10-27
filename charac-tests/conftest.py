"""Shared helpers for the characterization tests of OSWA-INV (black-box, over HTTP).

The tests talk to the running application and to its real MariaDB database.
They never import or touch the PHP code. Configure with environment variables:

  BASE_URL      default http://127.0.0.1:8080
  APP_DIR       default /root/baseline/warehouse-inventory-system (only read by a few 'change' tests)
  SQL_FILE      schema/seed loaded before every test (default APP_DIR/oswa_inv.sql)
  DB_NAME       default oswa_inv
  MYSQL_CMD     default "mysql" (must reach the database without a prompt)
  ADMIN_USER / ADMIN_PASS, SPECIAL_USER / SPECIAL_PASS, USER_USER / USER_PASS
                credentials of the three seeded accounts (default: the public defaults)
"""
import html
import os
import re
import subprocess
from collections import namedtuple

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8080").rstrip("/")
APP_DIR = os.environ.get("APP_DIR", "/root/baseline/warehouse-inventory-system")
SQL_FILE = os.environ.get("SQL_FILE", os.path.join(APP_DIR, "oswa_inv.sql"))
DB_NAME = os.environ.get("DB_NAME", "oswa_inv")
MYSQL = os.environ.get("MYSQL_CMD", "mysql").split()


def _cred(role, default_user, default_pass):
    return (
        os.environ.get(f"{role.upper()}_USER", default_user),
        os.environ.get(f"{role.upper()}_PASS", default_pass),
    )


# The original ships three seeded accounts (admin/admin ...). Once the app has bin/create_user.php there are
# no default accounts: the fixture creates the three test accounts through that script, with strong passwords.
HAS_CREATE_SCRIPT = os.path.exists(os.path.join(APP_DIR, "bin", "create_user.php"))
_STRONG = {"admin": "Admin-test-pass-1", "special": "Special-test-pass-1", "user": "User-test-pass-1"}
CREDS = {
    role: _cred(role, role, _STRONG[role] if HAS_CREATE_SCRIPT else role)
    for role in ("admin", "special", "user")
}
_ACCOUNTS = (("admin", " Admin User", 1), ("special", "Special User", 2), ("user", "Default User", 3))


def create_user_via_cli(username, name, level, password, extra_env=None):
    env = dict(os.environ, OSWA_NEW_PASSWORD=password, **(extra_env or {}))
    return subprocess.run(
        ["php", os.path.join(APP_DIR, "bin", "create_user.php"), username, name, str(level)],
        capture_output=True, text=True, env=env,
    )

# the modernised app has an anti-CSRF token in every page (tests keep working on both versions)
HAS_CSRF_SUPPORT = os.path.exists(os.path.join(APP_DIR, "includes", "session.php")) and \
    "csrf_token" in open(os.path.join(APP_DIR, "includes", "session.php"), encoding="utf-8", errors="replace").read()

ALERT = re.compile(r'<div class="alert alert-(\w+)"><a[^>]*>&times;</a>(.*?)</div>', re.S)

Outcome = namedtuple("Outcome", "status location flash flash_type")


# --------------------------------------------------------------------------- database
def sql(query):
    """Run a query on the real database; returns a list of rows (lists of strings)."""
    out = subprocess.run(
        MYSQL + ["-N", "-B", DB_NAME, "-e", query],
        capture_output=True, text=True, check=True,
    ).stdout
    return [line.split("\t") for line in out.splitlines()]


def sql_value(query):
    rows = sql(query)
    return rows[0][0] if rows else None


@pytest.fixture(autouse=True)
def fresh_db():
    """Reload the schema and seed data before every test, so tests are independent and repeatable."""
    subprocess.run(
        MYSQL + ["-e", f"DROP DATABASE IF EXISTS {DB_NAME}; CREATE DATABASE {DB_NAME}"],
        check=True,
    )
    with open(SQL_FILE, "rb") as fh:
        subprocess.run(MYSQL + [DB_NAME], stdin=fh, check=True)
    if HAS_CREATE_SCRIPT:
        for role, name, level in _ACCOUNTS:
            r = create_user_via_cli(CREDS[role][0], name, level, CREDS[role][1])
            assert r.returncode == 0, r.stderr + r.stdout


@pytest.fixture(scope="session", autouse=True)
def app_is_up():
    try:
        requests.get(BASE_URL + "/", timeout=5)
    except requests.RequestException as exc:
        pytest.exit(f"Application not reachable at {BASE_URL} ({exc}). Run ./run_app.sh first.", returncode=2)


# --------------------------------------------------------------------------- HTTP client
class Client:
    """A browser-like session that never follows redirects on its own (we want to see them)."""

    def __init__(self):
        self.s = requests.Session()
        self._token = None

    def get(self, path, **kw):
        return self.s.get(f"{BASE_URL}/{path}", allow_redirects=False, timeout=15, **kw)

    def csrf_token(self, refresh=False):
        """Like a browser: read the token the app puts in its pages (None for an app that has none)."""
        if refresh or self._token is None:
            page = self.s.get(f"{BASE_URL}/index.php", allow_redirects=False, timeout=15)
            m = re.search(r'name="csrf-token" content="([0-9a-f]+)"', page.text)
            self._token = m.group(1) if m else ""
        return self._token

    def post(self, path, data=None, token=True, **kw):
        """POST like a browser form: the CSRF token is sent unless token=False."""
        if token and data is None and "files" in kw:
            data = {}
        if token and data is not None and "csrf_token" not in data:
            tok = self.csrf_token()
            if tok:
                data = dict(data, csrf_token=tok)
        resp = self.s.post(f"{BASE_URL}/{path}", data=data, allow_redirects=False, timeout=15, **kw)
        if token and resp.status_code == 403 and "security token" in resp.text and data is not None:
            data = dict(data, csrf_token=self.csrf_token(refresh=True))
            resp = self.s.post(f"{BASE_URL}/{path}", data=data, allow_redirects=False, timeout=15, **kw)
        return resp

    def delete(self, path):
        """Deleting is a button inside a form in the modernised app (a plain link in the original)."""
        if HAS_CSRF_SUPPORT:
            return self.post(path, {})
        return self.get(path)

    def login_as(self, username, password):
        self._token = None  # a new login starts from a fresh page, like a browser
        return self.post("auth.php", {"username": username, "password": password})

    def login(self, role):
        return self.login_as(*CREDS[role])

    def outcome(self, resp):
        """Status, redirect target, and the flash message the redirect target displays.

        The app stores a one-shot message in the session and shows it on the *next* page,
        so we fetch the redirect target immediately to read it.
        """
        loc = resp.headers.get("Location")
        flash = ftype = None
        if resp.status_code in (301, 302) and loc:
            nxt = self.get(loc)
            m = ALERT.search(nxt.text)
            if m:
                ftype, flash = m.group(1), html.unescape(m.group(2)).strip()
        return Outcome(resp.status_code, loc, flash, ftype)

    def do(self, method, path, data=None):
        if method == "DELETE":
            resp = self.delete(path)
        else:
            resp = self.get(path) if method == "GET" else self.post(path, data)
        return self.outcome(resp)


def logged_in(role):
    c = Client()
    r = c.login(role)
    assert r.status_code == 302 and r.headers.get("Location", "").endswith("home.php"), \
        f"could not log in as {role}: HTTP {r.status_code} {r.headers.get('Location')}"
    return c


@pytest.fixture
def admin():
    return logged_in("admin")


@pytest.fixture
def special():
    return logged_in("special")


@pytest.fixture
def user():
    return logged_in("user")


# --------------------------------------------------------------------------- data helpers (through the app)
def add_category(client, name="Tools"):
    out = client.do("POST", "categorie.php", {"categorie-name": name, "add_cat": ""})
    assert out.status == 302, out
    return int(sql_value(f"SELECT id FROM categories WHERE name='{name}' ORDER BY id DESC LIMIT 1"))


def add_product(client, title="Hammer", category_id=None, qty="10", buy="5", sale="9", photo=""):
    if category_id is None:
        category_id = add_category(client)
    out = client.do("POST", "add_product.php", {
        "product-title": title, "product-categorie": str(category_id),
        "product-quantity": qty, "buying-price": buy, "saleing-price": sale,
        "product-photo": photo, "add_product": "",
    })
    assert out.status == 302, out
    return int(sql_value(f"SELECT id FROM products WHERE name='{title}' ORDER BY id DESC LIMIT 1"))


def add_sale(client, product_id, qty="2", price="9", total="18", date="2000-01-01"):
    return client.do("POST", "add_sale.php", {
        "s_id": str(product_id), "quantity": qty, "price": price,
        "total": total, "date": date, "add_sale": "",
    })


def add_user(client, name="New Person", username="newperson", password="Secret-123", level="3"):
    return client.do("POST", "add_user.php", {
        "full-name": name, "username": username, "password": password,
        "level": level, "add_user": "",
    })
