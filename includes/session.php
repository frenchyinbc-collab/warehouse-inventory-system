<?php
 // Session cookie: not readable by scripts (HttpOnly), not sent on cross-site requests (SameSite),
 // and HTTPS-only when the site is served over HTTPS.
 $oswa_https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
            || (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https');
 session_set_cookie_params(array('lifetime' => 0, 'path' => '/', 'secure' => $oswa_https, 'httponly' => true, 'samesite' => 'Lax'));
 ini_set('session.use_strict_mode', '1');
 session_start();

class Session {

 public $msg;
 private $user_is_logged_in = false;

 function __construct(){
   $this->flash_msg();
   $this->userLoginSetup();
 }

  public function isUserLoggedIn(){
    return $this->user_is_logged_in;
  }
  public function login($user_id){
    session_regenerate_id(true); // a new id at login: a pre-login id cannot be reused (session fixation)
    $_SESSION['user_id'] = $user_id;
  }
  private function userLoginSetup()
  {
    if(isset($_SESSION['user_id']))
    {
      $this->user_is_logged_in = true;
    } else {
      $this->user_is_logged_in = false;
    }

  }
  public function logout(){
    unset($_SESSION['user_id']);
    session_regenerate_id(true);
  }

  public function msg($type ='', $msg =''){
    if(!empty($msg)){
       if(strlen(trim($type)) == 1){
         $type = str_replace( array('d', 'i', 'w','s'), array('danger', 'info', 'warning','success'), $type );
       }
       $_SESSION['msg'][$type] = $msg;
    } else {
      return $this->msg;
    }
  }

  private function flash_msg(){

    if(isset($_SESSION['msg'])) {
      $this->msg = $_SESSION['msg'];
      unset($_SESSION['msg']);
    } else {
      $this->msg;
    }
  }
}

$session = new Session();
$msg = $session->msg();

/*--------------------------------------------------------------*/
/* CSRF protection: every POST must carry the token that belongs to
/* the visitor's session (hidden field "csrf_token" or the header
/* X-CSRF-Token for ajax). Deletions are POST-only, so they are
/* protected too. A request from another site cannot know the token.
/*--------------------------------------------------------------*/
function csrf_token(){
  if(empty($_SESSION['csrf_token'])){
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
  }
  return $_SESSION['csrf_token'];
}
function csrf_field(){
  return '<input type="hidden" name="csrf_token" value="'.htmlspecialchars(csrf_token(), ENT_QUOTES).'">';
}
function csrf_request_is_valid(){
  $sent = isset($_POST['csrf_token']) ? $_POST['csrf_token'] : (isset($_SERVER['HTTP_X_CSRF_TOKEN']) ? $_SERVER['HTTP_X_CSRF_TOKEN'] : '');
  return is_string($sent) && !empty($_SESSION['csrf_token']) && hash_equals($_SESSION['csrf_token'], $sent);
}
function csrf_require_post(){
  if(isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] !== 'POST'){
    http_response_code(405);
    header('Allow: POST');
    exit('Method not allowed.');
  }
}
if(isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'POST' && !csrf_request_is_valid()){
  http_response_code(403);
  exit('Invalid or missing security token. Go back, reload the page and try again.');
}

?>
