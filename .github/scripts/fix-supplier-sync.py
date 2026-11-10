"""Narrow repair of pending saves; never changes or migrates business data."""
from pathlib import Path
import re

def replace(path,old,new):
 p=Path(path);s=p.read_text()
 if new in s:return
 assert s.count(old)==1,(path,old[:80],s.count(old))
 p.write_text(s.replace(old,new,1))

replace('shared.js',"let seenSignature=null;", "let seenSignature=null,flushTask=null,lastSyncError=null;")
replace('shared.js',"async function api(url,options={}){", "async function api(url,options={},retrySession=true){")
replace('shared.js',"if(!r.ok)throw Object.assign(Error(d.error||'No se pudo sincronizar.'),{status:r.status});return d;", """if(r.status===403&&d.error==='La sesión debe actualizarse.'&&retrySession&&who?.role==='editor'){
   // Cookies are shared across tabs; a same-account login renews the CSRF token.
   // Never retry a mutation under a different user or a read-only account.
   const current=await api('session',{},false);
   if(!current.authenticated||current.user?.username!==who.username||current.user?.role!=='editor')throw Object.assign(Error('La cuenta cambió en otra pestaña. Vuelve a entrar con el mismo socio EB1; tu captura local se conserva.'),{status:403});
   csrf=current.csrf;return api(url,options,false);
  }
  if(!r.ok)throw Object.assign(Error(d.error||'No se pudo sincronizar.'),{status:r.status});return d;""")
replace('shared.js',"if(sending||conflict||!ready||who.role!=='editor')return;sending=true;", "if(sending||conflict||!ready||who?.role!=='editor')return;sending=true;lastSyncError=null;")
replace('shared.js',"}catch(e){if(e.status===409){conflict=true;status('Conflicto:","}catch(e){lastSyncError=syncError(e);if(e.status===409){conflict=true;status('Conflicto:")
replace('shared.js',"else status('Pendiente de enviar · '+e.message,true);}finally{sending=false;}", "else status('Pendiente de enviar · '+lastSyncError.message,true);}finally{sending=false;}")
replace('shared.js',"async function flush(){if(navigator.locks)return navigator.locks.request('entre-besos-sync',{ifAvailable:true},lock=>lock?sendPending():undefined);return sendPending();}", """function syncError(e){
 if(e?.name==='AbortError')return Error('La conexión tardó demasiado. Tu captura se conserva; pulsa Guardar para reintentar.');
 if(e instanceof TypeError)return Error('No hay conexión con la base compartida. Tu captura se conserva; revisa tu conexión y vuelve a guardar.');
 return e instanceof Error?e:Error('No se pudo confirmar el guardado. Tu captura se conserva.');
}
function flush(){
 // A confirmation joins the actual send, including a send started by autosave.
 // Queued Web Locks prevent two tabs sending conflicting snapshots at once.
 if(flushTask)return flushTask;
 const controller=new AbortController();let lockEntered=false;
 const timeout=setTimeout(()=>controller.abort(),30000);
 flushTask=(async()=>{
  try{
   if(navigator.locks)await navigator.locks.request('entre-besos-sync',{signal:controller.signal},async()=>{lockEntered=true;clearTimeout(timeout);await sendPending();});
   else {clearTimeout(timeout);await sendPending();}
  }catch(e){lastSyncError=e?.name==='AbortError'&&!lockEntered?Error('Otra pestaña sigue guardando. Tu captura se conserva; termina ese guardado y pulsa Guardar aquí.'):syncError(e);status('Pendiente de enviar · '+lastSyncError.message,true);}
  finally{clearTimeout(timeout);flushTask=null;}
 })();
 return flushTask;
}""")
replace('shared.js',"if(!ready||!who)throw Error('Inicia sesión para generar el reporte.');", "if(!ready||!who)throw Error('Inicia sesión para confirmar la información compartida. Tu captura local se conserva.');")
replace('shared.js',"if(get(OUT)||conflict||sending)throw Error('Hay cambios pendientes de guardar. Confirma Actualizado y vuelve a generar el PDF.');", "if(get(OUT)||conflict||sending)throw lastSyncError||Error('El guardado todavía no está confirmado. Tu captura local se conserva; vuelve a intentar Guardar.');")
replace('shared.js',"if(!row.data)throw Error('Conecta primero la PC con tus datos. No se generará un resumen vacío.');", "if(!row.data)throw Error('Conecta primero la PC con tus datos. La base compartida aún no tiene información.');")
p=Path('suppliers-ui.js');s=p.read_text();start=s.index('async function confirmedRecord(result){');end=s.index('\nfunction render()',start)
replacement="""async function confirmedRecord(result){
 const row=await window.EBShared.snapshot();
 const saved=(row.data?.suppliers||[]).find(x=>x.id===result.record.id);
 if(saved&&JSON.stringify(saved)===JSON.stringify(result.record))return saved;
 throw Error('El proveedor no coincide con la versión confirmada. Tu captura se conserva; revisa si otro socio lo modificó.');
}"""
s=s[:start]+replacement+s[end:];p.write_text(s)
replace('suppliers-ui.js',"$('supplier-form')?.setAttribute('aria-busy',String(value));", """$('supplier-form')?.setAttribute('aria-busy',String(value));
 for(const el of $('supplier-form')?.querySelectorAll('input,select,textarea,button')||[]){
  if(['supplier-save','supplier-cancel'].includes(el.id))continue;
  if(value){if(el.dataset.beforeSaveDisabled===undefined)el.dataset.beforeSaveDisabled=el.disabled?'1':'0';el.disabled=true;}
  else if(el.dataset.beforeSaveDisabled!==undefined){el.disabled=el.dataset.beforeSaveDisabled==='1';delete el.dataset.beforeSaveDisabled;}
 }""")
replace('suppliers-ui.js',"editing={id:result.record.id,expected:JSON.stringify(result.record)};\n  await confirmedRecord(result);", "editing={id:result.record.id,expected:JSON.stringify(result.record)};\n  setSaving(true);await confirmedRecord(result);")
for p in Path('.').glob('*.html'):
 s=p.read_text()
 for asset in ['shared.js','suppliers-ui.js']:
  s=re.sub(re.escape(asset)+r'\?v=[^"\s]+',asset+'?v=supplier-sync3',s)
 p.write_text(s)
print('Applied narrow shared-send/supplier confirmation repair. No user records changed.')
