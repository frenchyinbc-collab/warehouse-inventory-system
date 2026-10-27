#!/usr/bin/env bash
# One-command install of OSWA-INV on a machine that already has PHP (with mysqli) and MySQL/MariaDB.
#
#   OSWA_DB_USER=oswa OSWA_DB_PASS='db password' \
#   OSWA_ADMIN_USER=admin OSWA_NEW_PASSWORD='admin password (8+ characters)' \
#   ./install.sh
#
# Optional: OSWA_DB_HOST (localhost), OSWA_DB_NAME (oswa_inv), MYSQL_CMD (default "mysql": a command
# that connects as a database administrator, used to create the database and the application user).
# The script refuses to touch a database that already contains the application's tables.
set -euo pipefail
cd "$(dirname "$0")"

die() { echo "install.sh: $*" >&2; exit 1; }

: "${OSWA_DB_USER:?set OSWA_DB_USER (the database account the application will use)}"
: "${OSWA_DB_PASS:?set OSWA_DB_PASS}"
: "${OSWA_NEW_PASSWORD:?set OSWA_NEW_PASSWORD (password of the first administrator, 8+ characters)}"
OSWA_ADMIN_USER="${OSWA_ADMIN_USER:-admin}"
OSWA_DB_HOST="${OSWA_DB_HOST:-localhost}"
OSWA_DB_NAME="${OSWA_DB_NAME:-oswa_inv}"
MYSQL_CMD="${MYSQL_CMD:-mysql}"
[ "${#OSWA_NEW_PASSWORD}" -ge 8 ] || die "OSWA_NEW_PASSWORD must be at least 8 characters"
[[ "$OSWA_DB_NAME" =~ ^[A-Za-z0-9_]+$ ]] || die "OSWA_DB_NAME may only contain letters, digits and _"
[[ "$OSWA_DB_USER" =~ ^[A-Za-z0-9_]+$ ]] || die "OSWA_DB_USER may only contain letters, digits and _"
[[ "$OSWA_DB_PASS" != *"'"* && "$OSWA_DB_PASS" != *"\\"* ]] || die "OSWA_DB_PASS must not contain ' or \\"

command -v php >/dev/null || die "php is not installed"
php -r 'exit(version_compare(PHP_VERSION, "8.0.0", ">=") && extension_loaded("mysqli") ? 0 : 1);' \
  || die "PHP 8.0+ with the mysqli extension is required"
$MYSQL_CMD -e 'SELECT 1' >/dev/null 2>&1 || die "cannot connect to the database server with: $MYSQL_CMD"

existing=$($MYSQL_CMD -N -B -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${OSWA_DB_NAME}' AND table_name IN ('users','products')")
[ "$existing" = "0" ] || die "database ${OSWA_DB_NAME} already contains OSWA-INV tables; refusing to overwrite"

# 1. database, application account, schema
$MYSQL_CMD -e "CREATE DATABASE IF NOT EXISTS \`${OSWA_DB_NAME}\`;
  CREATE USER IF NOT EXISTS '${OSWA_DB_USER}'@'${OSWA_DB_HOST}' IDENTIFIED BY '${OSWA_DB_PASS}';
  GRANT ALL ON \`${OSWA_DB_NAME}\`.* TO '${OSWA_DB_USER}'@'${OSWA_DB_HOST}'; FLUSH PRIVILEGES;"
$MYSQL_CMD "${OSWA_DB_NAME}" < oswa_inv.sql

# 2. first administrator (password taken from the environment, stored hashed)
export OSWA_DB_USER OSWA_DB_PASS OSWA_DB_HOST OSWA_DB_NAME OSWA_NEW_PASSWORD
php bin/create_user.php "$OSWA_ADMIN_USER" "Administrator" 1

# 3. upload folders: writable by the owner and the web server's group, not by everybody
chmod 775 uploads uploads/products uploads/users

echo "OK. Start the application with the same OSWA_DB_* variables, e.g.:"
echo "  OSWA_DB_USER=... OSWA_DB_PASS=... php -S 127.0.0.1:8080"
