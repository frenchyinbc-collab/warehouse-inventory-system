# Modernization report

Starting point: `siamon123/warehouse-inventory-system` at commit 69fdd1c (PHP/MySQL, last real activity before 2022), kept untouched as the reference.
Method: a characterization test suite was written first against the **original** running application and a real MariaDB (no mocks). Tests are tagged:
- `keep` (134): behaviour that must not change. All pass on the original **and** on the modernised version.
- `change` (15): documents a weakness of the original. All 15 pass on the original and fail on the modernised version (the weakness is gone).
- `secure` (40): the same weaknesses expressed as requirements. They fail on the original and pass on the modernised version (or, for a few regression guards such as login SQL injection, pass on both).

## Before / after

| Criterion | Measure | Original | Modernised |
|---|---|---|---|
| Security | DB password in the code | yes (config.php) | no (environment variables) |
| | Default accounts | admin/admin, special/special, user/user | none; first admin created at install |
| | Password storage | unsalted SHA1 (identical passwords = identical hashes) | `password_hash` (bcrypt, salted); old SHA1 accounts upgraded at first login |
| | Minimum password length | none (1 character accepted) | 8 |
| | SQL queries built with text | ~95 call sites with manual escaping | 0: prepared statements (table names via allow-list) |
| | Database errors | SQL text in the error path | generic message, details in the server log |
| | CSRF | none; a link on another site could delete data | token on all 25 forms + ajax; deletions POST-only |
| | Session cookie | no HttpOnly / SameSite | HttpOnly, SameSite=Lax, Secure over HTTPS |
| | Session fixation | session id kept at login | new id at login and logout |
| Compatibility | PHP warnings/deprecations during the 134 `keep` tests (E_ALL) | 395 | 0 |
| | Crashes | product search "not found" -> HTTP 500 | works |
| | Deactivated user group | check could never trigger | enforced (redirect loop avoided) |
| Tests | Automated tests | 0 | 189 (134 keep, 15 change, 40 secure) |
| Deployment | Install | 6 manual steps, undocumented DB setup, uploads 777 | `./install.sh`, 0.4 s measured, uploads 775 |
| Maintainability | PHPStan level 5 / max findings (include-based code, many false positives) | 195 / 1091 | 159 / 1048 |
| | Documentation | README with default passwords | README, ARCHITECTURE.md, this report |

## Deliberate behaviour changes (everything else is identical)
- No default accounts; passwords of 8+ characters required (add user, edit user, change password).
- Deleting is done with a button (POST) instead of a link; all forms carry a token.
- Deactivated groups are now really blocked (the original check was dead code).

## A bug the tests missed (and how it was found)
The first run of the modernised app on a real PC showed an empty side menu. Prepared statements return integers where the pages compare with strings (`'1'`), so menus, Active/Deactive badges, pre-selected options and the sales report broke, while the first 122 `keep` tests still passed because none of them looked at what the pages display. Fix: results of prepared statements are converted to strings, as before. 12 display tests were added (they fail on the buggy version, pass on the fixed one and on the original). Lesson: behaviour tests must check what the user sees, and a real run by a human is part of the method.

## Known limits
- Logout is still a GET request (low impact).
- Passwords containing quotes or backslashes are hashed after the original's input escaping, to keep existing accounts working.
- PHPStan numbers are mostly noise caused by the include-based architecture, not a quality score.
- Not done: moving to a framework, front-end rewrite, rate limiting of logins.
