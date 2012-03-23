$(document).ready(function() {

  $('.fade-input').each(function() {
    var $label = $(this).children('.fade-label'),
        $field = $(this).find('.input input');
    $label.disableSelection();
    $label.click(function() {
      $field.focus();
    });
    $field.focus(function() {
      $label.fadeOut('fast');
    });
    $field.blur(function() {
      if($field.val().length === 0) {
        $label.fadeIn('fast');
      }
    });
  });	

});