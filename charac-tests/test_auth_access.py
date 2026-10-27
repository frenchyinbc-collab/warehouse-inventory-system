"""Login, logout and page-level access control. Everything here must NOT change."""
import re

import pytest

from conftest import CREDS, Client, add_product, logged_in, sql, sql_value

pytestmark = pytest.mark.keep

# page -> access level required by the app (1 = admin, 2 = special, 3 = user; a user may open a page
# when their level number is <= the page's level number)
PAGE_LEVEL = {
    "users.php": 1, "group.php": 1, "categorie.php": 1, "add_user.php": 1,
    "product.php": 2, "add_product.php": 2, "media.php": 2,
    "sales.php": 3, "add_sale.php": 3, "sales_report.php": 3,
    "daily_sales.php": 3, "monthly_sales.php": 3, "change_password.php": 3,
}
ROLE_LEVEL = {"admin": 1, "special": 2, "user": 3}
ROLES = list(ROLE_LEVEL)


# ------------------------------------------------------------------ login / logout
def test_login_page_shows_the_form():
    r = Client().get("index.php")
    assert r.status_code == 200
    assert 'action="auth.php"' in r.text
    # the original HTML writes `name= "password"` (with a space), so match loosely
    assert re.search(r'name=\s*"username"', r.text) and re.search(r'name=\s*"password"', r.text)


@pytest.mark.parametrize("role", ROLES)
def test_login_succeeds_with_valid_credentials(role):
    c = Client()
    out = c.outcome(c.login(role))
    assert out.status == 302
    assert out.location == "home.php"
    assert (out.flash_type, out.flash) == ("success", "Welcome to OSWA INV.")


@pytest.mark.parametrize("role", ROLES)
def test_home_page_opens_after_login(role):
    c = logged_in(role)
    r = c.get("home.php")
    assert r.status_code == 200
    assert "Home Page" in r.text


def test_login_rejects_wrong_password():
    c = Client()
    out = c.outcome(c.login_as(CREDS["admin"][0], "definitely-wrong"))
    assert (out.status, out.location) == (302, "index.php")
    assert (out.flash_type, out.flash) == ("danger", "Sorry Username/Password incorrect.")


def test_login_rejects_unknown_user():
    c = Client()
    out = c.outcome(c.login_as("nobody-here", "whatever"))
    assert (out.status, out.location) == (302, "index.php")
    assert out.flash == "Sorry Username/Password incorrect."


def test_login_rejects_blank_username():
    c = Client()
    out = c.outcome(c.login_as("", "x"))
    assert (out.status, out.location) == (302, "index.php")
    assert out.flash_type == "danger" and "can't be blank" in out.flash


def test_login_rejects_blank_password():
    c = Client()
    out = c.outcome(c.login_as(CREDS["admin"][0], ""))
    assert (out.status, out.location) == (302, "index.php")
    assert out.flash_type == "danger" and "can't be blank" in out.flash


@pytest.mark.parametrize("payload", ["admin' OR '1'='1", "' OR 1=1 -- ", "admin'--"])
def test_login_is_not_bypassed_by_sql_injection_probes(payload):
    c = Client()
    out = c.outcome(c.login_as(payload, "x"))
    assert (out.status, out.location) == (302, "index.php")
    assert out.flash == "Sorry Username/Password incorrect."
    after = c.get("home.php")
    assert (after.status_code, after.headers.get("Location")) == (302, "index.php")


def test_login_updates_last_login_time():
    username = CREDS["admin"][0]
    before = sql_value(f"SELECT last_login FROM users WHERE username='{username}'")
    # original: seeded with a 2015 date; modernised: account created by the CLI, never logged in (NULL)
    assert before in ("NULL", None) or before.startswith("2015")
    logged_in("admin")
    after = sql_value(f"SELECT last_login FROM users WHERE username='{username}'")
    assert after not in ("NULL", None) and not after.startswith("2015")


def test_logout_ends_the_session():
    c = logged_in("admin")
    r = c.get("logout.php")
    assert (r.status_code, r.headers.get("Location")) == (302, "index.php")
    after = c.get("home.php")
    assert (after.status_code, after.headers.get("Location")) == (302, "index.php")


# ------------------------------------------------------------------ not logged in
def test_home_requires_login():
    r = Client().get("home.php")
    assert (r.status_code, r.headers.get("Location")) == (302, "index.php")


@pytest.mark.parametrize("page", sorted(PAGE_LEVEL))
def test_protected_pages_redirect_anonymous_visitors_to_login(page):
    c = Client()
    out = c.do("GET", page)
    assert (out.status, out.location) == (302, "index.php")
    assert (out.flash_type, out.flash) == ("danger", "Please login...")


def test_anonymous_post_cannot_create_a_product():
    c = Client()
    out = c.do("POST", "add_product.php", {
        "product-title": "Sneaky", "product-categorie": "1", "product-quantity": "1",
        "buying-price": "1", "saleing-price": "2", "product-photo": "", "add_product": "",
    })
    assert (out.status, out.location) == (302, "index.php")
    assert sql_value("SELECT COUNT(*) FROM products") == "0"


def test_anonymous_get_cannot_delete_a_product(admin):
    pid = add_product(admin)
    out = Client().do("DELETE", f"delete_product.php?id={pid}")
    assert (out.status, out.location) == (302, "index.php")
    assert sql_value("SELECT COUNT(*) FROM products") == "1"


# ------------------------------------------------------------------ role-based access
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("page", sorted(PAGE_LEVEL))
def test_access_by_role(role, page):
    allowed = ROLE_LEVEL[role] <= PAGE_LEVEL[page]
    c = logged_in(role)
    out = c.do("GET", page)
    if allowed:
        assert out.status == 200, f"{role} should open {page}"
    else:
        assert (out.status, out.location) == (302, "home.php"), f"{role} must be refused {page}"
        assert (out.flash_type, out.flash) == ("danger", "Sorry! you dont have permission to view the page.")
