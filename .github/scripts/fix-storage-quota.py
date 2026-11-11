from pathlib import Path
import re

def patch(path,old,new):
 p=Path(path);s=p.read_text()
 if new in s:return
 assert s.count(old)==1,(path,old[:80],s.count(old))
 p.write_text(s.replace(old,new,1))

header=r'''// Confirmed cloud data need not fit a second localStorage copy.
// Pending writes have a durable IndexedDB journal; no existing key is erased.
const cache=new Map();
const get=k=>cache.has(k)?cache.get(k):nativeGet.call(localStorage,k);
const set=(k,v)=>{nativeSet.call(localStorage,k,v);cache.delete(k);};
const remove=k=>{nativeRemove.call(localStorage,k);cache.delete(k);};
const isQuota=e=>e?.name==='QuotaExceededError'||e?.code===22||e?.code===1014;
let quotaPending=null,journalDB=null;
function journal(){
 if(journalDB)return Promise.resolve(journalDB);
 return new Promise((resolve,reject)=>{
  if(!window.indexedDB)return reject(Error('No hay espacio local para conservar el pedido pendiente. Tu captura sigue abierta; no borres datos.'));
  const r=indexedDB.open('entre-besos-save-journal',1);
  r.onupgradeneeded=()=>r.result.createObjectStore('saves');
  r.onsuccess=()=>{journalDB=r.result;journalDB.onversionchange=()=>{journalDB.close();journalDB=null;};resolve(journalDB);};
  r.onerror=()=>reject(Error('No se pudo reservar espacio seguro para el guardado. Tu captura sigue abierta; no borres datos.'));
  r.onblocked=()=>reject(Error('Otra pestaña está preparando el guardado. Tu captura se conserva; vuelve a intentar.'));
 });
}
async function journalRead(){const db=await journal();return new Promise((resolve,reject)=>{const t=db.transaction('saves','readonly'),r=t.objectStore('saves').get('pending');let value;r.onsuccess=()=>value=r.result;t.oncomplete=()=>resolve(value||null);t.onabort=t.onerror=()=>reject(Error('No se pudo revisar el guardado local pendiente. No borres datos.'));});}
async function journalPut(value){
 const db=await journal();return new Promise((resolve,reject)=>{
  const t=db.transaction('saves','readwrite'),store=t.objectStore('saves'),r=store.get('pending');let problem='';
  r.onsuccess=()=>{if(r.result&&r.result.operation!==value.operation){problem='Hay otro guardado pendiente en este navegador. Se conservan ambas capturas; termina el primero antes de guardar.';t.abort();return;}try{store.put(value,'pending');}catch(e){problem='No se pudo conservar el guardado en este dispositivo. Tu captura sigue abierta; no borres datos.';t.abort();}};
  t.oncomplete=resolve;t.onabort=t.onerror=()=>reject(Error(problem||'El almacenamiento del dispositivo no permite conservar el pedido. Tu captura sigue abierta; no borres datos.'));
 });
}
async function journalRemove(operation){const db=await journal();return new Promise((resolve,reject)=>{const t=db.transaction('saves','readwrite'),store=t.objectStore('saves'),r=store.get('pending');r.onsuccess=()=>{if(r.result?.operation===operation)store.delete('pending');};t.oncomplete=resolve;t.onabort=t.onerror=()=>reject(Error('El servidor recibió el guardado, pero falta confirmar la copia de recuperación. Reintenta sin crear otro registro.'));});}
async function recoverJournal(){
 if(who?.role!=='editor')return;
 const pending=await journalRead();if(!pending)return;
 if(pending.actor!==who.username)throw Error('Hay un guardado pendiente de '+pending.actor+'. Entra con ese mismo socio EB1 para confirmarlo. No borres datos.');
 const local=parse(nativeGet.call(localStorage,OUT));
 if(local&&local.operation!==pending.operation)throw Error('Hay dos guardados pendientes en este navegador. Se conservan sin sobrescribirlos; no borres datos.');
 checkData(pending.raw);quotaPending=pending;cache.set(OUT,JSON.stringify(pending));cache.set(KEY,pending.raw);
}
async function clearPending(sent){
 if(quotaPending?.operation===sent.operation){await journalRemove(sent.operation);quotaPending=null;cache.delete(OUT);const local=parse(nativeGet.call(localStorage,OUT));if(local?.operation===sent.operation)nativeRemove.call(localStorage,OUT);}
 else remove(OUT);
}
function confirmedCache(row){
 const raw=JSON.stringify(row.data),meta=JSON.stringify({revision:row.revision,signature:signature(raw)});
 if(cache.has(KEY)){cache.set(KEY,raw);cache.set(META,meta);return;}
 const oldKey=nativeGet.call(localStorage,KEY),oldMeta=nativeGet.call(localStorage,META);
 try{set(KEY,raw);set(META,meta);}
 catch(e){
  if(!isQuota(e))throw e;
  try{if(oldKey!==null)nativeSet.call(localStorage,KEY,oldKey);if(oldMeta!==null)nativeSet.call(localStorage,META,oldMeta);}catch{}
  cache.set(KEY,raw);cache.set(META,meta);
 }
}
async function writeState(raw){
 raw=String(raw);const original=get(KEY);
 try{localStorage.setItem(KEY,raw);return;}
 catch(e){if(!isQuota(e))throw e;}
 if(!ready||who?.role!=='editor'||conflict||get(OUT)||sending)throw Error('Hay un guardado pendiente. Tu captura sigue abierta; vuelve a guardar cuando termine.');
 checkData(raw);const actor=who.username,pending={revision:parse(get(META))?.revision??revision,operation:crypto.randomUUID(),raw,actor};
 await journalPut(pending);
 if(who?.username!==actor||get(KEY)!==original||get(OUT)||sending){await journalRemove(pending.operation);throw Error('La información cambió mientras se preparaba el guardado. Tu captura se conserva; vuelve a guardar.');}
 quotaPending=pending;cache.set(KEY,raw);cache.set(OUT,JSON.stringify(pending));seenSignature=signature(raw);touched=false;
 status('Guardando en la base compartida…');setTimeout(flush,0);
}'''
patch('shared.js',"const get=k=>nativeGet.call(localStorage,k),set=(k,v)=>nativeSet.call(localStorage,k,v),remove=k=>nativeRemove.call(localStorage,k);",header)
patch('shared.js',"  const row=await api('state'),local=get(KEY)","  await recoverJournal();\n  const row=await api('state'),local=get(KEY)")
patch('shared.js',"if(parse(get(OUT))?.operation===pending.operation)remove(OUT);set(META,JSON.stringify({revision:ack.revision,signature:signature(pending.raw)}));return connect();","if(parse(get(OUT))?.operation===pending.operation)await clearPending(pending);confirmedCache({revision:ack.revision,data:checkData(pending.raw)});return connect();")
patch('shared.js',"const raw=JSON.stringify(row.data);if(get(KEY)&&get(KEY)!==raw)preserve();\n set(KEY,raw);set(META,JSON.stringify({revision:row.revision,signature:signature(raw)}));revision=row.revision;","const raw=JSON.stringify(row.data);if(get(KEY)&&get(KEY)!==raw){try{preserve();}catch(e){if(!isQuota(e))throw e;}}\n confirmedCache(row);revision=row.revision;")
patch('shared.js',"const next=parse(get(OUT));set(META,JSON.stringify({revision,signature:signature(sent.raw)}));\n   if(next?.operation===sent.operation){remove(OUT);}else if(next){next.revision=revision;set(OUT,JSON.stringify(next));}","const next=parse(get(OUT));\n   if(next?.operation===sent.operation){await clearPending(sent);confirmedCache({revision,data:checkData(sent.raw)});}else if(next){next.revision=revision;set(OUT,JSON.stringify(next));set(META,JSON.stringify({revision,signature:signature(sent.raw)}));}")
patch('shared.js',"function syncError(e){","function syncError(e){\n if(isQuota(e))return Error('Se llenó el espacio local reservado para esta app. Tu captura se conserva; vuelve a pulsar Guardar. No es un límite de pedidos ni de inventario.');")
patch('shared.js',"Storage.prototype.getItem=function(k){const raw=nativeGet.call(this,k);","Storage.prototype.getItem=function(k){const raw=this===localStorage?get(String(k)):nativeGet.call(this,k);")
patch('shared.js',"const previous=get(OUT),existing=parse(previous),meta=parse(get(META));","if(quotaPending)throw Error('Hay un guardado en recuperación pendiente. Termina de confirmarlo antes de modificar otro registro.');\n const previous=get(OUT),existing=parse(previous),meta=parse(get(META));")
patch('shared.js',"try{nativeSet.call(this,k,raw);}catch(e)","try{nativeSet.call(this,k,raw);cache.delete(KEY);}catch(e)")
patch('shared.js',"revision;},flush,prepareSave,","revision;},flush,writeState,prepareSave,")
patch('shared.js',"if(get(OUT))set('eb-conflict-copy-v1',parse(get(OUT)).raw);remove(OUT);","if(get(OUT))set('eb-conflict-copy-v1',parse(get(OUT)).raw);if(quotaPending)await clearPending(quotaPending);else remove(OUT);")
for name in ['orders-ui.js','suppliers-ui.js']:
 patch(name,"localStorage.setItem('eb-v1',JSON.stringify(result.data));","await window.EBShared.writeState(JSON.stringify(result.data));")
p=Path('orders.css');s=p.read_text();rule='\n.order-dialog .fields>label{min-width:0}.order-dialog input[type=date]{min-width:0;max-width:100%;width:100%;-webkit-appearance:none;appearance:none}\n'
if rule not in s:p.write_text(s+rule)
for p in Path('.').glob('*.html'):
 s=p.read_text()
 for asset in ['shared.js','orders-ui.js','orders.css','suppliers-ui.js']:
  s=re.sub(re.escape(asset)+r'\?v=[^"\s]+',asset+'?v=quota-journal1',s)
 p.write_text(s)
print('Quota-safe journal integrated without reading or modifying production records.')
