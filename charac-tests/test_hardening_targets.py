"""Current behaviour that the modernisation is EXPECTED to change.

Every test here passes today and documents a weakness or a crash. After hardening, each one that
starts failing is proof the weakness is gone (and the test is then replaced by its secure twin).
They deliberately use the original default values, not the environment variables.
"""
import hashlib
import os
import re
import stat

import pytest
import requests

from conftest import APP_DIR, BASE_URL, CREDS, Client, add_category, add_product, add_user, sql, sql_value

pytestmark = pytest.mark.change

DEFAULTS = [("admin", "admin"), ("special", "special"), ("user", "user")]


@pytest.mark.parametrize("username,password", DEFAULTS)
def test_default_accounts_are_accepted(username, password):
    c = Client()
    r = c.login_as(username, password)
    assert (r.status_code, r.headers.get("Location")) == (302, "home.php")


@pytest.mark.parametrize("username,password", DEFAULTS)
def test_seeded_passwords_are_unsalted_sha1(username, password):
    stored = sql_value(f"SELECT password FROM users WHERE username='{username}'")
    assert stored == hashlib.sha1(password.encode()).hexdigest()


def test_two_users_with_the_same_password_get_the_same_hash(admin):
    add_user(admin, username="aa", password="Same-Password-1")
    add_user(admin, username="bb", password="Same-Password-1")
    rows = sql("SELECT password FROM users WHERE username IN ('aa','bb')")
    assert len(rows) == 2 and rows[0][0] == rows[1][0]


def test_a_one_character_password_is_accepted(admin):
    out = add_user(admin, username="weak", password="a")
    assert (out.flash_type, out.flash) == ("success", "User account has been creted!")


def test_cross_site_post_without_any_token_is_accepted(admin):
    """No CSRF token and no Origin/Referer check: a request coming from another site is honoured."""
    out = admin.outcome(admin.s.post(
        f"{BASE_URL}/categorie.php", data={"categorie-name": "Planted", "add_cat": ""},
        headers={"Origin": "https://evil.example", "Referer": "https://evil.example/page"},
        allow_redirects=False, timeout=15))
    assert out.status == 302
    assert sql_value("SELECT COUNT(*) FROM categories WHERE name='Planted'") == "1"


def test_a_cross_site_link_can_delete_data(admin):
    """Deleting is a plain GET with only the session cookie as protection."""
    pid = add_product(admin)
    r = admin.s.get(f"{BASE_URL}/delete_product.php?id={pid}", headers={"Referer": "https://evil.example/"},
                    allow_redirects=False, timeout=15)
    assert r.status_code == 302
    assert sql_value("SELECT COUNT(*) FROM products") == "0"


def test_session_cookie_has_no_security_flags():
    r = requests.get(BASE_URL + "/index.php", timeout=15)
    cookie = r.headers.get("Set-Cookie", "")
    assert "PHPSESSID" in cookie
    assert "httponly" not in cookie.lower()
    assert "samesite" not in cookie.lower()


def test_session_id_is_not_renewed_at_login():
    """Session fixation: the id used before login is the id that becomes authenticated."""
    c = Client()
    c.get("index.php")
    before = c.s.cookies.get("PHPSESSID")
    assert before
    c.login_as(*CREDS["admin"])
    assert c.s.cookies.get("PHPSESSID") == before
    assert c.get("home.php").status_code == 200


def test_ajax_unknown_product_crashes_with_http_500(admin):
    """Bug on current PHP versions: addslashes() is called without an argument in the 'not found' branch."""
    r = admin.post("ajax.php", {"product_name": "no-such-product"})
    assert r.status_code == 500


def test_database_password_is_written_in_the_code():
    with open(os.path.join(APP_DIR, "includes", "config.php")) as fh:
        text = fh.read()
    assert re.search(r"define\(\s*'DB_PASS'\s*,\s*'[^']+'\s*\)", text)


def test_upload_folders_are_world_writable():
    """The README tells the installer to chmod 777 the upload folders."""
    for sub in ("uploads", "uploads/products", "uploads/users"):
        mode = os.stat(os.path.join(APP_DIR, sub)).st_mode
        assert mode & stat.S_IWOTH, f"{sub} is not world-writable"
