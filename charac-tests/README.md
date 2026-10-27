# Characterization tests for OSWA-INV (warehouse-inventory-system)

Black-box tests: they talk to the running app over HTTP and read the real MariaDB/MySQL database.
They never touch the PHP code. Baseline taken on the unmodified upstream copy
(commit 69fdd1c, PHP 8.3.6, MariaDB 10.11): **all 137 tests pass**, twice in a row.

## WARNING
Before every test the suite **drops and recreates the database** (`DB_NAME`, default `oswa_inv`)
and reloads `oswa_inv.sql`. Never point it at a database that holds real data.

## Run
    ./run_app.sh                  # starts MariaDB and `php -S 127.0.0.1:8080` (APP_DIR defaults to the baseline copy)
    python3 -m pytest             # all tests (needs: pip install pytest requests)
    python3 -m pytest -m keep     # behaviour that must not change
    python3 -m pytest -m change   # weaknesses expected to disappear after hardening

Settings (environment variables): BASE_URL, APP_DIR, SQL_FILE, DB_NAME, MYSQL_CMD,
ADMIN_USER/ADMIN_PASS, SPECIAL_USER/SPECIAL_PASS, USER_USER/USER_PASS (credentials of the three seeded accounts).

## Two categories
- `keep` (122): business behaviour. A failure after modernisation = regression.
  Known quirks (names end in `quirk`) are preserved on purpose; fixing one is a decision, taken later, with a note.
- `change` (15): documents a weakness or a crash (default accounts, unsalted SHA1, no CSRF protection,
  session cookie flags, session fixation, HTTP 500 in `ajax.php`, DB password in the code, 777 upload folders).
  Each is expected to start failing once the weakness is fixed; it is then replaced by its secure twin.

## Known quirks recorded (not fixed)
- Add sale ignores the date typed in the form (uses server time) and allows selling more than the stock (negative stock).
- Editing a sale subtracts the whole new quantity from stock again; deleting a sale does not restore stock.
- Re-saving a product with identical values reports "Sorry failed to updated!".
- A sales report for an empty period shows an empty report ($0.00); the "no sales found" branch is never reached.
- Usernames are not unique.

## Not covered yet
Media upload/delete, user groups, edit user / edit account / profile pages, edit/delete category, the AJAX
product auto-suggest happy path. Add them before modernising code that touches those areas.

## Note on intentional interface changes
Deletions are plain GET links today. If hardening turns them into POST + token, update the affected `keep`
tests in one place and record the decision; the business outcome (row gone, flash message) must stay the same.
