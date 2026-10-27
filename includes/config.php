<?php
/*
|--------------------------------------------------------------------------
| OWSA-INV V2
|--------------------------------------------------------------------------
| Author: Siamon Hasan
| Project Name: OSWA-INV
| Version: v2
| Offcial page: http://oswapp.com/
| facebook Page: https://www.facebook.com/oswapp
|
|
|
*/

/*
|--------------------------------------------------------------------------
| Database settings come from the environment, never from this file.
|--------------------------------------------------------------------------
|   OSWA_DB_USER   required
|   OSWA_DB_PASS   required
|   OSWA_DB_HOST   optional (default: localhost)
|   OSWA_DB_NAME   optional (default: oswa_inv)
| Set them in your web server, PHP-FPM pool or container configuration.
*/
function oswa_env($name, $default = null) {
  $value = getenv($name);
  if ($value === false && isset($_SERVER[$name])) {
    $value = $_SERVER[$name];
  }
  return ($value === false) ? $default : $value;
}

$oswa_db_user = oswa_env('OSWA_DB_USER');
$oswa_db_pass = oswa_env('OSWA_DB_PASS');

if ($oswa_db_user === null || $oswa_db_pass === null) {
  error_log('OSWA-INV: OSWA_DB_USER and OSWA_DB_PASS must be set in the environment.');
  if (PHP_SAPI !== 'cli') {
    http_response_code(500);
  }
  echo 'Configuration error: database credentials are not set.';
  exit(1);
}

define( 'DB_HOST', oswa_env('OSWA_DB_HOST', 'localhost') );  // Database host
define( 'DB_USER', $oswa_db_user );                          // Database user
define( 'DB_PASS', $oswa_db_pass );                          // Database password
define( 'DB_NAME', oswa_env('OSWA_DB_NAME', 'oswa_inv') );   // Database name

unset($oswa_db_user, $oswa_db_pass);
