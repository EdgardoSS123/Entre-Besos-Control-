/* Authenticated shared workspace. Existing ledger unchanged; local storage is a recoverable cache/outbox. */
(function(){
'use strict';
const KEY='eb-v1',META='eb-shared-meta-v1',OUT='eb-shared-outbox-v1',BACK='eb-before-shared-v1';
const nativeSet=Storage.prototype.setItem,nativeGet=Storage.prototype.getItem,nativeRemove=Storage.prototype.removeItem;
const get=k=>nativeGet.call(localStorage,k),set=(k,v)=>nativeSet.call(localStorage,k,v),remove=k=>nativeRemove.call(localStorage,k);
const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const signature=s=>{let n=2166136261;for(let i=0;i<s.length;i++){n^=s.charCodeAt(i);n=Math.imul(n,16777619);}return (n>>>0).toString(16)+':'+s.length;};
const parse=(raw,fallback=null)=>{try{return JSON.parse(raw||'null')??fallback;}catch{return fallback;}};
let who=null,csrf='',revision=0,ready=false,loaded=false,sending=false,touched=false,conflict=false,checking=false,remoteWaiting=false;
let seenSignature=null;
let shell,timer,reportPass=false,lastStatus='Conectando…';
const meaningful=d=>d&&Object.values(d).some(v=>Array.isArray(v)&&v.length);
function checkData(raw){const d=JSON.parse(raw);if(!d||!Array.isArray(d.lots)||!Array.isArray(d.moves))throw Error('No se pudo leer la copia local. No se borró.');return d;}
async function api(url,options={}){
 const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),15000);
 try{const r=await fetch('/api/'+url,{credentials:'same-origin',cache:'no-store',...options,headers:{'Content-Type':'application/json',...(csrf?{'X-EB-CSRF':csrf}:{}),...options.headers},signal:abort.signal});let d;try{d=await r.json();}catch{throw Error('La conexión compartida no respondió. No borres los datos.');}if(!r.ok)throw Object.assign(Error(d.error||'No se pudo sincronizar.'),{status:r.status});return d;}finally{clearTimeout(timer);}
}
function backup(raw=get(KEY),name='Entre-Besos-respaldo'){
 if(!raw)return;const u=URL.createObjectURL(new Blob([raw],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download=name+'-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),60000);
}
function preserve(){const raw=get(KEY);if(raw&&!get(BACK))set(BACK,raw);}
function status(text,bad=false){lastStatus=text;const el=$('eb-cloud-state');if(el){el.textContent=text;el.dataset.bad=String(bad);}document.documentElement.dataset.sharedStatus=bad?'pending':'ready';}
function screen(title,message,actions=''){
 if(!shell){shell=document.createElement('section');shell.id='eb-cloud-shell';document.body.append(shell);}
 shell.hidden=false;document.documentElement.classList.add('eb-cloud-loading');
 shell.innerHTML='<div class="eb-cloud-card"><img src="/icons/eb-192.png" alt="Entre Besos" width="90" height="90"><p class="eb-cloud-eyebrow">CONTROL INTERNO · BASE COMPARTIDA</p><h1>'+esc(title)+'</h1><p>'+esc(message)+'</p>'+actions+'<p id="eb-cloud-error" role="alert"></p></div>';
}
function fail(message){const el=$('eb-cloud-error');if(el)el.textContent=message;else status(message,true);}
function login(){
 ready=false;screen('Entre Besos','Entra con tu usuario de socio. PC y celular consultan la misma información.',
 '<form id="eb-login"><label for="eb-user">Usuario</label><input id="eb-user" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" required value="'+esc(get('eb-remember-user')||'')+'"><label for="eb-password">Contraseña</label><input id="eb-password" name="password" type="password" autocomplete="current-password" required><label class="eb-check"><input id="eb-remember" type="checkbox" checked> Recordar sesión</label><button id="eb-enter" type="submit">Entrar</button></form><small>Tus capturas anteriores permanecen en este dispositivo hasta conectarlas.</small>');
 $('eb-login').onsubmit=async e=>{e.preventDefault();$('eb-enter').disabled=true;try{const s=await api('login',{method:'POST',body:JSON.stringify({username:$('eb-user').value,password:$('eb-password').value,remember:$('eb-remember').checked})});set('eb-remember-user',s.user.username);who=s.user;csrf=s.csrf;await connect();}catch(e){fail(e.message);if($('eb-enter'))$('eb-enter').disabled=false;}};
}
function keepCloud(row,message){
 screen('Hay una copia local distinta',message+' La copia local se conserva como respaldo; no se combinarán ni reemplazarán registros automáticamente.',
 '<button id="eb-local-export" class="secondary">Respaldar esta copia local</button><button id="eb-use-cloud">Usar la información compartida</button>');
 $('eb-local-export').onclick=()=>backup(get(OUT)?parse(get(OUT)).raw:get(KEY),'Entre-Besos-copia-local');
 $('eb-use-cloud').onclick=async()=>{try{preserve();if(get(OUT))set('eb-conflict-copy-v1',parse(get(OUT)).raw);remove(OUT);conflict=false;accept(row);if(!loaded)await startApp();else location.reload();}catch(e){fail(e.message);}};
}
async function connect(){
 try{
  const row=await api('state'),local=get(KEY),meta=parse(get(META));revision=row.revision;
  if(!row.data){
   const d=local?checkData(local):null;
   if(meaningful(d)&&who.role==='editor'){
    screen('Conectar mis datos','Esta copia contiene '+d.lots.length+' lotes, '+(d.materials||[]).length+' registros de marketing y '+(d.supplies||[]).length+' de insumos. Se publicará completa, sin volver a capturar.',
    '<button id="eb-publish">Usar estos datos como base compartida</button><button id="eb-migrate-backup" class="secondary">Guardar respaldo primero</button>');
    $('eb-migrate-backup').onclick=()=>backup();$('eb-publish').onclick=async()=>{const b=$('eb-publish');b.disabled=true;try{preserve();const operation=crypto.randomUUID();const r=await api('state',{method:'PUT',body:JSON.stringify({revision:0,operation,data:d,initialize:true})});accept({...r,data:d});await startApp();}catch(e){fail(e.message);b.disabled=false;}};return;
   }
   screen('Falta conectar la PC','Abre Entre Besos en el navegador de la PC donde capturaste tus datos, entra con un socio EB1 y pulsa «Usar estos datos como base compartida». Después aparecerán aquí.',
   '<button id="eb-check-again">Ya conecté la PC · Actualizar</button><button id="eb-switch-user" class="secondary">Cambiar usuario</button>');$('eb-check-again').onclick=connect;$('eb-switch-user').onclick=logout;return;
  }
  const pending=parse(get(OUT));
  if(pending){
   if(who.role!=='editor'){keepCloud(row,'Hay cambios pendientes de un socio con permiso de edición.');return;}
   try{const ack=await api('state',{method:'PUT',body:JSON.stringify({revision:pending.revision,operation:pending.operation,data:checkData(pending.raw)})});if(parse(get(OUT))?.operation===pending.operation)remove(OUT);set(META,JSON.stringify({revision:ack.revision,signature:signature(pending.raw)}));return connect();}
   catch(e){if(e.status===409){conflict=true;keepCloud(row,e.message);return;}throw e;}
  }
  if(local&&meaningful(checkData(local))&&(!meta||meta.signature!==signature(local))&&local!==JSON.stringify(row.data)){
   keepCloud(row,'Este dispositivo tiene registros que todavía no están identificados como sincronizados.');return;
  }
  accept(row);if(loaded){location.reload();return;}await startApp();
 }catch(e){screen('No se pudo conectar',e.message,'<button id="eb-retry">Reintentar</button><button id="eb-emergency-backup" class="secondary">Respaldar datos de este dispositivo</button>');$('eb-retry').onclick=boot;$('eb-emergency-backup').onclick=()=>backup();}
}
function accept(row){
 const raw=JSON.stringify(row.data);if(get(KEY)&&get(KEY)!==raw)preserve();
 set(KEY,raw);set(META,JSON.stringify({revision:row.revision,signature:signature(raw)}));revision=row.revision;ready=true;conflict=false;remoteWaiting=false;
 window.EBShared.user=who;status('Actualizado · versión '+revision);
}
async function startApp(){
 if(loaded){shell.hidden=true;document.documentElement.classList.remove('eb-cloud-loading');return;}
 loaded=true;
 const viewHelper=document.createElement('script');viewHelper.type='application/x-eb-shared';viewHelper.src='/edit-return.js?v=suppliers1';document.head.append(viewHelper);
 const scripts=[viewHelper,...document.querySelectorAll('script[type="application/x-eb-shared"]:not([src^="/edit-return.js"])')];
 for(const old of [...scripts.filter(x=>x.src),...scripts.filter(x=>!x.src)]){
  await new Promise((resolve,reject)=>{const el=document.createElement('script');if(old.id)el.id=old.id;el.async=false;if(old.src){el.src=old.src;el.onload=resolve;el.onerror=()=>reject(Error('No cargó un módulo. Recarga sin borrar datos.'));}else el.textContent=old.textContent;old.replaceWith(el);if(!el.src)resolve();});
 }
 shell.hidden=true;document.documentElement.classList.remove('eb-cloud-loading');
 const bar=document.createElement('div');bar.id='eb-cloud-bar';bar.innerHTML='<span><b>'+esc(who.name)+'</b> · '+(who.role==='editor'?'EB1':'EB2 · Solo consulta')+'<small id="eb-cloud-state"></small></span><button id="eb-cloud-refresh" type="button">Actualizar</button><button id="eb-cloud-account" type="button">Cuenta</button>';
 const host=document.querySelector('.workspace')||document.body;host.prepend(bar);document.querySelectorAll('.topbar .chip').forEach(x=>x.remove());
 $('eb-cloud-refresh').onclick=async()=>{if(touched&&!confirm('¿Actualizar desde la base compartida? Guarda primero cualquier captura que quieras conservar.'))return;touched=false;await flush();if(!get(OUT))await poll(true);};
 $('eb-cloud-account').onclick=()=>{const d=document.createElement('dialog');d.className='eb-shared-account';d.innerHTML='<h2>'+esc(who.name)+'</h2><p>'+esc(who.username)+' · '+(who.role==='editor'?'EB1 · Edición':'EB2 · Consulta')+'</p><p>La información guardada se comparte entre PC y celular. Los borradores sin guardar permanecen en este dispositivo.</p><button data-backup>Respaldo</button><button data-out>Cerrar sesión</button><button data-close>Volver</button>';document.body.append(d);d.onclose=()=>d.remove();d.querySelector('[data-close]').onclick=()=>d.close();d.querySelector('[data-backup]').onclick=()=>backup();d.querySelector('[data-out]').onclick=logout;d.showModal();};
 status('Actualizado · versión '+revision);document.documentElement.classList.toggle('eb-shared-reader',who.role==='reader');
 timer=setInterval(()=>{if(get(OUT))flush();else poll();},5000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden){if(get(OUT))flush();else poll();}});
 window.addEventListener('online',()=>{if(get(OUT))flush();else poll();});
}
async function logout(){if(get(OUT)){status('Hay cambios pendientes. Conecta y espera a que aparezca Actualizado antes de salir.',true);return;}try{await api('logout',{method:'POST',body:'{}'});location.reload();}catch(e){fail(e.message);}}
function editing(){return touched||!!document.querySelector('dialog[open]')||!!$('lot-id')||($('material-form-title')?.textContent||'').includes('Editar');}
function refreshUI(raw){
 const old=get(KEY),ctx=window.EBReports?.context?.();accept({revision,data:JSON.parse(raw)});
 window.dispatchEvent(new StorageEvent('storage',{key:KEY,oldValue:old,newValue:raw,storageArea:localStorage}));
 if(ctx?.type==='warehouse')window.EBOperations?.renderWarehouses();
 else if(ctx?.type==='lot'&&ctx.lotId)window.EBSimpleUI?.open(ctx.lotId);
 else if(typeof D!=='undefined'&&typeof render==='function'){D=JSON.parse(raw);render();}
}
async function poll(force=false){
 if(!ready||checking||sending||get(OUT)||document.hidden&&!force)return;checking=true;
 try{const row=await api('state?since='+revision);if(get(OUT)||sending)return;if(row.unchanged){if(!remoteWaiting)status('Actualizado · versión '+revision);return;}
  if(editing()&&!force){remoteWaiting=true;status('Hay cambios en otro dispositivo. Guarda o cancela tu captura y pulsa Actualizar.',true);return;}
  revision=row.revision;const y=scrollY;refreshUI(JSON.stringify(row.data));window.scrollTo(0,y);status('Actualizado · versión '+revision);
 }catch(e){if(e.status===401){ready=false;login();}else status('Sin conexión · no se confirma información actualizada',true);}finally{checking=false;}
}
async function sendPending(){
 if(sending||conflict||!ready||who.role!=='editor')return;sending=true;
 try{
  let pending=parse(get(OUT));while(pending){
   status('Guardando en la base compartida…');const sent=pending;
   const ack=await api('state',{method:'PUT',body:JSON.stringify({revision:sent.revision,operation:sent.operation,data:checkData(sent.raw)})});revision=ack.revision;
   const next=parse(get(OUT));set(META,JSON.stringify({revision,signature:signature(sent.raw)}));
   if(next?.operation===sent.operation){remove(OUT);}else if(next){next.revision=revision;set(OUT,JSON.stringify(next));}
   pending=parse(get(OUT));
  }
  status('Actualizado · versión '+revision);
 }catch(e){if(e.status===409){conflict=true;status('Conflicto: se conservó tu captura local. Pulsa Actualizar para revisarlo.',true);const row=await api('state');keepCloud(row,e.message);}else if(e.status===401){ready=false;login();}else status('Pendiente de enviar · '+e.message,true);}finally{sending=false;}
}
async function flush(){if(navigator.locks)return navigator.locks.request('entre-besos-sync',{ifAvailable:true},lock=>lock?sendPending():undefined);return sendPending();}
Storage.prototype.getItem=function(k){const raw=nativeGet.call(this,k);if(this===localStorage&&String(k)===KEY&&raw)seenSignature=signature(raw);return raw;};
Storage.prototype.setItem=function(k,v){
 if(this!==localStorage||String(k)!==KEY)return nativeSet.call(this,k,v);
 const raw=String(v);if(raw===get(KEY))return;
 if(!ready||!who)throw Error('Primero inicia sesión y conecta los datos.');if(who.role!=='editor')throw Error('EB2 es solo consulta; no se modificó la información.');if(conflict)throw Error('Resuelve la copia pendiente antes de guardar nuevos cambios.');checkData(raw);
 if(seenSignature&&get(KEY)&&seenSignature!==signature(get(KEY)))throw Error('Otra pestaña cambió los datos. Conserva tu captura y actualiza antes de guardar.');
 const previous=get(OUT),existing=parse(previous),meta=parse(get(META));
 const pending={revision:existing?.revision??meta?.revision??revision,operation:crypto.randomUUID(),raw};
 set(OUT,JSON.stringify(pending));try{nativeSet.call(this,k,raw);}catch(e){if(previous)set(OUT,previous);else remove(OUT);throw e;}
 seenSignature=signature(raw);touched=false;status('Guardado local · enviando a la base compartida…');setTimeout(flush,0);
};
Storage.prototype.removeItem=function(k){if(this===localStorage&&String(k)===KEY)throw Error('No se permite borrar la base compartida desde el almacenamiento del navegador.');return nativeRemove.call(this,k);};
document.addEventListener('input',e=>{if(!loaded||e.target.closest('#eb-cloud-shell,#eb-cloud-bar,.eb-install-sheet'))return;const id=e.target.id||'';if(!/search|filter|history-warehouse/.test(id))touched=true;},true);
document.addEventListener('click',async e=>{
 const b=e.target instanceof Element?e.target.closest('button,[type="submit"]'):null;if(!b||b.closest('#eb-cloud-shell,#eb-cloud-bar,.eb-shared-account'))return;
 if(who?.role==='reader'&&/^(Guardar|Eliminar|Editar|Nuevo|Nueva|Registrar|Capturar|Mover|Descontar|Restaurar|Importar|Duplicar|\+ Otro)/i.test(b.textContent.trim())){e.preventDefault();e.stopImmediatePropagation();status('EB2 · Solo consulta. Los cambios requieren un socio EB1.',true);return;}
 if(b.matches('#eb-report-pdf,#simple-print,#print-stock,[data-print]')&&!reportPass&&!window.EBReports?.handlesSharedSnapshot){
  e.preventDefault();e.stopImmediatePropagation();await flush();if(get(OUT)||conflict){status('El PDF espera a que tus cambios estén guardados en la base compartida.',true);return;}
  try{await api('session');await poll();if(!ready||document.documentElement.dataset.sharedStatus==='pending')throw Error('Conecta para generar el reporte actualizado.');reportPass=true;const current=b.isConnected?b:document.getElementById(b.id);current?.click();}catch(err){status(err.message,true);}finally{reportPass=false;}
 }
},true);
window.addEventListener('storage',e=>{if(e.key===META){const m=parse(get(META));if(m)revision=m.revision;}if(e.key===OUT&&!sending)setTimeout(flush,0);});
window.addEventListener('beforeunload',e=>{if(get(OUT)){e.preventDefault();e.returnValue='';}});
async function reportSnapshot(){
 if(!ready||!who)throw Error('Inicia sesión para generar el reporte.');
 await flush();
 if(get(OUT)||conflict||sending)throw Error('Hay cambios pendientes de guardar. Confirma Actualizado y vuelve a generar el PDF.');
 const row=await api('state');
 if(!row.data)throw Error('Conecta primero la PC con tus datos. No se generará un resumen vacío.');
 return row;
}
window.EBShared={user:null,get revision(){return revision;},flush,snapshot:reportSnapshot,cancelDraft(){touched=false;},get pending(){return!!get(OUT);}};
async function boot(){screen('Conectando Entre Besos','Revisando acceso y datos compartidos…');try{const s=await api('session');if(!s.authenticated)return login();who=s.user;csrf=s.csrf;await connect();}catch(e){screen('Conectar Entre Besos',e.message,'<button id="eb-start-retry">Reintentar</button><button id="eb-start-backup" class="secondary">Respaldo local</button>');$('eb-start-retry').onclick=boot;$('eb-start-backup').onclick=()=>backup();}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
