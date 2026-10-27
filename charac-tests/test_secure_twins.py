"""Secure twins of the 'change' tests: they FAIL on the original code and must PASS once the weakness is fixed.

Run the original code with `-m change` (all pass = weaknesses present) and the modernised code with
`-m "keep or secure"`. One twin is added per step of the modernisation plan.
"""
import os
import re
import subprocess

import pytest
import requests

from conftest import APP_DIR, CREDS, Client, add_user, logged_in, sql, sql_value
CREDS_ADMIN = CREDS["admin"]

pytestmark = pytest.mark.secure

CONFIG = os.path.join(APP_DIR, "includes", "config.php")


# ---- step 1: secrets out of the code
def test_database_password_is_not_written_in_the_code():
    with open(CONFIG) as fh:
        text = fh.read()
    assert not re.search(r"define\(\s*'DB_PASS'\s*,\s*'[^']+'\s*\)", text), "a literal DB password is still in config.php"
    assert "OSWA_DB_PASS" in text


def test_app_refuses_to_start_without_database_credentials():
    env = {k: v for k, v in os.environ.items() if not k.startswith("OSWA_")}
    r = subprocess.run(
        ["php", "-r", "require 'includes/config.php';"],
        cwd=APP_DIR, env=env, capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "Configuration error" in r.stdout


# ---- step 2: salted password hashes, old SHA1 accounts upgraded at login
BCRYPT = re.compile(r"^\$2y\$\d\d\$")
LEGACY_USER, LEGACY_PASSWORD = "legacy", "Legacy-pass-1"


def _insert_legacy_sha1_user():
    sql(f"INSERT INTO users (name, username, password, user_level, status) "
        f"VALUES ('Legacy User', '{LEGACY_USER}', SHA1('{LEGACY_PASSWORD}'), 3, 1)")
    stored = sql_value(f"SELECT password FROM users WHERE username='{LEGACY_USER}'")
    assert re.fullmatch(r"[0-9a-f]{40}", stored)
    return stored


def test_new_users_get_salted_hashes(admin):
    add_user(admin, username="aa", password="Same-Password-1")
    add_user(admin, username="bb", password="Same-Password-1")
    rows = sql("SELECT password FROM users WHERE username IN ('aa','bb')")
    assert len(rows) == 2
    assert rows[0][0] != rows[1][0], "same password must not give the same hash"
    assert all(BCRYPT.match(r[0]) for r in rows)


def test_change_password_stores_a_salted_hash(admin):
    add_user(admin, username="cp", password="Start-Pass-1")
    uid = sql_value("SELECT id FROM users WHERE username='cp'")
    c = Client()
    assert c.login_as("cp", "Start-Pass-1").status_code == 302
    c.do("POST", "change_password.php", {"old-password": "Start-Pass-1", "new-password": "Next-Pass-22", "id": uid, "update": ""})
    assert BCRYPT.match(sql_value("SELECT password FROM users WHERE username='cp'"))
    assert Client().login_as("cp", "Next-Pass-22").headers.get("Location") == "home.php"


def test_edit_user_password_stores_a_salted_hash(admin):
    add_user(admin, username="ep", password="Start-Pass-1")
    uid = sql_value("SELECT id FROM users WHERE username='ep'")
    out = admin.do("POST", f"edit_user.php?id={uid}", {"password": "Admin-Set-Pass-3", "update-pass": ""})
    assert out.flash_type == "success"
    assert BCRYPT.match(sql_value("SELECT password FROM users WHERE username='ep'"))
    assert Client().login_as("ep", "Admin-Set-Pass-3").headers.get("Location") == "home.php"


def test_legacy_sha1_account_still_logs_in_and_is_upgraded():
    _insert_legacy_sha1_user()
    c = Client()
    assert c.login_as(LEGACY_USER, LEGACY_PASSWORD).headers.get("Location") == "home.php"
    assert BCRYPT.match(sql_value(f"SELECT password FROM users WHERE username='{LEGACY_USER}'"))
    assert Client().login_as(LEGACY_USER, LEGACY_PASSWORD).headers.get("Location") == "home.php"


def test_wrong_password_neither_logs_in_nor_upgrades_a_legacy_account():
    before = _insert_legacy_sha1_user()
    assert Client().login_as(LEGACY_USER, "not-the-password").headers.get("Location") == "index.php"
    assert sql_value(f"SELECT password FROM users WHERE username='{LEGACY_USER}'") == before


# ---- step 3: no default accounts, minimum password length, account creation from the command line
import subprocess
from conftest import HAS_CREATE_SCRIPT, create_user_via_cli, sql as _sql


def test_no_default_account_exists_after_install():
    """Load only the schema (no CLI account creation): the database must contain no user."""
    # fresh_db already created our test accounts; check the seed file itself.
    from conftest import SQL_FILE
    text = open(SQL_FILE, encoding="utf-8", errors="replace").read()
    assert "INSERT INTO `users`" not in text, "the SQL file still seeds user accounts"


@pytest.mark.parametrize("username,password", [("admin", "admin"), ("special", "special"), ("user", "user")])
def test_default_credentials_are_rejected(username, password):
    r = Client().login_as(username, password)
    assert (r.status_code, r.headers.get("Location")) == (302, "index.php")


def test_a_one_character_password_is_refused(admin):
    out = add_user(admin, username="weak", password="a")
    assert out.flash_type == "danger"
    assert sql_value("SELECT COUNT(*) FROM users WHERE username='weak'") == "0"


def test_a_short_new_password_is_refused_at_change(admin):
    add_user(admin, username="shorty", password="Start-Pass-1")
    c = Client(); c.login_as("shorty", "Start-Pass-1")
    uid = sql_value("SELECT id FROM users WHERE username='shorty'")
    out = c.do("POST", "change_password.php", {"old-password": "Start-Pass-1", "new-password": "abc", "id": uid, "update": ""})
    assert out.flash_type == "danger"
    assert Client().login_as("shorty", "Start-Pass-1").headers.get("Location") == "home.php"


def test_a_short_password_is_refused_by_admin_reset(admin):
    add_user(admin, username="rs", password="Start-Pass-1")
    uid = sql_value("SELECT id FROM users WHERE username='rs'")
    out = admin.do("POST", f"edit_user.php?id={uid}", {"password": "abc", "update-pass": ""})
    assert out.flash_type == "danger"
    assert Client().login_as("rs", "Start-Pass-1").headers.get("Location") == "home.php"


def test_create_script_makes_a_working_admin():
    assert HAS_CREATE_SCRIPT, "bin/create_user.php is missing"
    r = create_user_via_cli("boss", "The Boss", 1, "Boss-pass-1234")
    assert r.returncode == 0, r.stderr
    assert Client().login_as("boss", "Boss-pass-1234").headers.get("Location") == "home.php"
    assert BCRYPT.match(sql_value("SELECT password FROM users WHERE username='boss'"))


def test_create_script_refuses_a_weak_password_and_a_duplicate():
    assert HAS_CREATE_SCRIPT, "bin/create_user.php is missing"
    assert create_user_via_cli("weakling", "W", 3, "short").returncode != 0
    assert sql_value("SELECT COUNT(*) FROM users WHERE username='weakling'") == "0"
    assert create_user_via_cli("boss2", "B", 1, "Boss-pass-1234").returncode == 0
    assert create_user_via_cli("boss2", "B", 1, "Boss-pass-1234").returncode != 0


# ---- step 4: prepared statements, no database detail shown to visitors
def test_a_database_error_shows_no_sql_and_a_generic_message(admin):
    r = admin.post("add_product.php", {"product-title": "x", "product-categorie": "abc", "product-quantity": "zz",
                                       "buying-price": "1", "saleing-price": "1", "product-photo": "", "add_product": ""})
    assert r.status_code == 500
    assert "A database error occurred." in r.text
    assert not re.search(r"INSERT|SELECT|UPDATE|mysqli|SQL syntax", r.text, re.I)


@pytest.mark.parametrize("payload", ["' OR '1'='1' -- ", "admin'-- ", "x' OR 1=1 #", "\\' OR 1=1 -- "])
def test_sql_injection_in_the_login_form_does_not_log_in(payload):
    r = Client().login_as(payload, payload)
    assert (r.status_code, r.headers.get("Location")) == (302, "index.php")


def test_quotes_and_backslashes_in_a_name_are_stored_and_do_not_break_queries(admin):
    out = add_user(admin, name="O'Brien \\ x", username="ob", password="Quote-pass-12")
    assert out.flash_type == "success"
    assert sql_value("SELECT COUNT(*) FROM users WHERE username='ob'") == "1"


def test_no_query_is_built_by_pasting_request_values_into_sql():
    import glob
    offenders = []
    for path in glob.glob(os.path.join(APP_DIR, "*.php")) + glob.glob(os.path.join(APP_DIR, "includes", "*.php")):
        text = open(path, encoding="utf-8", errors="replace").read()
        for n, line in enumerate(text.splitlines(), 1):
            if re.search(r"\$_(POST|GET|REQUEST)\[", line) and re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b.*['\"]\s*\.|\{\$_(POST|GET)", line):
                offenders.append(f"{os.path.basename(path)}:{n}")
    assert not offenders, offenders
    # escaping by hand is replaced by bound parameters everywhere except the password derivation kept for compatibility
    for path in glob.glob(os.path.join(APP_DIR, "*.php")):
        text = open(path, encoding="utf-8", errors="replace").read()
        assert "$db->query(" not in text, os.path.basename(path)


# ---- step 5: anti-CSRF token on every POST, deletions only by POST
from conftest import BASE_URL


def _raw_post(client, path, data, headers=None):
    return client.s.post(f"{BASE_URL}/{path}", data=data, headers=headers or {}, allow_redirects=False, timeout=15)


def test_post_without_a_token_is_refused(admin):
    r = _raw_post(admin, "categorie.php", {"categorie-name": "Planted", "add_cat": ""},
                  {"Origin": "https://evil.example", "Referer": "https://evil.example/page"})
    assert r.status_code == 403
    assert sql_value("SELECT COUNT(*) FROM categories WHERE name='Planted'") == "0"


def test_post_with_a_wrong_token_is_refused(admin):
    r = _raw_post(admin, "categorie.php", {"categorie-name": "Planted", "add_cat": "", "csrf_token": "0" * 64})
    assert r.status_code == 403
    assert sql_value("SELECT COUNT(*) FROM categories WHERE name='Planted'") == "0"


def test_a_token_from_another_session_is_refused(admin):
    other = Client()
    foreign = other.csrf_token()
    r = _raw_post(admin, "categorie.php", {"categorie-name": "Planted", "add_cat": "", "csrf_token": foreign})
    assert r.status_code == 403


def test_the_login_form_is_protected_too():
    r = _raw_post(Client(), "auth.php", {"username": CREDS_ADMIN[0], "password": CREDS_ADMIN[1]})
    assert r.status_code == 403


def test_a_link_cannot_delete_data(admin):
    from conftest import add_product
    pid = add_product(admin)
    r = admin.s.get(f"{BASE_URL}/delete_product.php?id={pid}", headers={"Referer": "https://evil.example/"},
                    allow_redirects=False, timeout=15)
    assert r.status_code == 405
    assert sql_value("SELECT COUNT(*) FROM products") == "1"


def test_deleting_with_the_token_still_works(admin):
    from conftest import add_product
    pid = add_product(admin)
    out = admin.do("DELETE", f"delete_product.php?id={pid}")
    assert out.status == 302
    assert sql_value("SELECT COUNT(*) FROM products") == "0"


def test_every_form_in_the_pages_carries_the_token(admin):
    for page in ("add_product.php", "add_user.php", "categorie.php", "change_password.php", "sales_report.php", "add_group.php"):
        assert 'name="csrf_token"' in admin.get(page).text, page
    assert 'name="csrf_token"' in Client().get("index.php").text


def test_ajax_accepts_the_token_in_a_header(admin):
    tok = admin.csrf_token()
    r = _raw_post(admin, "ajax.php", {"product_name": "zz"}, {"X-CSRF-Token": tok})
    assert r.status_code != 403
    r = _raw_post(admin, "ajax.php", {"product_name": "zz"})
    assert r.status_code == 403


# ---- step 6: session cookie flags, new session id at login
def test_session_cookie_has_httponly_and_samesite():
    cookie = requests.get(BASE_URL + "/index.php", timeout=15).headers.get("Set-Cookie", "")
    assert "PHPSESSID" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()


def test_session_id_is_renewed_at_login():
    c = Client()
    c.get("index.php")
    before = c.s.cookies.get("PHPSESSID")
    c.login_as(*CREDS["admin"])
    after = c.s.cookies.get("PHPSESSID")
    assert after and after != before
    assert c.get("home.php").status_code == 200


def test_an_old_session_id_does_not_work_after_login():
    c = Client()
    c.get("index.php")
    old = c.s.cookies.get("PHPSESSID")
    c.login_as(*CREDS["admin"])
    r = requests.get(BASE_URL + "/home.php", cookies={"PHPSESSID": old}, allow_redirects=False, timeout=15)
    assert r.status_code == 302


def test_an_unknown_session_id_is_not_adopted():
    r = requests.get(BASE_URL + "/index.php", cookies={"PHPSESSID": "attackerchosenid1234567890abcdef"}, timeout=15)
    assert "attackerchosenid1234567890abcdef" not in r.headers.get("Set-Cookie", "")


# ---- step 7: crash and warning fixes
def test_ajax_unknown_product_answers_normally(admin):
    r = admin.post("ajax.php", {"product_name": "no-such-product"})
    assert r.status_code == 200
    assert "Not found" in r.text


def test_a_deactivated_group_is_really_blocked():
    """The code had a 'this level user has been band' check that could never trigger."""
    c = logged_in("user")
    assert c.get("home.php").status_code == 200
    sql("UPDATE user_groups SET group_status=0 WHERE group_level=3")
    out = c.outcome(c.get("sales.php"))
    assert (out.status, out.location) == (302, "index.php")
    assert out.flash == "This level user has been band!"


# ---- step 8: one-command install, upload folders not world-writable
import time

INSTALL = os.path.join(APP_DIR, "install.sh")
INSTALL_DB = "oswa_install_check"


def _run_install(**extra):
    env = dict(os.environ, OSWA_DB_USER="oswa_install", OSWA_DB_PASS="Install-db-pass-1",
               OSWA_DB_NAME=INSTALL_DB, OSWA_NEW_PASSWORD="Install-admin-1", **extra)
    return subprocess.run(["bash", INSTALL], capture_output=True, text=True, env=env, cwd=APP_DIR)


@pytest.fixture
def clean_install_db():
    drop = f"DROP DATABASE IF EXISTS {INSTALL_DB}"
    subprocess.run(["mysql", "-e", drop], check=True)
    yield
    subprocess.run(["mysql", "-e", drop], check=True)


def test_install_script_sets_up_a_working_database_and_admin(clean_install_db):
    assert os.path.exists(INSTALL), "install.sh is missing"
    t0 = time.time()
    r = _run_install()
    elapsed = time.time() - t0
    print(f"\ninstall.sh took {elapsed:.1f}s")
    assert r.returncode == 0, r.stderr + r.stdout
    rows = sql(f"SELECT username, user_level FROM {INSTALL_DB}.users")
    assert rows == [["admin", "1"]]
    assert BCRYPT.match(sql_value(f"SELECT password FROM {INSTALL_DB}.users"))
    assert sql_value(f"SELECT COUNT(*) FROM {INSTALL_DB}.user_groups") == "3"
    assert elapsed < 30


def test_install_script_refuses_an_existing_installation_and_weak_passwords(clean_install_db):
    assert _run_install().returncode == 0
    again = _run_install()
    assert again.returncode != 0 and "refusing" in again.stderr
    subprocess.run(["mysql", "-e", f"DROP DATABASE {INSTALL_DB}"], check=True)
    weak = subprocess.run(["bash", INSTALL], capture_output=True, text=True, cwd=APP_DIR,
                          env=dict(os.environ, OSWA_DB_USER="oswa_install", OSWA_DB_PASS="Install-db-pass-1",
                                   OSWA_DB_NAME=INSTALL_DB, OSWA_NEW_PASSWORD="short"))
    assert weak.returncode != 0


def test_upload_folders_are_not_world_writable(clean_install_db):
    assert _run_install().returncode == 0
    for sub in ("uploads", "uploads/products", "uploads/users"):
        mode = os.stat(os.path.join(APP_DIR, sub)).st_mode & 0o777
        assert not mode & 0o002, f"{sub} is {oct(mode)}"
