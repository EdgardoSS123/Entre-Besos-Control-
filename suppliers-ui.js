(function(){
'use strict';
const $=id=>document.getElementById(id),C=window.EBSupplierCore;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let query='',filter='',trash=false,dialog=null,editing=null,dirty=false,busy=false,chosen=[],returnView=null;
const editor=()=>window.EBShared?.user?.role==='editor';
function read(){const raw=localStorage.getItem('eb-v1'),data=JSON.parse(raw||'null');if(!data||!Array.isArray(data.lots)||!Array.isArray(data.moves))throw Error('No se pudo leer la base compartida. No se reiniciaron tus datos.');C.rows(data);return{raw,data};}
function message(m,bad=false){const el=$('supplier-message');if(el){el.textContent=m;el.dataset.error=String(bad);}}
function formError(m){
 const el=$('supplier-error');if(!el){message(m,true);return;}
 el.textContent=m;el.hidden=!m;
 if(m)requestAnimationFrame(()=>{if(el.isConnected)el.scrollIntoView({block:'nearest',behavior:'instant'});});
}
function setSaving(value){
 const b=$('supplier-save');if(b){b.disabled=value;b.textContent=value?'Guardando…':'Guardar proveedor';}
 for(const id of ['supplier-close','supplier-cancel'])if($(id))$(id).disabled=value;
 $('supplier-form')?.setAttribute('aria-busy',String(value));
 for(const el of $('supplier-form')?.querySelectorAll('input,select,textarea,button')||[]){
  if(['supplier-save','supplier-cancel'].includes(el.id))continue;
  if(value){if(el.dataset.beforeSaveDisabled===undefined)el.dataset.beforeSaveDisabled=el.disabled?'1':'0';el.disabled=true;}
  else if(el.dataset.beforeSaveDisabled!==undefined){el.disabled=el.dataset.beforeSaveDisabled==='1';delete el.dataset.beforeSaveDisabled;}
 }
}
function collectInput(){
 // Some touch/autofill flows leave a selected value without firing change.
 const select=$('supplier-item'),other=$('supplier-other').value.trim();
 if(select.value&&select.value!=='__other__')addItem(select.value);
 if((select.value==='__other__'||!$('supplier-other-wrap').hidden)&&other)addItem(other);
 // An empty optional Otros field must not reject already selected supplies.
 return {name:$('supplier-name').value,items:[...chosen],contact:$('supplier-contact').value,phone:$('supplier-phone').value,email:$('supplier-email').value.trim(),place:$('supplier-place').value,notes:$('supplier-notes').value};
}
async function confirmedRecord(result){
 const row=await window.EBShared.snapshot();
 const saved=(row.data?.suppliers||[]).find(x=>x.id===result.record.id);
 if(saved&&JSON.stringify(saved)===JSON.stringify(result.record))return saved;
 throw Error('El proveedor no coincide con la versión confirmada. Tu captura se conserva; revisa si otro socio lo modificó.');
}
function render(){
 try{
  const d=read().data,names=C.catalog(d),all=C.rows(d),count=all.filter(x=>!x.deletedAt).length;
  if(filter&&!names.includes(filter))names.push(filter);
  $('suppliers-app').innerHTML=`<div class="heading"><div><div class="eyebrow">DIRECTORIO DE INSUMOS</div><h1>Proveedores</h1><p class="muted">Quién nos surte y cómo contactarlo.</p></div>${editor()?'<button class="primary" id="supplier-new">+ Nuevo proveedor</button>':''}</div><div class="supplier-toolbar"><input id="supplier-search" type="search" placeholder="Buscar proveedor, contacto o insumo" aria-label="Buscar proveedores" value="${esc(query)}"><select id="supplier-filter" aria-label="Filtrar por insumo"><option value="">Todos los insumos</option>${names.map(x=>`<option value="${esc(x)}" ${x===filter?'selected':''}>${esc(x)}</option>`).join('')}</select></div><div class="supplier-list-heading"><span id="supplier-count">${count} proveedores</span>${editor()?`<button class="textbtn" id="supplier-trash">${trash?'Volver al directorio':'Papelera'}</button>`:''}</div><p id="supplier-message" role="status"></p><section id="supplier-list" aria-label="Registro de proveedores"></section>`;
  $('supplier-new')?.addEventListener('click',()=>open());
  $('supplier-search').oninput=()=>{query=$('supplier-search').value;draw();};
  $('supplier-filter').onchange=()=>{filter=$('supplier-filter').value;draw();};
  $('supplier-trash')?.addEventListener('click',()=>{trash=!trash;render();});draw();
 }catch(e){$('suppliers-app').innerHTML='<div class="alert">'+esc(e.message)+'</div>';}
}
function draw(){
 const d=read().data,records=C.rows(d).filter(r=>!!r.deletedAt===trash).map(r=>({r,v:C.view(r)})).filter(({v})=>(!filter||v.items.some(x=>C.norm(x)===C.norm(filter)))&&C.norm([v.name,v.contact,v.place,v.email,v.phone,...v.items].join(' ')).includes(C.norm(query))).sort((a,b)=>a.v.name.localeCompare(b.v.name,'es'));
 $('supplier-count').textContent=records.length+' proveedor'+(records.length===1?'':'es')+(trash?' en papelera':'');
 $('supplier-list').innerHTML=records.length?records.map(({r,v})=>{
  const tel=v.phone.replace(/[^+0-9]/g,'');
  return `<article class="supplier-card" data-supplier="${esc(r.id)}"><div class="supplier-card-head"><div><small>PROVEEDOR</small><h2>${esc(v.name)}</h2>${v.place?`<p class="muted">${esc(v.place)}</p>`:''}</div>${editor()?`<div class="supplier-actions">${trash?`<button class="secondary" data-supplier-restore="${esc(r.id)}">Restaurar</button>`:`<button class="secondary" data-supplier-edit="${esc(r.id)}">Editar</button><button class="textbtn supplier-delete" data-supplier-delete="${esc(r.id)}">Eliminar</button>`}</div>`:''}</div><div class="supplier-tags" aria-label="Insumos que ofrece">${v.items.map(x=>`<span>${esc(x)}</span>`).join('')}</div><div class="supplier-contact-lines">${v.contact?`<div><small>CONTACTO</small><strong>${esc(v.contact)}</strong></div>`:''}${v.phone?`<div><small>TELÉFONO</small><a href="tel:${esc(tel)}">${esc(v.phone)}</a></div>`:''}${v.email?`<div><small>CORREO</small><a href="mailto:${esc(encodeURIComponent(v.email))}">${esc(v.email)}</a></div>`:''}</div>${v.notes?`<details class="supplier-notes"><summary>Notas</summary><p>${esc(v.notes)}</p></details>`:''}</article>`;
 }).join(''):`<div class="empty"><h2>${trash?'Sin proveedores en esta selección de papelera':'Sin proveedores en esta selección'}</h2><p>${query||filter?'Cambia la búsqueda o el insumo.':editor()?'Pulsa «Nuevo proveedor» para agregar el primero.':'No hay registros para consultar.'}</p></div>`;
 document.querySelectorAll('[data-supplier-edit]').forEach(b=>b.onclick=()=>open(b.dataset.supplierEdit));
 document.querySelectorAll('[data-supplier-delete]').forEach(b=>b.onclick=()=>changeState(b.dataset.supplierDelete,'delete'));
 document.querySelectorAll('[data-supplier-restore]').forEach(b=>b.onclick=()=>changeState(b.dataset.supplierRestore,'restore'));
}
function closeForm(restore=true){
 if(!dialog)return;const d=dialog,state=returnView;dialog=null;editing=null;dirty=false;returnView=null;window.EBShared?.cancelDraft?.();if(d.contains(document.activeElement))document.activeElement.blur();if(d.open)d.close();d.remove();if(restore)window.EBEditReturn?.restore(state);
}
function chosenList(){
 $('supplier-chosen').innerHTML=chosen.length?chosen.map((x,i)=>`<span class="supplier-picked">${esc(x)}<button type="button" data-remove-supply="${i}" aria-label="Quitar ${esc(x)}">×</button></span>`).join(''):'<span class="muted">Selecciona uno o varios insumos.</span>';
 document.querySelectorAll('[data-remove-supply]').forEach(b=>b.onclick=()=>{chosen.splice(Number(b.dataset.removeSupply),1);dirty=true;chosenList();});
}
function addItem(value){const v=String(value||'').trim();if(!v||v.length>160)throw Error('Escribe un insumo de hasta 160 caracteres.');if(C.norm(v)==='otros')throw Error('Escribe el concepto específico, por ejemplo: cajas de regalo.');if(!chosen.some(x=>C.norm(x)===C.norm(v)))chosen.push(v);dirty=true;chosenList();}
function open(id){
 if(!editor()||busy||dialog)return;
 const d=read().data,r=id?C.rows(d).find(x=>x.id===id):null;if(id&&!r){message('Proveedor no encontrado.',true);return;}
 const v=r?C.view(r):{name:'',items:[],contact:'',place:'',email:'',phone:'',notes:''};
 editing=r?{id:r.id,expected:JSON.stringify(r)}:{id:crypto.randomUUID()};dirty=false;chosen=[...v.items];returnView=window.EBEditReturn?.capture();
 dialog=document.createElement('dialog');dialog.className='supplier-dialog';dialog.id='supplier-dialog';dialog.setAttribute('aria-labelledby','supplier-dialog-title');
 dialog.innerHTML=`<div class="supplier-dialog-head"><div><div class="eyebrow">REGISTRO DE PROVEEDORES</div><h2 id="supplier-dialog-title">${r?'Editar proveedor':'Nuevo proveedor'}</h2></div><button type="button" id="supplier-close" aria-label="Cerrar">×</button></div><form id="supplier-form" novalidate><div class="supplier-fields"><label class="wide">Proveedor / empresa *<input id="supplier-name" required maxlength="160" autocomplete="organization" value="${esc(v.name)}"></label><div class="wide"><label for="supplier-item">Insumos que ofrece *</label><select id="supplier-item"><option value="">Selecciona un insumo</option>${C.catalog(d).map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('')}<option value="__other__">Otros…</option></select><div id="supplier-other-wrap" class="supplier-other" hidden><label for="supplier-other">Escribe el insumo</label><div><input id="supplier-other" maxlength="160" value=""><button type="button" class="secondary" id="supplier-add-other">Agregar</button></div></div><div id="supplier-chosen" class="supplier-chosen" aria-live="polite"></div></div><label>Persona de contacto<input id="supplier-contact" maxlength="160" autocomplete="name" value="${esc(v.contact)}"></label><label>Teléfono<input id="supplier-phone" type="tel" maxlength="60" autocomplete="tel" value="${esc(v.phone)}"></label><label class="wide">Correo<input id="supplier-email" type="email" maxlength="254" autocomplete="email" value="${esc(v.email)}"></label><label class="wide">Ubicación / dirección<input id="supplier-place" maxlength="240" autocomplete="street-address" value="${esc(v.place)}"></label></div><details class="supplier-notes"><summary>Notas (opcional)</summary><label for="supplier-notes">Presentaciones, condiciones o referencias</label><textarea id="supplier-notes" maxlength="1000" rows="3">${esc(v.notes)}</textarea></details><p class="supplier-help">Registrar un proveedor no cambia tus inventarios ni costos.</p><p id="supplier-error" role="alert" hidden></p><div class="supplier-form-actions"><button class="secondary" type="button" id="supplier-cancel">Cancelar</button><button class="primary" type="submit" id="supplier-save">Guardar proveedor</button></div></form>`;
 document.body.append(dialog);dialog.showModal();chosenList();
 const cancel=()=>{if(busy)return;if(dirty&&!confirm('¿Salir sin guardar los cambios del proveedor?'))return;closeForm();};
 $('supplier-close').onclick=cancel;$('supplier-cancel').onclick=cancel;dialog.addEventListener('cancel',e=>{e.preventDefault();cancel();});
 $('supplier-item').onchange=()=>{try{formError('');const value=$('supplier-item').value;$('supplier-other-wrap').hidden=value!=='__other__';if(value==='__other__'){$('supplier-other').value='';$('supplier-other').focus();return;}if(value){addItem(value);$('supplier-item').value='';}}catch(e){formError(e.message);}};
 $('supplier-add-other').onclick=()=>{try{addItem($('supplier-other').value);$('supplier-other').value='';$('supplier-other-wrap').hidden=true;$('supplier-item').value='';formError('');}catch(e){formError(e.message);}};
 $('supplier-form').oninput=()=>{dirty=true;};$('supplier-form').onchange=()=>{dirty=true;};$('supplier-form').onsubmit=e=>{e.preventDefault();save();};
}
function options(extra={}){return{...editing,...extra,operation:crypto.randomUUID(),stamp:new Date().toISOString(),actor:window.EBShared.user.username};}
function persist(result,raw){
 if(result.unchanged)return;
 if(localStorage.getItem('eb-v1')!==raw)throw Error('La base cambió en otra pestaña. Vuelve a abrir el proveedor antes de guardar.');
 localStorage.setItem('eb-v1',JSON.stringify(result.data));
}
async function confirmShared(result,label){
 try{const row=await window.EBShared.snapshot(),saved=(row.data.suppliers||[]).find(x=>x.id===result.record.id);if(saved&&saved.version>=result.record.version)message(label+' Confirmado en la base compartida.');else message(label+' Revisa la sincronización.',true);}catch(e){message(label+' Guardado en este dispositivo; pendiente de sincronizar.',true);}
}
async function save(){
 if(busy||!editor())return;busy=true;setSaving(true);formError('');let locallySaved=false;
 try{
  const input=collectInput(),before=read(),result=C.change(before.data,input,options());
  persist(result,before.raw);locallySaved=true;
  // Retrying after a network problem updates this same record, never adds a duplicate.
  editing={id:result.record.id,expected:JSON.stringify(result.record)};
  setSaving(true);await confirmedRecord(result);
  const state=returnView;closeForm(false);render();window.EBEditReturn?.restore(state);
  message(result.unchanged?'Proveedor confirmado. Sin cambios adicionales.':'Proveedor guardado. Confirmado en la base compartida.');
 }catch(e){
  formError(locallySaved?'Tu captura está guardada en este dispositivo, pero no se confirmó en la base compartida. No la vuelvas a crear; pulsa Guardar para reintentar. '+e.message:'No se guardó: '+e.message);
 }finally{busy=false;setSaving(false);}
}
async function changeState(id,action){
 if(busy||!editor()||dialog)return;const before=read(),r=C.rows(before.data).find(x=>x.id===id);if(!r)return;
 if(!confirm(action==='delete'?'¿Enviar a '+C.view(r).name+' a Papelera? No cambia inventarios ni pedidos.':'¿Restaurar este proveedor?'))return;busy=true;
 try{const state=window.EBEditReturn?.capture(),result=C.change(before.data,null,{id,expected:JSON.stringify(r),action,operation:crypto.randomUUID(),stamp:new Date().toISOString(),actor:window.EBShared.user.username});persist(result,before.raw);window.EBShared.cancelDraft();render();window.EBEditReturn?.restore(state);await confirmShared(result,action==='delete'?'Proveedor enviado a Papelera.':'Proveedor restaurado.');}catch(e){message(e.message,true);}finally{busy=false;}
}
window.EBSuppliers={render,get dirty(){return dirty;}};
window.addEventListener('storage',e=>{if(e.key!=='eb-v1')return;if(dialog){formError('Hay cambios en otro dispositivo. Tu captura se conserva y se verificará al guardar.');return;}const state=window.EBEditReturn?.capture();render();window.EBEditReturn?.restore(state);});
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
render();
})();
