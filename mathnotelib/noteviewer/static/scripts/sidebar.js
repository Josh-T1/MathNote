export function setupSidebar(){
  const sidebar = document.getElementById('sidebar');
  const openBtn = document.getElementById('toggle-button');
  const closeBtn = document.getElementById('sidebar-toggle-button');

  openBtn.addEventListener('click', () => {
    sidebar.classList.add('open');
    openBtn.style.display = 'none';
  });

  closeBtn.addEventListener('click', () => {
    sidebar.classList.remove('open');
    openBtn.style.display = 'block';
  });

}

