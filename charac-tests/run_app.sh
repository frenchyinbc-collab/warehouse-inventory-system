#!/usr/bin/env bash
# Starts MariaDB and the PHP built-in server for the app under test.
# Does not modify the application's files.
# Usage: ./run_app.sh [APP_DIR] [PORT]
set -u
APP_DIR="${1:-/root/baseline/warehouse-inventory-system}"
PORT="${2:-8080}"

if ! mysql -N -e 'select 1' >/dev/null 2>&1; then
  (mysqld_safe >/tmp/mysqld.log 2>&1 &)
  for _ in $(seq 1 30); do
    mysql -N -e 'select 1' >/dev/null 2>&1 && break
    sleep 1
  done
fi
mysql -N -e 'select 1' >/dev/null 2>&1 || { echo "MariaDB did not start"; exit 1; }

# DB + user expected by includes/config.php (the README does not document this step)
# Local test account for the database. The app under test receives the same values through
# OSWA_DB_USER / OSWA_DB_PASS (the original code ignores them and uses its own hard-coded ones).
export OSWA_DB_USER="${OSWA_DB_USER:-admin}"
export OSWA_DB_PASS="${OSWA_DB_PASS:-root}"
mysql -e "CREATE DATABASE IF NOT EXISTS oswa_inv;
          CREATE USER IF NOT EXISTS '${OSWA_DB_USER}'@'localhost' IDENTIFIED BY '${OSWA_DB_PASS}';
          GRANT ALL ON oswa_inv.* TO '${OSWA_DB_USER}'@'localhost'; FLUSH PRIVILEGES;"

if ! curl -s -o /dev/null "http://127.0.0.1:${PORT}/"; then
  # one log file per port, so two copies of the app can be compared side by side
  (cd "$APP_DIR" && nohup php -S "127.0.0.1:${PORT}" >"${LOG_FILE:-/tmp/php-server-${PORT}.log}" 2>&1 &)
  for _ in $(seq 1 20); do
    curl -s -o /dev/null "http://127.0.0.1:${PORT}/" && break
    sleep 0.5
  done
fi
curl -s -o /dev/null -w "app: HTTP %{http_code} on port ${PORT}\n" "http://127.0.0.1:${PORT}/"
