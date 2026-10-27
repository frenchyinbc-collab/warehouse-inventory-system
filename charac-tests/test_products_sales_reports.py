"""Categories, products, sales and reports. Everything here must NOT change.

Some tests record behaviour that looks like a bug (marked 'quirk' in the name). They are kept on purpose:
the modernisation must not change business behaviour silently. Fixing one is a decision, taken later,
and the test is then updated together with a note.
"""
import re
from datetime import datetime, timedelta, timezone

import pytest

from conftest import add_category, add_product, add_sale, logged_in, sql, sql_value

pytestmark = pytest.mark.keep


def today():
    return datetime.now(timezone.utc).date()


def ymd(d):
    return d.strftime("%Y-%m-%d")


def num(value):
    return float(value)


# ------------------------------------------------------------------ categories (admin)
def test_admin_adds_a_category(admin):
    out = admin.do("POST", "categorie.php", {"categorie-name": "Tools", "add_cat": ""})
    assert (out.status, out.location) == (302, "categorie.php")
    assert (out.flash_type, out.flash) == ("success", "Successfully Added Categorie")
    assert sql("SELECT name FROM categories") == [["Tools"]]


def test_blank_category_name_is_refused(admin):
    out = admin.do("POST", "categorie.php", {"categorie-name": "", "add_cat": ""})
    assert (out.status, out.location) == (302, "categorie.php")
    assert (out.flash_type, out.flash) == ("danger", "Categorie name can't be blank.")
    assert sql_value("SELECT COUNT(*) FROM categories") == "0"


def test_category_page_lists_categories(admin):
    add_category(admin, "Garden")
    r = admin.get("categorie.php")
    assert r.status_code == 200 and "Garden" in r.text


# ------------------------------------------------------------------ products (special level)
def test_add_product(special, admin):
    cat = add_category(admin, "Tools")
    out = special.do("POST", "add_product.php", {
        "product-title": "Hammer", "product-categorie": str(cat), "product-quantity": "10",
        "buying-price": "5", "saleing-price": "9", "product-photo": "", "add_product": "",
    })
    assert (out.status, out.location) == (302, "add_product.php")
    assert (out.flash_type, out.flash) == ("success", "Product added")
    row = sql("SELECT name, quantity, buy_price, sale_price, categorie_id, media_id FROM products")
    assert len(row) == 1
    name, qty, buy, sale, cat_id, media = row[0]
    assert (name, num(qty), num(buy), num(sale), cat_id, media) == ("Hammer", 10, 5, 9, str(cat), "0")
    assert sql_value("SELECT date FROM products") not in (None, "NULL", "")


@pytest.mark.parametrize("field,blank_label", [
    ("product-title", "Product title"),
    ("product-categorie", "Product categorie"),
    ("product-quantity", "Product quantity"),
    ("buying-price", "Buying price"),
    ("saleing-price", "Saleing price"),
])
def test_add_product_refuses_a_blank_required_field(special, admin, field, blank_label):
    cat = add_category(admin)
    data = {
        "product-title": "Hammer", "product-categorie": str(cat), "product-quantity": "10",
        "buying-price": "5", "saleing-price": "9", "product-photo": "", "add_product": "",
    }
    data[field] = ""
    out = special.do("POST", "add_product.php", data)
    assert (out.status, out.location) == (302, "add_product.php")
    assert (out.flash_type, out.flash) == ("danger", f"{blank_label} can't be blank.")
    assert sql_value("SELECT COUNT(*) FROM products") == "0"


def test_product_list_shows_name_category_and_prices(special, admin):
    cat = add_category(admin, "Tools")
    add_product(special, "Hammer", cat, qty="10", buy="5", sale="9")
    r = special.get("product.php")
    assert r.status_code == 200
    for expected in ("Hammer", "Tools"):
        assert expected in r.text
    assert re.search(r">\s*10\s*<", r.text)  # stock


def test_edit_product(special, admin):
    cat = add_category(admin)
    pid = add_product(special, "Hammer", cat)
    out = special.do("POST", f"edit_product.php?id={pid}", {
        "product-title": "Hammer XL", "product-categorie": str(cat), "product-quantity": "12",
        "buying-price": "6", "saleing-price": "10", "product-photo": "", "product": "",
    })
    assert (out.status, out.location) == (302, "product.php")
    assert (out.flash_type, out.flash) == ("success", "Product updated")
    name, qty, buy, sale = sql(f"SELECT name, quantity, buy_price, sale_price FROM products WHERE id={pid}")[0]
    assert (name, num(qty), num(buy), num(sale)) == ("Hammer XL", 12, 6, 10)


