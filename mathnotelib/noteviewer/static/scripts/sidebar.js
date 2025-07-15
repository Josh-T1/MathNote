function getSelectedFile(){
  var selected = "None";
  for (const file of document.querySelectorAll('.file-row')) {
    if (file.classList.contains('highlight')) {
      selected = file; 
    }
  }
}

export function setupSidebar(){
  const sidebar = document.getElementById('sidebar');
  const openBtn = document.getElementById('toggle-button');
  const closeBtn = document.getElementById('sidebar-toggle-button');
  const newNoteBtn = document.getElementById("new-note-button")
  const newDirBtn = document.getElementById("new-dir-button")

  openBtn.addEventListener('click', () => {
    sidebar.classList.add('open');
    openBtn.style.display = 'none';
  });

  closeBtn.addEventListener('click', () => {
    sidebar.classList.remove('open');
    openBtn.style.display = 'block';
  });
  
  newNoteBtn.addEventListener('click', () => {
    console.log("click on new note")
  });
  
  newDirBtn.addEventListener('click', () => {
    console.log("click on new dir")
  });
}

