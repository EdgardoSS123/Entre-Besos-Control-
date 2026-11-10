/* Sequential private uploads. Each file keeps its own stable retry identifier. */
(function(){
'use strict';
const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ACCEPT='.pdf,.jpg,.jpeg,.png,.webp,.heic,.heif,.doc,.docx,.xls,.xlsx',LIMIT=10*1024*1024;
const size=n=>n<1048576?(n/1024).toLocaleString('es-MX',{maximumFractionDigits:1})+' KB':(n/1048576).toLocaleString('es-MX',{maximumFractionDigits:1})+' MB';
function open(c){
 if(!c.editor()||$('docs-dialog'))return;
 const back=window.EBEditReturn?.capture(),queue=[];let running=false,pause=false,closing=false;
 const dialog=document.createElement('dialog');dialog.id='docs-dialog';dialog.className='docs-dialog docs-batch-dialog';dialog.setAttribute('aria-labelledby','docs-batch-title');
 dialog.innerHTML='<div class="docs-dialog-title"><div><div class="eyebrow">ARCHIVO COMPARTIDO</div><h2 id="docs-batch-title">Subir documentos</h2></div><button type="button" id="docs-close" aria-label="Cerrar">×</button></div><form id="docs-form" novalidate><label>Categoría *<select id="doc-category"><option value="">Selecciona una categoría</option>'+c.categories.map(x=>'<option '+(x===c.selected?'selected':'')+'>'+esc(x)+'</option>').join('')+'</select></label><label class="docs-upload">Selecciona uno o varios archivos<input id="doc-file" type="file" multiple accept="'+ACCEPT+'"><small>PDF, imágenes, Word o Excel. Hasta 10 MB por archivo. Puedes agregar más archivos antes de guardar.</small></label><div id="doc-batch-files"></div><details class="docs-optional"><summary>Lote, vencimiento y notas (opcional)</summary><small>Estos datos se aplicarán a todos los archivos de esta carga. Después puedes editar cada documento por separado.</small><label>Lote relacionado<select id="doc-lot"><option value="">General / SAGAV Cuatro</option>'+c.lots.map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join('')+'</select></label><label>Fecha de vencimiento<input id="doc-expiry" type="date"></label><label>Notas<textarea id="doc-notes" maxlength="2000" rows="3"></textarea></label></details><p id="doc-batch-progress" role="status" aria-live="polite"></p><div id="docs-form-error" class="docs-form-error" role="alert"></div><div class="docs-form-actions"><button type="button" class="secondary" id="doc-cancel">Cancelar</button><button type="submit" class="primary" id="doc-save">Guardar documentos</button></div><p class="docs-save-note">Cada archivo se confirma en la base compartida. Reintentar no vuelve a subir los que ya quedaron guardados.</p></form>';
 document.body.append(dialog);dialog.showModal();
 function pending(){return queue.some(r=>r.state!=='saved');}
 function draw(){
  $('doc-batch-files').innerHTML=queue.map((r,i)=>'<article class="doc-batch-item" data-batch-index="'+i+'" data-state="'+r.state+'"><div class="doc-batch-name"><span>'+esc(r.file.name)+' · '+size(r.file.size)+'</span>'+(!r.payload&&r.state!=='saved'?'<button type="button" data-batch-remove="'+i+'" aria-label="Quitar '+esc(r.file.name)+'">Quitar</button>':'')+'</div><label>Nombre del documento<input '+(i===0?'id="doc-title"':'')+' data-batch-title="'+i+'" maxlength="160" value="'+esc(r.title)+'" '+(r.payload||r.state==='saved'?'readonly':'')+'></label><p class="doc-batch-state">'+esc(r.state==='saved'?'✓ Guardado':r.state==='sending'?'Enviando…':r.error||'Pendiente')+'</p></article>').join('');
  dialog.querySelectorAll('[data-batch-title]').forEach(e=>e.oninput=()=>{queue[Number(e.dataset.batchTitle)].title=e.value;c.dirty(true);});
  dialog.querySelectorAll('[data-batch-remove]').forEach(e=>e.onclick=()=>{if(running)return;queue.splice(Number(e.dataset.batchRemove),1);draw();c.dirty(pending());});
  const saved=queue.filter(r=>r.state==='saved').length,errors=queue.filter(r=>r.state==='error').length;
  $('doc-batch-progress').textContent=queue.length?saved+' de '+queue.length+' guardados'+(errors?' · '+errors+' por revisar':''):'';
  $('doc-save').textContent=running?'Guardando '+(saved+1)+' de '+queue.length+'…':queue.length&&saved===queue.length?'Finalizar':saved?'Reintentar pendientes':queue.length===1?'Guardar documento':'Guardar documentos';
  const locked=queue.some(r=>r.payload);for(const id of ['doc-category','doc-lot','doc-expiry','doc-notes'])$(id).disabled=running||locked;
  $('doc-file').disabled=running;$('doc-save').disabled=running;$('docs-close').disabled=running;$('doc-cancel').textContent=running?'Pausar':'Cerrar';$('doc-cancel').disabled=running&&pause;
  dialog.querySelectorAll('[data-batch-title],[data-batch-remove]').forEach(e=>e.disabled=running);
 }
 function choose(){
  for(const file of $('doc-file').files){const key=[file.name,file.size,file.lastModified].join('\u0000');if(queue.some(r=>r.key===key))continue;
   const supported=ACCEPT.split(',').some(ext=>file.name.toLowerCase().endsWith(ext)),error=!file.size?'El archivo está vacío.':file.size>LIMIT?'Supera 10 MB. Selecciona una versión más pequeña.':!supported?'Formato no admitido. Usa PDF, imagen, Word o Excel.':'';
   queue.push({key,id:crypto.randomUUID(),file,title:file.name.replace(/\.[^.]+$/,'').slice(0,160),state:error?'error':'pending',error,invalid:!!error,payload:null});
  }
  $('doc-file').value='';c.dirty(pending());draw();
 }
 async function finish(){
  if(closing)return;closing=true;const count=queue.filter(r=>r.state==='saved').length,category=$('doc-category').value;c.dirty(false);dialog.close();await c.saved(category,count,back);
 }
 function close(){
  if(running){pause=true;draw();return;}
  const saved=queue.filter(r=>r.state==='saved').length;
  if(pending()&&!confirm('Hay archivos pendientes o sin confirmación. Los '+saved+' guardados se conservan. ¿Cerrar esta selección?'))return;
  const category=$('doc-category').value;dialog.close();if(saved)c.saved(category,saved,back);else window.EBEditReturn?.restore(back);
 }
 $('doc-file').onchange=choose;$('docs-close').onclick=close;$('doc-cancel').onclick=close;dialog.oncancel=e=>{e.preventDefault();close();};dialog.onclose=()=>{c.dirty(false);c.saving(false);dialog.remove();window.EBShared?.cancelDraft?.();};
 $('docs-form').oninput=()=>c.dirty(pending());
 $('docs-form').onsubmit=async e=>{
  e.preventDefault();if(running)return;$('docs-form-error').textContent='';const common={category:$('doc-category').value,lot:$('doc-lot').value,expiry:$('doc-expiry').value,notes:$('doc-notes').value.trim()};
  if(!c.categories.includes(common.category)){$('docs-form-error').textContent='Selecciona una categoría.';return;}if(!queue.length){$('docs-form-error').textContent='Selecciona al menos un archivo.';return;}
  if(common.expiry&&(!/^\d{4}-\d{2}-\d{2}$/.test(common.expiry)||!Number.isFinite(Date.parse(common.expiry+'T12:00:00Z'))||new Date(common.expiry+'T12:00:00Z').toISOString().slice(0,10)!==common.expiry)){$('docs-form-error').textContent='La fecha de vencimiento no es válida.';return;}
  running=true;pause=false;c.saving(true);draw();
  try{
   for(const r of queue){
    if(pause)break;if(r.state==='saved'||r.invalid)continue;
    if(!r.title.trim()){r.state='error';r.error='Escribe un nombre para este documento.';draw();continue;}
    r.state='sending';r.error='';draw();
    try{
     const base64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(Error('No se pudo leer este archivo.'));reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(r.file);});
     if(!r.payload)r.payload={...common,id:r.id,title:r.title.trim(),filename:r.file.name.normalize('NFC').trim()};
     const response=await c.api('',{method:'POST',body:JSON.stringify({...r.payload,base64})});
     if(!response.document||response.document.id!==r.id||response.document.size!==r.file.size)throw Error('El servidor no confirmó este archivo.');
     r.state='saved';r.error='';
    }catch(err){
     let recovered=false;
     if(r.payload&&(!err.status||err.status>=500)){
      try{const response=await c.api('/'+r.id),stored=response.document;if(stored&&!stored.deleted&&stored.size===r.file.size&&['title','category','lot','expiry','notes','filename'].every(k=>stored[k]===r.payload[k])){r.state='saved';r.error='';recovered=true;}}catch{}
     }
     if(!recovered){r.state='error';r.error=err.message||'No se confirmó el archivo.';if([400,413,415].includes(err.status))r.payload=null;if(!err.status||[401,403,413].includes(err.status)||err.status>=500)pause=true;}
    }
    draw();
   }
  }finally{running=false;c.saving(false);c.dirty(pending());draw();}
  if(!pending())await finish();else{$('docs-form-error').textContent='Los archivos guardados se conservan. Revisa los pendientes y pulsa «Reintentar pendientes»; no se duplicarán los guardados.';}
 };
 draw();
}
window.EBDocBatch={open};
})();
