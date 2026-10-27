<?php
 $errors = array();

 /*--------------------------------------------------------------*/
 /* Password hashing
 /* New passwords use password_hash() (salted, adaptive). Old
 /* accounts stored an unsalted SHA1 (40 hex characters): those are
 /* still accepted at login, to verify them only, and are replaced
 /* by a modern hash as soon as the user logs in successfully.
 /*--------------------------------------------------------------*/
function oswa_password_hash($plain){
  return password_hash($plain, PASSWORD_DEFAULT);
}
function oswa_password_is_legacy($stored){
  return is_string($stored) && preg_match('/^[0-9a-f]{40}$/', $stored) === 1;
}
function oswa_password_verify($plain, $stored){
  if(!is_string($stored) || $stored === ''){
    return false;
  }
  if(oswa_password_is_legacy($stored)){
    return hash_equals($stored, sha1($plain));
  }
  return password_verify($plain, $stored);
}
function oswa_password_needs_upgrade($stored){
  return oswa_password_is_legacy($stored) || password_needs_rehash($stored, PASSWORD_DEFAULT);
}
 /*--------------------------------------------------------------*/
 /* Password policy: returns an error message, or null when the
 /* password is acceptable.
 /*--------------------------------------------------------------*/
defined('OSWA_MIN_PASSWORD_LENGTH') || define('OSWA_MIN_PASSWORD_LENGTH', 8);
function oswa_password_policy_error($plain){
  $length = function_exists('mb_strlen') ? mb_strlen((string)$plain) : strlen((string)$plain);
  if($length < OSWA_MIN_PASSWORD_LENGTH){
    return 'Password must be at least '.OSWA_MIN_PASSWORD_LENGTH.' characters long.';
  }
  return null;
}

 /*--------------------------------------------------------------*/
 /* Function for Remove escapes special
 /* characters in a string for use in an SQL statement
 /*--------------------------------------------------------------*/
function real_escape($str){
  global $con;
  $escape = mysqli_real_escape_string($con,$str);
  return $escape;
}
/*--------------------------------------------------------------*/
/* Function for Remove html characters
/*--------------------------------------------------------------*/
function remove_junk($str){
  $str = nl2br($str);
  $str = htmlspecialchars(strip_tags($str, ENT_QUOTES));
  return $str;
}
/*--------------------------------------------------------------*/
/* Function for Uppercase first character
/*--------------------------------------------------------------*/
function first_character($str){
  $val = str_replace('-'," ",$str);
  $val = ucfirst($val);
  return $val;
}
/*--------------------------------------------------------------*/
/* Function for Checking input fields not empty
/*--------------------------------------------------------------*/
function validate_fields($var){
  global $errors;
  foreach ($var as $field) {
    $val = remove_junk($_POST[$field]);
    if(isset($val) && $val==''){
      $errors = $field ." can't be blank.";
      return $errors;
    }
  }
}
/*--------------------------------------------------------------*/
/* Function for Display Session Message
   Ex echo displayt_msg($message);
/*--------------------------------------------------------------*/
function display_msg($msg =''){
   $output = array();
   if(!empty($msg)) {
      foreach ($msg as $key => $value) {
         $output  = "<div class=\"alert alert-{$key}\">";
         $output .= "<a href=\"#\" class=\"close\" data-dismiss=\"alert\">&times;</a>";
         $output .= remove_junk(first_character($value));
         $output .= "</div>";
      }
      return $output;
   } else {
     return "" ;
   }
}
/*--------------------------------------------------------------*/
/* Function for redirect
/*--------------------------------------------------------------*/
function redirect($url, $permanent = false)
{
    if (headers_sent() === false)
    {
      header('Location: ' . $url, true, ($permanent === true) ? 301 : 302);
    }

    exit();
}
/*--------------------------------------------------------------*/
/* Function for find out total saleing price, buying price and profit
/*--------------------------------------------------------------*/
function total_price($totals){
   $sum = 0;
   $sub = 0;
   foreach($totals as $total ){
     $sum += $total['total_saleing_price'];
     $sub += $total['total_buying_price'];
     $profit = $sum - $sub;
   }
   return array($sum,$profit);
}
/*--------------------------------------------------------------*/
/* Function for Readable date time
/*--------------------------------------------------------------*/
function read_date($str){
     if($str)
      return date('F j, Y, g:i:s a', strtotime($str));
     else
      return null;
  }
/*--------------------------------------------------------------*/
/* Function for  Readable Make date time
/*--------------------------------------------------------------*/
function make_date(){
  return strftime("%Y-%m-%d %H:%M:%S", time());
}
/*--------------------------------------------------------------*/
/* Function for  Readable date time
/*--------------------------------------------------------------*/
function count_id(){
  static $count = 1;
  return $count++;
}
/*--------------------------------------------------------------*/
/* Function for Creting random string
/*--------------------------------------------------------------*/
function randString($length = 5)
{
  $str='';
  $cha = "0123456789abcdefghijklmnopqrstuvwxyz";

  for($x=0; $x<$length; $x++)
   $str .= $cha[mt_rand(0,strlen($cha))];
  return $str;
}


?>
