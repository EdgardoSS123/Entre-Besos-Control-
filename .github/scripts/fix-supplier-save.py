from pathlib import Path
import re

p=Path('suppliers-ui.js');s=p.read_text()
def replace(old,new):
 global s
 if new in s:return
 assert s.count(old)==1,(old[:100],s.count(old))
 s=s.replace(old,new,1)

replace("function formError(m){const el=$('supplier-error');if(el)el.textContent=m;else message(m,true);}","""function formError(m){
 const el=$('supplier-error');if(!el){message(m,true);return;}
 el.textContent=m;el.hidden=!m;
 if(m)requestAnimationFrame(()=>{if(el.isConnected)el.scrollIntoView({block:'nearest',behavior:'instant'});});
}
function setSaving(value){
 const b=$('supplier-save');if(b){b.disabled=value;b.textContent=value?'Guardando…':'Guardar proveedor';}
 for(const id of ['supplier-close','supplier-cancel'])if($(id))$(id).disabled=value;
 $('supplier-form')?.setAttribute('aria-busy',String(value));
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
 const limit=Date.now()+20000;
 for(;;){
  await window.EBShared.flush();
  try{
   const row=await window.EBShared.snapshot(),saved=(row.data?.suppliers||[]).find(x=>x.id===result.record.id);
   if(saved&&saved.version>=result.record.version)return saved;
   throw Error('No se confirmó el proveedor en la base compartida. Tu captura se conserva.');
  }catch(e){
   const waiting=window.EBShared.pending||/pendientes de guardar|Confirma Actualizado/.test(e.message);
   if(!waiting||Date.now()>=limit)throw e;
   await new Promise(r=>setTimeout(r,100));
  }
 }
}""")
replace("<form id=\"supplier-form\"><p id=\"supplier-error\" role=\"alert\"></p>","<form id=\"supplier-form\" novalidate>")
replace('<div class="supplier-form-actions"><button class="secondary" type="button" id="supplier-cancel">','<p id="supplier-error" role="alert" hidden></p><div class="supplier-form-actions"><button class="secondary" type="button" id="supplier-cancel">')
replace("const d=dialog,state=returnView;dialog=null;editing=null;dirty=false;returnView=null;window.EBShared?.cancelDraft?.();window.EBEditReturn?.close(d);if(d.isConnected){if(d.open)d.close();d.remove();}if(restore)window.EBEditReturn?.restore(state);", "const d=dialog,state=returnView;dialog=null;editing=null;dirty=false;returnView=null;window.EBShared?.cancelDraft?.();if(d.contains(document.activeElement))document.activeElement.blur();if(d.open)d.close();d.remove();if(restore)window.EBEditReturn?.restore(state);")
old="""async function save(){
 if(busy||!editor())return;busy=true;$('supplier-save').disabled=true;formError('');
 try{
  if(!$('supplier-other-wrap').hidden){addItem($('supplier-other').value);$('supplier-other-wrap').hidden=true;$('supplier-item').value='';}
  const before=read(),input={name:$('supplier-name').value,items:chosen,contact:$('supplier-contact').value,phone:$('supplier-phone').value,email:$('supplier-email').value,place:$('supplier-place').value,notes:$('supplier-notes').value};
  const result=C.change(before.data,input,options());persist(result,before.raw);const state=returnView;closeForm(false);render();window.EBEditReturn?.restore(state);message(result.unchanged?'Sin cambios.':'Proveedor guardado.');if(!result.unchanged)await confirmShared(result,'Proveedor guardado.');
 }catch(e){formError('No se guardó: '+e.message);}finally{busy=false;if($('supplier-save'))$('supplier-save').disabled=false;}
}"""
new="""async function save(){
 if(busy||!editor())return;busy=true;setSaving(true);formError('');let locallySaved=false;
 try{
  const input=collectInput(),before=read(),result=C.change(before.data,input,options());
  persist(result,before.raw);locallySaved=true;
  // Retrying after a network problem updates this same record, never adds a duplicate.
  editing={id:result.record.id,expected:JSON.stringify(result.record)};
  await confirmedRecord(result);
  const state=returnView;closeForm(false);render();window.EBEditReturn?.restore(state);
  message(result.unchanged?'Proveedor confirmado. Sin cambios adicionales.':'Proveedor guardado. Confirmado en la base compartida.');
 }catch(e){
  formError(locallySaved?'Tu captura está guardada en este dispositivo, pero no se confirmó en la base compartida. No la vuelvas a crear; pulsa Guardar para reintentar. '+e.message:'No se guardó: '+e.message);
 }finally{busy=false;setSaving(false);}
}"""
replace(old,new)
p.write_text(s)

p=Path('suppliers.css');s=p.read_text()
extra='\n/* Visible validation beside Save, including native-email validation on touch. */\n#supplier-error:not(:empty){display:block;border:1px solid #e4a6b6;background:#fff4f7;color:#922342;padding:12px;border-radius:10px;margin:16px 0 8px;scroll-margin:18px;overflow-wrap:anywhere}#supplier-error[hidden]{display:none!important}.supplier-form-actions button:disabled{opacity:.65;cursor:wait}\n'
if extra not in s:p.write_text(s+extra)
p=Path('suppliers.html');s=p.read_text()
for name in ['suppliers-ui.js','suppliers.css']:
 s=re.sub(re.escape(name)+r'\?v=[^"\s]+',name+'?v=supplier-save2',s)
p.write_text(s)
print('Supplier-only fix applied. Existing core validation, EB1/EB2 permissions and all business data unchanged.')
