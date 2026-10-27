<?php
require_once(LIB_PATH_INC.DS."config.php");

class MySqli_DB {

    private $con;
    public $query_id;
    private $affected = -1;

    function __construct() {
      $this->db_connect();
    }

/*--------------------------------------------------------------*/
/* Function for Open database connection
/*--------------------------------------------------------------*/
public function db_connect()
{
  // Report errors as return values (handled by fail(), which logs them) instead of uncaught exceptions.
  mysqli_report(MYSQLI_REPORT_OFF);
  $this->con = mysqli_connect(DB_HOST,DB_USER,DB_PASS);
  if(!$this->con)
         {
           die(" Database connection failed:". mysqli_connect_error());
         } else {
           $select_db = $this->con->select_db(DB_NAME);
             if(!$select_db)
             {
               die("Failed to Select Database". mysqli_connect_error());
             }
         }
}
/*--------------------------------------------------------------*/
/* Function for Close database connection
/*--------------------------------------------------------------*/

public function db_disconnect()
{
  if(isset($this->con))
  {
    mysqli_close($this->con);
    unset($this->con);
  }
}
/*--------------------------------------------------------------*/
/* Function for mysqli query
/*--------------------------------------------------------------*/
public function query($sql)
   {
      $this->affected = -1;
      if (trim($sql) != "") {
          $this->query_id = $this->con->query($sql);
      }
      if (!$this->query_id) {
          $this->fail($this->con->error);
      }
      return $this->query_id;
   }

/*--------------------------------------------------------------*/
/* Prepared statement: values are sent separately from the SQL text
/* (use ? placeholders). Returns a result set for SELECT, true for
/* INSERT/UPDATE/DELETE. $params are bound as integers when they are
/* PHP ints, otherwise as strings (same conversions MySQL applied to
/* the old quoted literals).
/*--------------------------------------------------------------*/
public function execute($sql, $params = array())
   {
      $stmt = $this->con->prepare($sql);
      if (!$stmt) {
          $this->fail($this->con->error);
      }
      if (!empty($params)) {
          $types = '';
          foreach ($params as $p) {
              $types .= is_int($p) ? 'i' : 's';
          }
          $stmt->bind_param($types, ...array_values($params));
      }
      if (!$stmt->execute()) {
          $this->fail($stmt->error);
      }
      $result = $stmt->get_result();
      $this->affected = $stmt->affected_rows;
      $stmt->close();
      $this->query_id = ($result === false) ? true : $result;
      return $this->query_id;
   }

/* Never show SQL or driver errors to the visitor: log them instead. */
private function fail($detail)
   {
      error_log('OSWA-INV database error: ' . $detail);
      if (PHP_SAPI !== 'cli' && !headers_sent()) {
          http_response_code(500);
      }
      die('A database error occurred.');
   }

/*--------------------------------------------------------------*/
/* Function for Query Helper
/*--------------------------------------------------------------*/
public function fetch_array($statement)
{
  return mysqli_fetch_array($statement);
}
public function fetch_object($statement)
{
  return mysqli_fetch_object($statement);
}
public function fetch_assoc($statement)
{
  return mysqli_fetch_assoc($statement);
}
public function num_rows($statement)
{
  return mysqli_num_rows($statement);
}
public function insert_id()
{
  return mysqli_insert_id($this->con);
}
public function affected_rows()
{
  return $this->affected >= 0 ? $this->affected : mysqli_affected_rows($this->con);
}
/*--------------------------------------------------------------*/
 /* Function for Remove escapes special
 /* characters in a string for use in an SQL statement
 /*--------------------------------------------------------------*/
 public function escape($str){
   return $this->con->real_escape_string($str);
 }
/*--------------------------------------------------------------*/
/* Function for while loop
/*--------------------------------------------------------------*/
public function while_loop($loop){
 global $db;
   $results = array();
   while ($result = $this->fetch_array($loop)) {
      $results[] = $result;
   }
 return $results;
}

}

$db = new MySqli_DB();

?>
