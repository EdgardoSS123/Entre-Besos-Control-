(function(){
'use strict';
const $=id=>document.getElementById(id),C=window.EBContacts,E=window.EBExecutive,esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const section=new URLSearchParams(location.search).get('section')==='contacts'?'contacts':'summary';
const contactCountryParam=new URLSearchParams(location.search).get('country');
let editing=null,dirty=false,selected=C.COUNTRIES.includes(contactCountryParam)?contactCountryParam:'México',query='';
const reader=()=>window.EBShared?.user?.role==='reader';
function read(){const raw=localStorage.getItem('eb-v1');const d=JSON.parse(raw||'null');if(!d||!Array.isArray(d.lots)||!Array.isArray(d.moves))throw Error('No se pudieron leer los registros compartidos.');return d;}
function message(m,error=false){const t=$('office-message');if(t){t.textContent=m;t.dataset.error=String(error);}}
function discard(){if(dirty&&!confirm('¿Salir de esta captura sin guardarla? Los contactos guardados se conservan.'))return false;dirty=false;window.EBShared?.cancelDraft?.();return true;}
function renderSummary(){
 const model=E.build(read(),window.EBLedger),s=model.summary;
 $('office-app').innerHTML='<div class="heading"><div><div class="eyebrow">RESUMEN PARA SOCIOS</div><h1>Dónde estamos parados</h1><p class="muted">Toda la información guardada, sin filtros de lote o bodega.</p></div></div><section class="office-report-hero"><div><strong>Resumen general en PDF</strong><p>Existencias, valor a costo, ventas, cobranza, muestras, marketing, insumos y gastos.</p></div><button class="primary" id="office-pdf">Descargar resumen PDF</button></section><div id="office-message" role="status"></div><section class="office-kpis">'+model.metrics.map(m=>'<div><span>'+esc(m.label)+'</span><strong>'+esc(m.value)+'</strong><small>'+esc(m.note)+'</small></div>').join('')+'</section>'+table(model.sections[0])+table(model.sections[1])+table(model.sections[2])+'<section class="card office-note"><h2>El PDF reúne el detalle completo</h2><p>Producción y saldos por lote; botellas, cajas, pallets y sueltas por ubicación; ventas y cobros por cliente; marketing e insumos con sus costos; gastos, fletes y registros por aclarar.</p><p><b>Los importes sin capturar no se consideran cero.</b> No se presenta el inventario como efectivo ni se inventa una utilidad neta.</p></section>';
 $('office-pdf').onclick=async()=>{const b=$('office-pdf');b.disabled=true;message('Preparando el PDF con la información guardada en la base compartida…');try{const result=await window.EBReports.download({type:'executive'});message(result?'PDF listo. Puedes descargarlo, abrirlo o compartirlo.':'No se generó el PDF. Revisa el aviso y vuelve a intentarlo.',!result);}finally{b.disabled=false;}};
}
function table(s){return'<section class="card office-table"><h2>'+esc(s.title)+'</h2><div class="office-table-scroll"><table><thead><tr>'+s.head.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+(s.body.length?s.body.map(row=>'<tr>'+row.map(x=>'<td>'+esc(x).replace(/\n/g,'<br>')+'</td>').join('')+'</tr>').join(''):'<tr><td colspan="'+s.head.length+'">'+esc(s.empty||'Sin registros capturados.')+'</td></tr>')+'</tbody></table></div>'+(s.note?'<p class="office-explain">'+esc(s.note)+'</p>':'')+'</section>';}
function renderContacts(){
 const d=read(),legacy=C.rows(d).some(r=>!C.view(r).country),options=['Todos',...C.COUNTRIES,...(legacy?['Sin país']:[])];
 $('office-app').innerHTML='<div class="heading"><div><div class="eyebrow">DIRECTORIO COMPARTIDO</div><h1>Contactos</h1><p class="muted">USA · México · Singapur</p></div>'+(!reader()?'<button class="primary" id="contact-new">+ Nuevo contacto</button>':'')+'</div><div class="office-country-tabs" role="group" aria-label="País">'+options.map(x=>'<button type="button" data-country="'+esc(x)+'" class="'+(selected===x?'selected':'')+'">'+esc(x)+'</button>').join('')+'</div><div class="office-contact-search"><input type="search" id="contact-search" placeholder="Buscar nombre, lugar, correo o teléfono" aria-label="Buscar contactos" value="'+esc(query)+'"><span id="contact-count"></span></div><div id="office-message" role="status"></div><section id="contact-editor" class="card office-editor" hidden></section><div id="contact-list"></div>';
 $('contact-new')?.addEventListener('click',()=>{if(discard())openForm();});
 document.querySelectorAll('[data-country]').forEach(b=>b.onclick=()=>{if(!discard())return;selected=b.dataset.country;editing=null;renderContacts();});
 $('contact-search').oninput=()=>{query=$('contact-search').value;drawContacts();};drawContacts();
}
function drawContacts(){
 const list=C.rows(read()).map((raw,index)=>({raw,index,c:C.view(raw)})).filter(({c})=>(selected==='Todos'||(selected==='Sin país'?!c.country:c.country===selected))&&[c.name,c.place,c.email,c.phone,c.legacyDetails].join(' ').toLocaleLowerCase('es').includes(query.toLocaleLowerCase('es'))).sort((a,b)=>a.c.name.localeCompare(b.c.name,'es'));
 $('contact-count').textContent=list.length+' contacto'+(list.length===1?'':'s');
 $('contact-list').innerHTML=list.length?list.map(({c,index})=>{
 const tel=c.phone.replace(/[^+0-9]/g,'');
 return'<article class="office-contact"><div class="office-contact-heading"><div><small>'+esc(c.country||'Sin país')+'</small><h2>'+esc(c.name||'Contacto anterior')+'</h2><p>'+esc(c.place||'Lugar por capturar')+'</p></div>'+(!reader()?'<div class="office-contact-actions"><button class="secondary" data-contact-edit="'+index+'">Editar</button><button class="secondary danger" data-contact-delete="'+index+'">Eliminar</button></div>':'')+'</div><div class="office-contact-links"><div><span>Correo</span>'+(c.email?'<a href="mailto:'+esc(encodeURIComponent(c.email))+'">'+esc(c.email)+'</a>':'<p>Por capturar</p>')+'</div><div><span>Teléfono</span>'+(c.phone?'<a href="tel:'+esc(tel)+'">'+esc(c.phone)+'</a>':'<p>Por capturar</p>')+'</div></div>'+(c.legacyDetails?'<details><summary>Datos del registro anterior</summary><p>'+esc(c.legacyDetails)+'</p></details>':'')+'</article>';
 }).join(''):'<div class="empty"><h2>Sin contactos en esta selección</h2><p>'+(!reader()?'Pulsa «Nuevo contacto» para registrar el primero.':'No hay registros coincidentes.')+'</p></div>';
 document.querySelectorAll('[data-contact-edit]').forEach(b=>b.onclick=()=>{if(discard())openForm(Number(b.dataset.contactEdit));});
 document.querySelectorAll('[data-contact-delete]').forEach(b=>b.onclick=()=>remove(Number(b.dataset.contactDelete)));
}
function openForm(index){
 if(reader())return;
 const rows=C.rows(read()),raw=index===undefined?null:rows[index],c=raw?C.view(raw):{country:C.COUNTRIES.includes(selected)?selected:'México',name:'',place:'',email:'',phone:''};
 editing=raw?{index,expected:JSON.stringify(raw)}:null;
 const host=$('contact-editor');host.hidden=false;
 host.innerHTML='<h2>'+ (raw?'Editar contacto':'Nuevo contacto')+'</h2><form id="contact-form"><div id="contact-error" role="alert"></div><div class="office-fields"><label>País *<select id="contact-country" required><option value="">Elige el país</option>'+C.COUNTRIES.map(x=>'<option '+(c.country===x?'selected':'')+'>'+x+'</option>').join('')+'</select></label><label>Nombre *<input id="contact-name" maxlength="160" required autocomplete="name" value="'+esc(c.name)+'"></label><label class="wide">Lugar / empresa / ciudad<input id="contact-place" maxlength="240" value="'+esc(c.place)+'"></label><label>Correo<input id="contact-email" type="email" maxlength="254" autocomplete="email" value="'+esc(c.email)+'"></label><label>Teléfono<input id="contact-phone" type="tel" maxlength="60" autocomplete="tel" value="'+esc(c.phone)+'"></label></div><div class="actions"><button type="button" class="secondary" id="contact-cancel">Cancelar</button><button type="submit" class="primary" id="contact-save">Guardar contacto</button></div></form>';
 $('contact-form').oninput=()=>{dirty=true;};$('contact-form').onchange=()=>{dirty=true;};
 $('contact-cancel').onclick=()=>{if(discard()){host.hidden=true;editing=null;}};
 $('contact-form').onsubmit=e=>{e.preventDefault();try{
  const data=read(),out=C.change(data,{country:$('contact-country').value,name:$('contact-name').value,place:$('contact-place').value,email:$('contact-email').value,phone:$('contact-phone').value},{...(editing||{}),id:crypto.randomUUID(),stamp:new Date().toISOString()});
  localStorage.setItem('eb-v1',JSON.stringify(out));selected=$('contact-country').value;dirty=false;editing=null;renderContacts();message('Contacto guardado. Revisa «Actualizado» para confirmar la sincronización.');
 }catch(err){$('contact-error').textContent='No se guardó: '+err.message;}};
 host.scrollIntoView({behavior:'smooth',block:'start'});$('contact-name').focus({preventScroll:true});
}
function remove(index){
 if(reader()||!discard())return;const data=read(),raw=C.rows(data)[index];if(!raw||!confirm('¿Eliminar a '+(C.view(raw).name||'este contacto')+'?'))return;
 try{const out=C.change(data,null,{index,expected:JSON.stringify(raw),remove:true,id:crypto.randomUUID(),stamp:new Date().toISOString()});localStorage.setItem('eb-v1',JSON.stringify(out));editing=null;renderContacts();message('Contacto eliminado. Se conserva el cambio en el historial.');}catch(e){message(e.message,true);}
}
function render(){try{section==='contacts'?renderContacts():renderSummary();}catch(e){$('office-app').innerHTML='<div class="alert">'+esc(e.message)+'</div>';}}
window.EBOffice={get dirty(){return dirty;},context:()=>({type:'executive'}),render};
window.addEventListener('storage',e=>{if(e.key!=='eb-v1')return;if(dirty||editing){message('Hay cambios en otro dispositivo. Tu captura se conserva; al guardar se verifica el contacto.');return;}render();});
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!a.href.startsWith('mailto:')&&!a.href.startsWith('tel:')&&dirty&&!discard())e.preventDefault();});
render();
})();
