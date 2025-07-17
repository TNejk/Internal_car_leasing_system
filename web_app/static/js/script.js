
document.addEventListener('DOMContentLoaded', () => {
  function setFullHeight() {
    const el = document.querySelector('.full-height');
    if (el) {
      el.style.height = window.innerHeight + 'px';
    }
  }
  setFullHeight();
  window.addEventListener('resize', setFullHeight);

  let thm = localStorage.getItem('theme')

  if (thm === 'dark'){
    set_dark();
  }else if (thm === 'light'){
    set_light();
  }else {
    const darkThemeMq = window.matchMedia("(prefers-color-scheme: dark)");
    if (darkThemeMq.matches) {
      set_dark()
    } else {
      set_light()
    }
  }
});

function set_dark(){
  localStorage.setItem('theme', 'dark')
  localStorage.setItem('dlb', '/static/src/images/on-off-white.svg')
  document.documentElement.setAttribute('data-theme', localStorage.getItem('theme'));
  document.getElementById('toggle-btn').src = localStorage.getItem('dlb');
}

function set_light(){
  localStorage.setItem('theme', 'light');
  localStorage.setItem('dlb', '/static/src/images/on-off.svg')
  document.documentElement.setAttribute('data-theme', localStorage.getItem('theme'));
  document.getElementById('toggle-btn').src = localStorage.getItem('dlb');
}
function toggle() {
  if (localStorage.getItem('theme') === 'dark'){
    set_light();
  } else {
    set_dark();
  }
}
