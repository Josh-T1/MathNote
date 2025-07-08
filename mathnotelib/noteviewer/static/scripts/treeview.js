function createNavTree(data, parentTag, depth=0){

    const li = document.createElement('li');
    const div = document.createElement('div');
    const ul = document.createElement('ul');
    
    const spanIndent = document.createElement("span");
    const spanContent = document.createElement("span");

    div.classList.add("dir-row");
    div.setAttribute("data-path", data.path);
    spanIndent.classList.add("indent");
    spanIndent.style.setProperty("--level", depth + 1);
    spanContent.classList.add("caret");
    spanContent.textContent = data.name;
    spanContent.classList.add("content");

    div.appendChild(spanIndent);
    div.appendChild(spanContent);

    ul.classList.add('nested');
    ul.style.setProperty('--level', depth+1);

    li.appendChild(div);
    li.appendChild(ul);


    for (const i of data.notes){
        const noteLi = document.createElement("li");

        const div = document.createElement("div");
        const spanIndent = document.createElement("span");
        const spanContent = document.createElement("span");

        div.classList.add("file-row");
        spanIndent.classList.add("indent");
        spanIndent.style.setProperty("--level", depth + 1);
        spanContent.textContent = i.name;
        spanContent.classList.add("content");
        spanContent.setAttribute("data-type", i.type)
        spanContent.setAttribute("data-name", i.name)

        div.appendChild(spanIndent);
        div.appendChild(spanContent);
        noteLi.appendChild(div);
        ul.appendChild(noteLi);
    }
    for (const p of data.children){
        createNavTree(p,ul, depth+1)
    }
    parentTag.appendChild(li);

}


export async function setupTreeView(){
  const nav = document.getElementById('sidebar');
  const navData = await fetchTreeData()
  const outerList = document.createElement('ul');

  outerList.classList.add('tree-view');

  createNavTree(navData, outerList);
  nav.appendChild(outerList);

  const dirs = document.querySelectorAll('.dir-row');
  const files = document.querySelectorAll('.file-row');  

  dirs.forEach(dir => {
    dir.addEventListener('click', function (e) {
      e.stopPropagation();
      const caretSpan = this.querySelector('.caret');
        if (caretSpan){
          caretSpan.classList.toggle('caret-down');
        }
      const nested = dir.parentElement.querySelector('ul.nested');
      if (nested) {
        nested.classList.toggle("active");
      }
    });
  });

  files.forEach(file => {
      file.addEventListener('click', async function(e){
        const preview = document.getElementById("preview");
        e.stopPropagation();
        const dirDiv = this.parentElement.parentElement.parentElement.querySelector('div.dir-row');
        const parentPath = dirDiv.dataset.path

        const spanContent = this.querySelector("span.content")
        const name = spanContent.dataset.name
        
        const fileType = this.querySelector("span.content").dataset.type;
        const response = await fetch(`/render?parentPath=${encodeURIComponent(parentPath)}&name=${encodeURIComponent(name)}&type=${encodeURIComponent(fileType)}`);
        
        if (!response.ok){
          console.error("Failed to fetch SVG: ", await response.text());
          return;
        }

        const svg = await response.text();
        preview.innerHTML = svg;

      });
  });
}



export async function fetchTreeData(){
    try {
        const response = await fetch('/tree');
        if (!response.ok){
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const treeData = await response.json();
        return treeData

    } catch(error){
        console.error('Failed to fetch tree data: ', error)
        return null;
    }
}
