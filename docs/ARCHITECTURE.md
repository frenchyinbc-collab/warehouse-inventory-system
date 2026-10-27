# Architecture

OSWA-INV is a classic "one PHP file per page" application (PHP 8, MySQL/MariaDB, Bootstrap 3).

```
index.php / login_v2.php   login forms            -> auth.php / auth_v2.php (POST)
home.php, product.php ...  one page per feature   (form handling + HTML in the same file)
delete_*.php               POST-only deletions
ajax.php                   product search / sale line (called by libs/js/functions.js)
bin/create_user.php        CLI: create a user (first admin)
install.sh                 one-command install
includes/load.php          loads, in order: config, functions, session, upload, database, sql
includes/config.php        database settings from environment variables (OSWA_DB_*)
includes/functions.php     helpers: password hashing and policy, flash messages, dates
includes/session.php       session cookie flags, login/logout, CSRF token + check on every POST
includes/database.php      MySqli_DB: query(), execute() (prepared statements), error handling
includes/sql.php           all queries (find_*, join_*, sales reports) and access-level checks
includes/upload.php        image upload (users, products)
layouts/                   header, footer and menus per role
uploads/                   product and user images
```

## Request flow
1. A page starts with `require_once('includes/load.php')`, then `page_require_level(N)`.
2. `session.php` starts the session (HttpOnly, SameSite=Lax cookie) and rejects any POST that does not carry the CSRF token.
3. The page reads `$_POST`, calls functions of `sql.php` or `$db->execute($sql, $params)`, stores a flash message in the session and redirects.
4. The next page shows and clears the flash message.

## Roles
Levels: 1 = admin, 2 = special, 3 = user. A page with level N is open to users whose level is <= N.
A deactivated group (`user_groups.group_status = 0`) blocks its users.

## Security rules for contributors
- Never put a value in SQL text: use `?` placeholders with `$db->execute()`. Table names go through the `tableExists()` allow-list.
- Every `<form method="post">` must contain `<?php echo csrf_field(); ?>`. Deletions are forms with a button, never links.
- Passwords: only `oswa_password_hash()` / `oswa_password_verify()`; minimum length checked by `oswa_password_policy_error()`.
- Configuration comes from the environment, never from the code.
