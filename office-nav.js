(function(){
'use strict';
function add(host,section,label,icon){if(!host||host.querySelector('[data-office="'+section+'"]'))return;const b=document.createElement('button');b.type='button';b.dataset.office=section;b.className='';b.innerHTML=(host.classList.contains('mobile-nav')?'<span aria-hidden="true">'+icon+'</span>':'')+label;b.onclick=()=>{location.href=section==='documents'?'/documents.html':'/office.html?section='+section;};host.append(b);}
const side=document.querySelector('.side-nav'),mobile=document.querySelector('.mobile-nav');
add(side,'summary','Resumen general','▤');add(side,'contacts','Contactos','♧');add(side,'documents','Documentos','▱');
if(mobile){document.getElementById('backup-mobile')?.remove();mobile.querySelector('[data-backup]')?.remove();add(mobile,'summary','Resumen','▤');add(mobile,'contacts','Contactos','♧');add(mobile,'documents','Docs','▱');mobile.style.setProperty('grid-template-columns','repeat('+mobile.children.length+',minmax(0,1fr))','important');mobile.classList.add('office-mobile-menu');}
const current=new URLSearchParams(location.search).get('section');document.querySelectorAll('[data-office]').forEach(b=>b.classList.toggle('active',(location.pathname==='/office.html'&&b.dataset.office===current)||(location.pathname==='/documents.html'&&b.dataset.office==='documents')));
if(current==='warehouses'&&location.pathname!=='/office.html')window.EBOperations?.renderWarehouses();
})();
