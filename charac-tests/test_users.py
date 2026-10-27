"""User management and password change. Everything here must NOT change.

(The way passwords are stored is a different matter: see test_hardening_targets.py.)
"""
import pytest

from conftest import Client, add_user, logged_in, sql, sql_value

pytestmark = pytest.mark.keep

NEW_USERNAME = "newperson"
NEW_PASSWORD = "Secret-123"


def test_admin_creates_a_user(admin):
    out = add_user(admin, name="New Person", username=NEW_USERNAME, password=NEW_PASSWORD, level="3")
    assert (out.status, out.location) == (302, "add_user.php")
    assert (out.flash_type, out.flash) == ("success", "User account has been creted!")  # sic
    name, username, level, status = sql(
        f"SELECT name, username, user_level, status FROM users WHERE username='{NEW_USERNAME}'")[0]
    assert (name, username, level, status) == ("New Person", NEW_USERNAME, "3", "1")


def test_a_newly_created_user_can_log_in(admin):
    add_user(admin, username=NEW_USERNAME, password=NEW_PASSWORD)
    c = Client()
    out = c.outcome(c.login_as(NEW_USERNAME, NEW_PASSWORD))
    assert (out.status, out.location) == (302, "home.php")
    assert out.flash == "Welcome to OSWA INV."


def test_a_newly_created_user_gets_the_requested_access_level(admin):
    add_user(admin, username="level2person", password=NEW_PASSWORD, level="2")
    c = Client()
    assert c.login_as("level2person", NEW_PASSWORD).status_code == 302
    assert c.get("product.php").status_code == 200       # level 2 page: allowed
    assert c.get("users.php").status_code == 302         # level 1 page: refused


def test_new_user_wrong_password_is_rejected(admin):
    add_user(admin, username=NEW_USERNAME, password=NEW_PASSWORD)
    c = Client()
    out = c.outcome(c.login_as(NEW_USERNAME, NEW_PASSWORD + "x"))
    assert (out.status, out.location) == (302, "index.php")


@pytest.mark.parametrize("field,label", [
    ("full-name", "Full name"), ("username", "Username"), ("password", "Password"), ("level", "Level"),
])
def test_add_user_refuses_a_blank_field(admin, field, label):
    data = {"full-name": "New Person", "username": NEW_USERNAME, "password": NEW_PASSWORD,
            "level": "3", "add_user": ""}
    data[field] = ""
    out = admin.do("POST", "add_user.php", data)
    assert (out.status, out.location) == (302, "add_user.php")
    assert (out.flash_type, out.flash) == ("danger", f"{label} can't be blank.")
    assert sql_value(f"SELECT COUNT(*) FROM users WHERE username='{NEW_USERNAME}'") == "0"


def test_duplicate_usernames_are_accepted_quirk(admin):
    """Quirk: the database does not enforce unique usernames."""
    add_user(admin, username="twin", password="One-1111")
    out = add_user(admin, username="twin", password="Two-2222")
    assert out.flash == "User account has been creted!"
    assert sql_value("SELECT COUNT(*) FROM users WHERE username='twin'") == "2"


def test_only_admins_can_create_users(special):
    out = add_user(special, username=NEW_USERNAME, password=NEW_PASSWORD)
    assert (out.status, out.location) == (302, "home.php")
    assert sql_value(f"SELECT COUNT(*) FROM users WHERE username='{NEW_USERNAME}'") == "0"


def test_user_list_shows_the_accounts(admin):
    add_user(admin, name="Zed Zebra", username="zed", password=NEW_PASSWORD)
    r = admin.get("users.php")
    assert r.status_code == 200
    # the page shows name and username with ucwords(), so the username "zed" appears as "Zed"
    for expected in ("<td>Zed Zebra</td>", "<td>Zed</td>", "<td>Special User</td>"):
        assert expected in r.text


# ------------------------------------------------------------------ change password (as the new user)
def _new_user_client(admin):
    add_user(admin, username=NEW_USERNAME, password=NEW_PASSWORD)
    uid = sql_value(f"SELECT id FROM users WHERE username='{NEW_USERNAME}'")
    c = Client()
    assert c.login_as(NEW_USERNAME, NEW_PASSWORD).status_code == 302
    return c, uid


def test_change_password_then_old_password_stops_working(admin):
    c, uid = _new_user_client(admin)
    out = c.do("POST", "change_password.php", {
        "old-password": NEW_PASSWORD, "new-password": "Brand-New-456", "id": uid, "update": "",
    })
    assert (out.status, out.location) == (302, "index.php")
    assert (out.flash_type, out.flash) == ("success", "Login with your new password.")
    # the session is closed after the change
    assert c.get("home.php").headers.get("Location") == "index.php"
    fresh = Client()
    assert fresh.login_as(NEW_USERNAME, NEW_PASSWORD).headers.get("Location") == "index.php"
    assert fresh.login_as(NEW_USERNAME, "Brand-New-456").headers.get("Location") == "home.php"


def test_change_password_refuses_a_wrong_old_password(admin):
    c, uid = _new_user_client(admin)
    out = c.do("POST", "change_password.php", {
        "old-password": "not-the-password", "new-password": "Brand-New-456", "id": uid, "update": "",
    })
    assert (out.status, out.location) == (302, "change_password.php")
    assert (out.flash_type, out.flash) == ("danger", "Your old password not match")
    assert Client().login_as(NEW_USERNAME, NEW_PASSWORD).headers.get("Location") == "home.php"


def test_change_password_refuses_a_blank_new_password(admin):
    c, uid = _new_user_client(admin)
    out = c.do("POST", "change_password.php", {
        "old-password": NEW_PASSWORD, "new-password": "", "id": uid, "update": "",
    })
    assert (out.status, out.location) == (302, "change_password.php")
    assert out.flash == "New password can't be blank."


# ------------------------------------------------------------------ delete user
def test_admin_deletes_a_user_who_then_cannot_log_in(admin):
    add_user(admin, username=NEW_USERNAME, password=NEW_PASSWORD)
    uid = sql_value(f"SELECT id FROM users WHERE username='{NEW_USERNAME}'")
    out = admin.do("DELETE", f"delete_user.php?id={uid}")
    assert (out.status, out.location) == (302, "users.php")
    assert (out.flash_type, out.flash) == ("success", "User deleted.")
    assert sql_value(f"SELECT COUNT(*) FROM users WHERE username='{NEW_USERNAME}'") == "0"
    assert Client().login_as(NEW_USERNAME, NEW_PASSWORD).headers.get("Location") == "index.php"


def test_deleting_a_missing_user_reports_failure(admin):
    out = admin.do("DELETE", "delete_user.php?id=999")
    assert (out.status, out.location) == (302, "users.php")
    assert (out.flash_type, out.flash) == ("danger", "User deletion failed Or Missing Prm.")


def test_only_admins_can_delete_users(special):
    uid = sql_value("SELECT id FROM users ORDER BY id LIMIT 1")
    out = special.do("DELETE", f"delete_user.php?id={uid}")
    assert (out.status, out.location) == (302, "home.php")
    assert sql_value("SELECT COUNT(*) FROM users") == "3"
