(function(){
'use strict';
const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const categories=['Certificados','Análisis de laboratorio','Asambleas','Acta constitutiva','IMPI','COMERCAM','AMMA','FDA','COFEPRIS','Contratos'];
const hints=['Certificados y constancias','Resultados y dictámenes','Actas y acuerdos de socios','Constitución y modificaciones','Marca y propiedad industrial','Documentación COMERCAM','Documentación AMMA','Documentación FDA','Documentación COFEPRIS','Contratos y convenios'];
const icons=['<path d="M8 3h8l4 4v13H4V3h4m8 0v5h4M8 11h8M8 15h5"/><circle cx="16" cy="18" r="3"/>','<path d="M9 3h6m-5 0v7L5 19a1 1 0 0 0 1 2h12a1 1 0 0 0 1-2l-5-9V3M8 15h8"/>','<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-16a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 4v3"/>','<path d="M5 3h10l4 4v14H5V3m10 0v5h4M8 12h8M8 16h8"/>','<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3"/><path d="m8 12 3 3 5-6"/>'];
const icon=i=>'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(icons[i]||icons[0])+'</svg>';
let docs=[],selected=new URLSearchParams(location.search).get('category')||'',search='',filter='',trash=false,loading=false,dirty=false,saving=false,session=null,uploadId='',stats={};
if(!categories.includes(selected))selected='';
const editor=()=>window.EBShared?.user?.role==='editor';
const date=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const showDate=v=>v?v.slice(8,10)+'/'+v.slice(5,7)+'/'+v.slice(0,4):'Sin vencimiento indicado';
const bytes=n=>n<1024*1024?(n/1024).toLocaleString('es-MX',{maximumFractionDigits:1})+' KB':(n/1024/1024).toLocaleString('es-MX',{maximumFractionDigits:1})+' MB';
function state(d){if(!d.expiry)return'none';const days=Math.round((Date.parse(d.expiry+'T12:00:00Z')-Date.parse(date()+'T12:00:00Z'))/86400000);return days<0?'expired':days<=30?'soon':'valid';}
const badge=d=>{const s=state(d);return'<span class="docs-badge '+s+'">'+esc(s==='expired'?'Vencido · '+showDate(d.expiry):s==='soon'?'Por vencer · '+showDate(d.expiry):d.expiry?'Vigente hasta '+showDate(d.expiry):'Sin vencimiento indicado')+'</span>';};
function message(t,bad=false){$('docs-message').textContent=t;$('docs-message').dataset.error=String(bad);}
async function api(route='',options={}){
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),60000);
 try{
  if(options.method){const r=await fetch('/api/session',{credentials:'same-origin',cache:'no-store',signal:controller.signal});session=await r.json();if(!session.authenticated)throw Error('La sesión venció. Recarga la app para entrar.');}
  const r=await fetch('/api/documents'+route,{credentials:'same-origin',cache:'no-store',...options,headers:{'Content-Type':'application/json',...(session?.csrf?{'X-EB-CSRF':session.csrf}:{}),...options.headers},signal:controller.signal});
  const data=await r.json();if(!r.ok)throw Object.assign(Error(data.error||'No se pudo completar la operación.'),{status:r.status});return data;
 }catch(e){if(e.name==='AbortError')throw Error('No se confirmó el guardado. Tu selección permanece; puedes reintentar sin duplicar el archivo.');throw e;}finally{clearTimeout(timeout);}
}
function legacy(){try{const d=JSON.parse(localStorage.getItem('eb-v1'));return Array.isArray(d.documents)?d.documents:[];}catch{return[];}}
function shell(){
 $('documents-app').innerHTML='<div class="heading"><div><div class="eyebrow">SAGAV CUATRO · ARCHIVO COMPARTIDO</div><h1>Documentos</h1><p class="muted">Cada documento en su lugar. Disponible en PC y celular.</p></div><div class="docs-heading-actions"><button class="secondary" id="docs-refresh" aria-label="Actualizar documentos">Actualizar</button>'+ (editor()?'<button class="primary" id="docs-new">+ Subir documento</button>':'')+'</div></div><div id="docs-message" role="status" aria-live="polite"></div><div id="docs-categories" class="docs-categories"></div><div id="docs-alerts" class="docs-alerts"></div><section class="docs-panel"><div class="docs-toolbar"><div><h2 id="docs-title"></h2><p id="docs-count" class="muted"></p></div><div class="docs-tools"><button class="secondary" id="docs-all">Ver todos</button>'+ (editor()?'<button class="secondary" id="docs-trash">Papelera</button>':'')+'</div></div><div class="docs-filters"><input type="search" id="docs-search" placeholder="Buscar documento o lote" aria-label="Buscar documento o lote"><select id="docs-status" aria-label="Filtrar por vencimiento"><option value="">Todos los vencimientos</option><option value="soon">Por vencer en 30 días</option><option value="expired">Vencidos</option><option value="valid">Vigentes</option><option value="none">Sin vencimiento indicado</option></select></div><div id="docs-list"><div class="empty">Cargando documentos…</div></div></section><div id="docs-legacy"></div><p class="docs-footer" id="docs-storage"></p>';
 $('docs-new')?.addEventListener('click',()=>open());$('docs-refresh').onclick=()=>load(true);
 $('docs-search').oninput=()=>{search=$('docs-search').value;draw();};$('docs-status').onchange=()=>{filter=$('docs-status').value;draw();};
 $('docs-all').onclick=()=>choose('');$('docs-trash')?.addEventListener('click',()=>{trash=!trash;selected='';filter='';$('docs-status').value='';load(true);});
 const old=legacy();if(old.length){$('docs-legacy').innerHTML='<details class="docs-legacy"><summary>'+old.length+' ficha(s) del registro anterior · conservadas</summary><p>No se han borrado ni convertido en archivos. Puedes subir su documento en la categoría correspondiente.</p>'+old.map(d=>{const link=String(d.link||'');return'<p><b>'+esc(d.name||d.title||'Documento')+'</b> · '+esc(d.type||'Sin categoría')+(d.lot?' · Lote '+esc(d.lot):'')+(d.expiry?' · '+showDate(d.expiry):'')+(/^https?:\/\//i.test(link)?' <a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">Abrir enlace anterior</a>':'')+'</p>';}).join('')+'</details>';}
 draw();load();
}
function choose(cat){selected=cat;filter='';$('docs-status').value='';history.replaceState(null,'',location.pathname+(cat?'?category='+encodeURIComponent(cat):''));if(trash){trash=false;load(true);}else draw();}
function draw(){
 $('docs-categories').innerHTML=categories.map((c,i)=>'<button class="docs-category '+(!trash&&selected===c?'selected':'')+'" data-category="'+esc(c)+'" aria-pressed="'+(!trash&&selected===c)+'"><span class="docs-icon">'+icon(i)+'</span><strong>'+esc(c)+'</strong><small>'+hints[i]+'</small><span class="docs-category-count">'+(trash?'':docs.filter(d=>d.category===c).length+' archivos')+'</span></button>').join('');
 document.querySelectorAll('[data-category]').forEach(b=>b.onclick=()=>choose(b.dataset.category));
 const expired=docs.filter(d=>state(d)==='expired').length,soon=docs.filter(d=>state(d)==='soon').length;
 $('docs-alerts').innerHTML=!trash&&(expired||soon)?'<span>Vigencias:</span>'+(expired?'<button data-status="expired" class="expired">'+expired+' vencido'+(expired===1?'':'s')+'</button>':'')+(soon?'<button data-status="soon" class="soon">'+soon+' por vencer en 30 días</button>':''):'';
 document.querySelectorAll('[data-status]').forEach(b=>b.onclick=()=>{selected='';filter=b.dataset.status;$('docs-status').value=filter;draw();});
 $('docs-title').textContent=trash?'Papelera':selected||'Todos los documentos';$('docs-trash')?.classList.toggle('active',trash);
 const q=search.trim().toLocaleLowerCase('es'),list=docs.filter(d=>(!selected||d.category===selected)&&(!filter||state(d)===filter)&&[d.title,d.filename,d.category,d.lot,d.notes].join(' ').toLocaleLowerCase('es').includes(q));
 $('docs-count').textContent=list.length+' archivo'+(list.length===1?'':'s')+(trash?' · puedes restaurarlos':'');
 $('docs-list').innerHTML=list.length?list.map(d=>'<article class="docs-file"><div class="docs-file-main"><span class="docs-file-icon">'+icon(Math.max(0,categories.indexOf(d.category)))+'</span><div><span class="docs-type">'+esc(d.category)+'</span><h3>'+esc(d.title)+'</h3><p class="docs-file-meta">'+esc(d.filename)+' · '+bytes(d.size)+(d.lot?' · Lote '+esc(d.lot):'')+'</p>'+badge(d)+(d.notes?'<details class="docs-notes"><summary>Notas</summary><p>'+esc(d.notes)+'</p></details>':'')+'</div></div><div class="docs-file-actions">'+(trash?'<button class="primary" data-restore="'+d.id+'">Restaurar</button>':'<a class="btn secondary" href="/api/documents/'+d.id+'/file?inline=1" target="_blank" rel="noopener">Abrir</a><a class="btn primary" href="/api/documents/'+d.id+'/file" download>Descargar</a>'+(editor()?'<button class="secondary" data-edit-doc="'+d.id+'">Editar datos</button><button class="docs-remove" data-delete-doc="'+d.id+'">Eliminar</button>':''))+'</div></article>').join(''):'<div class="empty"><h2>'+esc(loading?'Cargando documentos…':q||filter?'Sin coincidencias':trash?'Papelera vacía':'Sin archivos todavía')+'</h2><p>'+esc(trash?'Los documentos eliminados aparecerán aquí.':selected?'Guarda aquí tus documentos de '+selected.toLocaleLowerCase('es')+'.':'Selecciona una categoría o sube tu primer documento.')+'</p>'+(!trash&&editor()?'<button class="primary" id="docs-empty-upload">+ Subir documento</button>':'')+'</div>';
 $('docs-empty-upload')?.addEventListener('click',()=>open());document.querySelectorAll('[data-edit-doc]').forEach(b=>b.onclick=()=>open(docs.find(d=>d.id===b.dataset.editDoc)));
 document.querySelectorAll('[data-delete-doc]').forEach(b=>b.onclick=()=>remove(docs.find(d=>d.id===b.dataset.deleteDoc)));
 document.querySelectorAll('[data-restore]').forEach(b=>b.onclick=()=>restore(docs.find(d=>d.id===b.dataset.restore)));
}
async function load(announce=false){
 if(loading)return;loading=true;$('docs-refresh').disabled=true;
 try{const r=await api(trash?'?trash=1':'');docs=r.documents;stats=r;loading=false;draw();$('docs-storage').textContent='Archivos guardados en la base compartida · '+bytes(r.usedBytes)+' de 500 MB. Hasta 10 MB por archivo. Los avisos de vencimiento se muestran en esta sección.';if(announce)message('Documentos actualizados.');}
 catch(e){message('No se pudo actualizar: '+e.message,true);}finally{loading=false;$('docs-refresh').disabled=false;}
}
function open(doc){
 if(!doc&&window.EBDocBatch){let lots=[];try{lots=JSON.parse(localStorage.getItem('eb-v1')).lots.map(l=>l.id);}catch{}return window.EBDocBatch.open({categories,selected,lots,editor,api,dirty:v=>{dirty=v;},saving:v=>{saving=v;},saved:async(category,count,back)=>{selected=category;trash=false;filter='';$('docs-status').value='';await load();window.EBEditReturn?.restore(back);message(count+' archivo'+(count===1?' guardado':'s guardados')+' y confirmado'+(count===1?'':'s')+' en la base compartida.');}});}
 if(!editor()||$('docs-dialog'))return;const back=window.EBEditReturn?.capture();dirty=false;uploadId=crypto.randomUUID();
 const dialog=document.createElement('dialog');dialog.id='docs-dialog';dialog.className='docs-dialog';
 let lots=[];try{lots=JSON.parse(localStorage.getItem('eb-v1')).lots.map(l=>l.id);}catch{}if(doc?.lot&&!lots.includes(doc.lot))lots.push(doc.lot);
 const cat=doc?.category||selected||'';
 dialog.innerHTML='<div class="docs-dialog-title"><div><div class="eyebrow">'+(doc?'DOCUMENTO GUARDADO':'NUEVO ARCHIVO')+'</div><h2>'+(doc?'Editar datos':'Subir documento')+'</h2></div><button type="button" id="docs-close" aria-label="Cerrar">×</button></div><form id="docs-form"><div id="docs-form-error" class="docs-form-error" role="alert"></div><label>Categoría *<select id="doc-category" required><option value="">Selecciona una categoría</option>'+categories.map(c=>'<option '+(cat===c?'selected':'')+'>'+esc(c)+'</option>').join('')+'</select></label>'+(!doc?'<label class="docs-upload">Archivo *<input id="doc-file" type="file" required accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.heif,.doc,.docx,.xls,.xlsx"><small>PDF, imágenes, Word o Excel · máximo 10 MB.</small></label>':'<p class="docs-file-meta">Archivo: '+esc(doc.filename)+'. Para conservar versiones, sube las renovaciones como documentos nuevos.</p>')+'<label>Nombre del documento *<input id="doc-title" required maxlength="160" value="'+esc(doc?.title||'')+'" placeholder="Ej. Certificado CRM · Espadín"></label><details class="docs-optional" '+(doc?.lot||doc?.expiry||doc?.notes?'open':'')+'><summary>Lote, vencimiento y notas (opcional)</summary><label>Lote relacionado<select id="doc-lot"><option value="">General / SAGAV Cuatro</option>'+lots.map(id=>'<option value="'+esc(id)+'" '+(doc?.lot===id?'selected':'')+'>'+esc(id)+'</option>').join('')+'</select></label><label>Fecha de vencimiento<input id="doc-expiry" type="date" value="'+esc(doc?.expiry||'')+'"></label><small>Déjala vacía cuando no aplique. La app señalará documentos vencidos o próximos a vencer en 30 días.</small><label>Notas<textarea id="doc-notes" maxlength="2000" rows="3">'+esc(doc?.notes||'')+'</textarea></label></details><div class="docs-form-actions"><button type="button" class="secondary" id="doc-cancel">Cancelar</button><button type="submit" class="primary" id="doc-save">'+(doc?'Guardar cambios':'Guardar documento')+'</button></div><p class="docs-save-note">Solo se confirma guardado cuando el servidor recibe el archivo. No se envía a servicios externos.</p></form>';
 document.body.append(dialog);dialog.showModal();
 const close=()=>{if(saving)return;if(dirty&&!confirm('¿Cerrar sin guardar? El archivo aún no se ha cargado.'))return;dialog.close();};
 $('docs-close').onclick=close;$('doc-cancel').onclick=close;dialog.oncancel=e=>{e.preventDefault();close();};dialog.onclose=()=>{dirty=false;dialog.remove();window.EBShared?.cancelDraft?.();};
 $('docs-form').oninput=()=>{dirty=true;};$('docs-form').onchange=()=>{dirty=true;uploadId=crypto.randomUUID();};
 $('doc-file')?.addEventListener('change',()=>{const f=$('doc-file').files[0];if(f&&!$('doc-title').value)$('doc-title').value=f.name.replace(/\.[^.]+$/,'').slice(0,160);});
 $('docs-form').onsubmit=async e=>{
  e.preventDefault();if(saving)return;saving=true;const button=$('doc-save');button.disabled=true;button.textContent='Guardando…';$('docs-form-error').textContent='';
  try{
   const input={title:$('doc-title').value,category:$('doc-category').value,lot:$('doc-lot').value,expiry:$('doc-expiry').value,notes:$('doc-notes').value};
   if(!doc){const f=$('doc-file').files[0];if(!f)throw Error('Selecciona el archivo.');if(!f.size||f.size>10*1024*1024)throw Error('El archivo debe tener contenido y pesar hasta 10 MB.');input.id=uploadId;input.filename=f.name;input.base64=await new Promise((resolve,reject)=>{const fr=new FileReader();fr.onerror=()=>reject(Error('No se pudo leer el archivo.'));fr.onload=()=>resolve(String(fr.result).split(',')[1]);fr.readAsDataURL(f);});}else input.revision=doc.revision;
   await api(doc?'/'+doc.id:'',{method:doc?'PATCH':'POST',body:JSON.stringify(input)});
   dirty=false;if(!doc){selected=input.category;trash=false;filter='';$('docs-status').value='';}dialog.close();await load();window.EBEditReturn?.restore(back);message(doc?'Datos actualizados en la base compartida.':'Documento guardado y disponible para los socios en PC y celular.');
  }catch(err){$('docs-form-error').textContent=err.message;}finally{saving=false;if(button.isConnected){button.disabled=false;button.textContent=doc?'Guardar cambios':'Guardar documento';}}
 };
}
async function remove(d){if(!d||!editor()||!confirm('¿Mover «'+d.title+'» a la papelera? Podrás restaurarlo.'))return;try{await api('/'+d.id,{method:'DELETE',body:JSON.stringify({revision:d.revision})});await load();message('Documento enviado a la papelera.');}catch(e){message(e.message,true);}}
async function restore(d){if(!d||!editor())return;try{await api('/'+d.id+'/restore',{method:'POST',body:JSON.stringify({revision:d.revision})});await load();message('Documento restaurado. Pulsa Ver todos para consultarlo.');}catch(e){message(e.message,true);}}
window.addEventListener('beforeunload',e=>{if(dirty||saving){e.preventDefault();e.returnValue='';}});
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!$('docs-dialog'))load();});
setInterval(()=>{if(!document.hidden&&!$('docs-dialog'))load();},15000);
shell();
})();