def test_edit_product_with_unchanged_values_reports_failure_quirk(special, admin):
    """Quirk: the app treats 'no row changed' as failure, so re-saving identical values shows an error."""
    cat = add_category(admin)
    pid = add_product(special, "Hammer", cat, qty="10", buy="5", sale="9")
    out = special.do("POST", f"edit_product.php?id={pid}", {
        "product-title": "Hammer", "product-categorie": str(cat), "product-quantity": "10",
        "buying-price": "5", "saleing-price": "9", "product-photo": "", "product": "",
    })
    assert (out.status, out.location) == (302, f"edit_product.php?id={pid}")
    assert (out.flash_type, out.flash) == ("danger", "Sorry failed to updated!")


def test_edit_product_refuses_a_blank_title(special, admin):
    cat = add_category(admin)
    pid = add_product(special, "Hammer", cat)
    out = special.do("POST", f"edit_product.php?id={pid}", {
        "product-title": "", "product-categorie": str(cat), "product-quantity": "10",
        "buying-price": "5", "saleing-price": "9", "product-photo": "", "product": "",
    })
    assert (out.status, out.location) == (302, f"edit_product.php?id={pid}")
    assert out.flash == "Product title can't be blank."
    assert sql_value(f"SELECT name FROM products WHERE id={pid}") == "Hammer"


def test_edit_missing_product_redirects_to_the_list(special):
    out = special.do("GET", "edit_product.php?id=999")
    assert (out.status, out.location) == (302, "product.php")
    assert (out.flash_type, out.flash) == ("danger", "Missing product id.")


def test_delete_product(special, admin):
    pid = add_product(special, category_id=add_category(admin))  # categories can only be created by an admin
    out = special.do("DELETE", f"delete_product.php?id={pid}")
    assert (out.status, out.location) == (302, "product.php")
    assert (out.flash_type, out.flash) == ("success", "Products deleted.")
    assert sql_value("SELECT COUNT(*) FROM products") == "0"


def test_delete_missing_product(special):
    out = special.do("DELETE", "delete_product.php?id=999")
    assert (out.status, out.location) == (302, "product.php")
    assert (out.flash_type, out.flash) == ("danger", "Missing Product id.")


def test_plain_user_cannot_add_or_delete_products(user, admin):
    pid = add_product(admin)
    out = user.do("POST", "add_product.php", {
        "product-title": "Nope", "product-categorie": "1", "product-quantity": "1",
        "buying-price": "1", "saleing-price": "2", "product-photo": "", "add_product": "",
    })
    assert (out.status, out.location) == (302, "home.php")
    out = user.do("DELETE", f"delete_product.php?id={pid}")
    assert (out.status, out.location) == (302, "home.php")
    assert sql_value("SELECT COUNT(*) FROM products") == "1"


# ------------------------------------------------------------------ sales (plain user level)
@pytest.fixture
def stocked(admin):
    """One product, 10 in stock, bought at 5 and sold at 9."""
    return add_product(admin, "Hammer", qty="10", buy="5", sale="9")


def test_add_sale_records_it_and_lowers_stock(user, stocked):
    out = add_sale(user, stocked, qty="2", price="9", total="18", date="2000-01-01")
    assert (out.status, out.location) == (302, "add_sale.php")
    assert (out.flash_type, out.flash) == ("success", "Sale added.")
    pid, qty, price, date = sql("SELECT product_id, qty, price, date FROM sales")[0]
    assert (pid, num(qty), num(price)) == (str(stocked), 2, 18)
    assert sql_value(f"SELECT quantity FROM products WHERE id={stocked}") == "8"
    # quirk: the date typed in the form is ignored, the sale gets the server's current time
    assert not date.startswith("2000-01-01")
    assert date.startswith(str(today().year))


def test_add_sale_refuses_a_blank_quantity(user, stocked):
    out = add_sale(user, stocked, qty="")
    assert (out.status, out.location) == (302, "add_sale.php")
    assert (out.flash_type, out.flash) == ("danger", "Quantity can't be blank.")
    assert sql_value("SELECT COUNT(*) FROM sales") == "0"
    assert sql_value(f"SELECT quantity FROM products WHERE id={stocked}") == "10"


def test_selling_more_than_the_stock_is_accepted_quirk(user, stocked):
    """Quirk: no stock check, so stock can go negative."""
    out = add_sale(user, stocked, qty="15", price="9", total="135")
    assert (out.flash_type, out.flash) == ("success", "Sale added.")
    assert sql_value(f"SELECT quantity FROM products WHERE id={stocked}") == "-5"


def test_sales_list_shows_the_sale(user, stocked):
    add_sale(user, stocked, qty="2", total="18")
    r = user.get("sales.php")
    assert r.status_code == 200
    assert "Hammer" in r.text and re.search(r">\s*18(\.00)?\s*<", r.text)


