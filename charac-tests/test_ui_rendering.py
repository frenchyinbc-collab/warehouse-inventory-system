"""What the pages actually show: menus, status badges, selected options, redirect by role.

Added after a real run on a developer's PC showed an empty side menu that the other tests did not notice
(prepared statements returned integers where the pages compare with strings). Must behave the same on the
original and on the modernised code.
"""
import re

import pytest

from conftest import CREDS, Client, add_product, logged_in, sql_value

pytestmark = pytest.mark.keep


def test_admin_sees_the_admin_menu(admin):
    page = admin.get("home.php").text
    for label in ("Dashboard", "User Management", "Manage Users", "Manage Groups"):
        assert label in page, label


def test_special_user_sees_the_special_menu(special):
    page = special.get("home.php").text
    for label in ("Dashboard", "Categorie", "Product", "Media"):
        assert f"<span>{label}</span>" in page, label
    assert "User Management" not in page


def test_plain_user_sees_the_user_menu(user):
    page = user.get("home.php").text
    for label in ("Dashboard", "Sales", "Sales Report"):
        assert f"<span>{label}</span>" in page, label
    assert "User Management" not in page


def test_users_page_marks_active_accounts(admin):
    page = admin.get("users.php").text
    assert page.count('label label-success') == 3
    assert "label-danger" not in page


def test_group_page_marks_active_groups(admin):
    page = admin.get("group.php").text
    assert page.count('label label-success') == 3


def test_a_deactivated_user_is_marked_as_deactive(admin):
    from conftest import sql
    sql("UPDATE users SET status=0 WHERE username='user'")
    page = admin.get("users.php").text
    assert page.count('label label-success') == 2
    assert page.count('label label-danger') == 1


def test_product_without_a_picture_shows_the_placeholder(admin):
    add_product(admin)
    page = admin.get("product.php").text
    assert "uploads/products/no_image.jpg" in page


def test_edit_user_preselects_the_current_status_and_role(admin):
    uid = sql_value("SELECT id FROM users WHERE username='special'")
    page = admin.get(f"edit_user.php?id={uid}").text
    assert re.search(r'selected="selected"\s*value="1">Active', page)
    assert re.search(r'<option selected="selected" value="2">Special</option>', page)


def test_edit_group_preselects_the_current_status(admin):
    gid = sql_value("SELECT id FROM user_groups WHERE group_level=2")
    page = admin.get(f"edit_group.php?id={gid}").text
    assert re.search(r'selected="selected"\s*value="1">\s*Active', page)


@pytest.mark.parametrize("role,target", [("admin", "admin.php"), ("special", "special.php"), ("user", "home.php")])
def test_second_login_form_redirects_by_role(role, target):
    c = Client()
    r = c.post("auth_v2.php", {"username": CREDS[role][0], "password": CREDS[role][1]})
    assert (r.status_code, r.headers.get("Location")) == (302, target)
