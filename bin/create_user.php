<?php
/*
 * Create a user from the command line (used to create the first admin).
 *
 *   OSWA_NEW_PASSWORD='a long password' php bin/create_user.php <username> <full name> <level>
 *
 * level: 1 = admin, 2 = special, 3 = user.
 * The password is read from the environment (never from the command line, which
 * would leave it in the shell history and process list). Minimum 8 characters.
 * Database settings come from OSWA_DB_* like the web application.
 */
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit(1);
}
require_once(__DIR__ . '/../includes/config.php');
require_once(__DIR__ . '/../includes/functions.php');

function fail($message) {
    fwrite(STDERR, "Error: {$message}\n");
    exit(1);
}

if ($argc !== 4) {
    fail("usage: OSWA_NEW_PASSWORD=... php bin/create_user.php <username> <full name> <level 1|2|3>");
}
list(, $username, $name, $level) = $argv;
$password = getenv('OSWA_NEW_PASSWORD');

if ($username === '' || $name === '') {
    fail('username and full name must not be empty.');
}
if (!in_array($level, array('1', '2', '3'), true)) {
    fail('level must be 1 (admin), 2 (special) or 3 (user).');
}
if ($password === false) {
    fail('set the password in the OSWA_NEW_PASSWORD environment variable.');
}
$policy_error = oswa_password_policy_error($password);
if ($policy_error !== null) {
    fail($policy_error);
}

mysqli_report(MYSQLI_REPORT_OFF);
$con = mysqli_connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
if (!$con) {
    fail('cannot connect to the database: ' . mysqli_connect_error());
}

$stmt = mysqli_prepare($con, 'SELECT id FROM users WHERE username = ?');
mysqli_stmt_bind_param($stmt, 's', $username);
mysqli_stmt_execute($stmt);
mysqli_stmt_store_result($stmt);
if (mysqli_stmt_num_rows($stmt) > 0) {
    fail("user '{$username}' already exists.");
}
mysqli_stmt_close($stmt);

$hash = oswa_password_hash($password);
$lvl = (int)$level;
$stmt = mysqli_prepare($con, "INSERT INTO users (name, username, password, user_level, status) VALUES (?, ?, ?, ?, '1')");
mysqli_stmt_bind_param($stmt, 'sssi', $name, $username, $hash, $lvl);
if (!mysqli_stmt_execute($stmt)) {
    fail('could not create the user: ' . mysqli_stmt_error($stmt));
}
echo "User '{$username}' created (level {$lvl}).\n";