def test_edit_sale(user, stocked):
    add_sale(user, stocked, qty="2", total="18")
    sid = sql_value("SELECT id FROM sales")
    out = user.do("POST", f"edit_sale.php?id={sid}", {
        "title": "Hammer", "quantity": "3", "price": "9", "total": "27",
        "date": "2024-05-01", "update_sale": "",
    })
    assert (out.status, out.location) == (302, f"edit_sale.php?id={sid}")
    assert (out.flash_type, out.flash) == ("success", "Sale updated.")
    qty, price, date = sql(f"SELECT qty, price, date FROM sales WHERE id={sid}")[0]
    assert (num(qty), num(price)) == (3, 27)
    assert date.startswith("2024-05-01")
    # quirk: editing subtracts the whole new quantity from stock again (10 - 2 - 3), not just the difference
    assert sql_value(f"SELECT quantity FROM products WHERE id={stocked}") == "5"


def test_edit_missing_sale_redirects_to_the_list(user):
    out = user.do("GET", "edit_sale.php?id=999")
    assert (out.status, out.location) == (302, "sales.php")
    assert out.flash == "Missing product id."  # sic: the original message says "product"


def test_delete_sale_does_not_restore_stock_quirk(user, stocked):
    add_sale(user, stocked, qty="2", total="18")
    sid = sql_value("SELECT id FROM sales")
    out = user.do("DELETE", f"delete_sale.php?id={sid}")
    assert (out.status, out.location) == (302, "sales.php")
    assert (out.flash_type, out.flash) == ("success", "Sale deleted.")
    assert sql_value("SELECT COUNT(*) FROM sales") == "0"
    assert sql_value(f"SELECT quantity FROM products WHERE id={stocked}") == "8"


def test_delete_missing_sale(user):
    out = user.do("DELETE", "delete_sale.php?id=999")
    assert (out.status, out.location) == (302, "sales.php")
    assert (out.flash_type, out.flash) == ("danger", "Missing sale id.")


# ------------------------------------------------------------------ reports (plain user level)
def test_sales_report_form_page_opens(user):
    r = user.get("sales_report.php")
    assert r.status_code == 200 and "start-date" in r.text and "end-date" in r.text


def test_sales_report_by_dates_totals(user, stocked):
    add_sale(user, stocked, qty="2", price="9", total="18")
    r = user.post("sale_report_process.php", {
        "start-date": ymd(today() - timedelta(days=1)),
        "end-date": ymd(today() + timedelta(days=1)),
        "submit": "",
    })
    assert r.status_code == 200
    assert "Sales Report" in r.text and "Hammer" in r.text
    # total = 2 x selling price 9; profit = 18 - (2 x buying price 5)
    assert re.search(r"Grand Total</td>\s*<td>\s*\$\s*18\.00", r.text)
    assert re.search(r"Profit</td>\s*<td>\s*\$\s*8\.00", r.text)


def test_sales_report_with_no_sales_in_range_shows_an_empty_report_quirk(user, stocked):
    """Quirk: the code has a 'Sorry no sales has been found' branch, but it is never reached
    (the query result object is always truthy), so an empty period gives an empty report with $0.00."""
    add_sale(user, stocked)
    r = user.post("sale_report_process.php", {
        "start-date": "2000-01-01", "end-date": "2000-01-31", "submit": "",
    })
    assert r.status_code == 200
    assert "Sales Report" in r.text and "2000-01-01 To 2000-01-31" in r.text
    assert "Hammer" not in r.text
    assert re.search(r"Grand Total</td>\s*<td>\s*\$\s*0\.00", r.text)
    assert re.search(r"Profit</td>\s*<td>\s*\$\s*0\.00", r.text)


def test_sales_report_refuses_a_blank_date(user):
    out = user.do("POST", "sale_report_process.php", {"start-date": "", "end-date": "2000-01-31", "submit": ""})
    assert (out.status, out.location) == (302, "sales_report.php")
    assert out.flash == "Start date can't be blank."


def test_sales_report_without_form_data_redirects(user):
    out = user.do("GET", "sale_report_process.php")
    assert (out.status, out.location) == (302, "sales_report.php")
    assert (out.flash_type, out.flash) == ("danger", "Select dates")


@pytest.mark.parametrize("page", ["daily_sales.php", "monthly_sales.php"])
def test_daily_and_monthly_sales_pages_show_todays_sale(user, stocked, page):
    add_sale(user, stocked, qty="2", price="9", total="18")
    r = user.get(page)
    assert r.status_code == 200
    assert "Hammer" in r.text and "18" in r.text


@pytest.mark.parametrize("page", ["daily_sales.php", "monthly_sales.php"])
def test_daily_and_monthly_sales_pages_open_with_no_sales(user, page):
    assert user.get(page).status_code == 200
