# OSWA-INV: warehouse inventory system

Web application to track products, categories, stock, sales and sales reports, with three roles (admin, special, user).
Original project by Siamon Hasan (MIT). This branch is a modernised version: see [MODERNIZATION.md](MODERNIZATION.md) for what changed and how it was measured, and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the code is organised.

## Requirements
PHP 8.0+ with `mysqli`, MySQL or MariaDB.

## Install (one command)
```
OSWA_DB_USER=oswa OSWA_DB_PASS='a database password' \
OSWA_ADMIN_USER=admin OSWA_NEW_PASSWORD='a password of 8+ characters' \
./install.sh
```
It creates the database and the application's database account, loads the schema, creates the first administrator (password stored hashed) and sets the upload folders to 775. There are no default accounts.

Optional variables: `OSWA_DB_HOST` (default `localhost`), `OSWA_DB_NAME` (default `oswa_inv`), `MYSQL_CMD` (default `mysql`, the command that connects as a database administrator).

## Run
The application reads its database settings from the environment of the web server / PHP process:
```
OSWA_DB_USER=oswa OSWA_DB_PASS='a database password' php -S 127.0.0.1:8080
```
Without `OSWA_DB_USER` and `OSWA_DB_PASS` it stops with a clear "Configuration error". Behind a real web server, set the same variables in its PHP configuration. Serve it over HTTPS (the session cookie is then marked Secure automatically).

## Users
Add users from the "Add user" page (admin) or from the command line:
```
OSWA_NEW_PASSWORD='long password' php bin/create_user.php <username> "<full name>" <1|2|3>
```
Levels: 1 = admin, 2 = special, 3 = user. Passwords must have at least 8 characters.

## Tests
A black-box test suite (pytest, real HTTP requests against the running application and a real database) is provided separately in `charac-tests/`; see its README.

## Manual install (without install.sh)
1. Create the database and load `oswa_inv.sql`.
2. Set the `OSWA_DB_*` variables as above.
3. `chmod 775 uploads uploads/*`.
4. Create the first admin with `bin/create_user.php`.

License: MIT.
